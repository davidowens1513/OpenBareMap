package org.openbaremap.android

import org.json.JSONObject
import java.io.File
import java.io.InputStream
import java.security.MessageDigest
import java.util.UUID
import java.util.zip.ZipInputStream

/** Local MapLibre resource resolution and verified offline-package installation. */
object OpenBareMapResources {
    private const val MAX_BYTES = 8L * 1024 * 1024 * 1024
    private const val MAX_FILES = 10000

    fun prepareStyle(packageDirectory: File): String {
        val manifest = JSONObject(File(packageDirectory, "manifest.json").readText())
        require(manifest.getString("packageFormat") == "openbaremap-android-resources-v1") { "Unsupported map package" }
        val style = JSONObject(File(packageDirectory, "style.json").readText())
        val sources = style.getJSONObject("sources")
        val files = manifest.getJSONObject("sourceFiles")
        for (name in files.keys()) {
            val file = containedFile(packageDirectory, files.getString(name))
            require(file.isFile) { "Missing map database: $name" }
            val source = sources.getJSONObject(name)
            source.remove("tiles")
            source.put("url", "mbtiles://" + file.toURI().rawPath)
        }
        sources.getJSONObject("townlands").put("data", fileURL(File(packageDirectory, "townlands.geojson")))
        style.put("glyphs", fileURL(File(packageDirectory, "fonts")).trimEnd('/') + "/{fontstack}/{range}.pbf")
        style.put("sprite", fileURL(File(packageDirectory, "sprites/outdoors")))
        return style.toString()
    }

    /** Runs on a worker thread. Previous installed versions are preserved. */
    fun installZip(input: InputStream, storage: File, progress: (Long) -> Unit = {}): File {
        require(storage.isDirectory || storage.mkdirs()) { "Cannot create map storage" }
        val staging = File(storage, ".install-${UUID.randomUUID()}")
        require(staging.mkdir())
        try {
            var total = 0L
            var entries = 0
            val names = HashSet<String>()
            ZipInputStream(input.buffered()).use { zip ->
                val buffer = ByteArray(1024 * 1024)
                while (true) {
                    val entry = zip.nextEntry ?: break
                    require(++entries <= MAX_FILES) { "Too many package files" }
                    require(names.add(entry.name)) { "Duplicate package entry" }
                    val target = containedFile(staging, entry.name)
                    if (entry.isDirectory) require(target.isDirectory || target.mkdirs()) else {
                        require(target.parentFile!!.isDirectory || target.parentFile!!.mkdirs())
                        target.outputStream().use { output ->
                            while (true) {
                                val count = zip.read(buffer)
                                if (count < 0) break
                                total += count
                                require(total <= MAX_BYTES) { "Map package exceeds size limit" }
                                output.write(buffer, 0, count)
                                progress(total)
                            }
                        }
                    }
                    zip.closeEntry()
                }
            }
            verify(staging)
            prepareStyle(staging) // Validate all runtime database references before publication.
            val identity = digest(File(staging, "manifest.json")).take(16)
            val destination = File(storage, "map-$identity")
            if (destination.exists()) {
                verify(destination)
                staging.deleteRecursively()
                return destination
            }
            require(staging.renameTo(destination)) { "Cannot publish installed map" }
            return destination
        } catch (failure: Exception) {
            staging.deleteRecursively()
            throw failure
        }
    }

    /** Detects corruption; hashes do not authenticate an untrusted publisher. */
    fun verify(directory: File) {
        val sums = File(directory, "SHA256SUMS.txt")
        require(sums.isFile) { "Missing package checksums" }
        val verified = HashSet<String>()
        sums.forEachLine { line ->
            if (line.isNotBlank()) {
                require(line.length > 66 && line.substring(64, 66) == "  ") { "Invalid checksum record" }
                val expected = line.substring(0, 64)
                require(expected.matches(Regex("[0-9a-f]{64}")))
                val name = line.substring(66)
                require(verified.add(name)) { "Duplicate checksum record" }
                val file = containedFile(directory, name)
                require(file.isFile && digest(file) == expected) { "Corrupt map file: $name" }
            }
        }
        val actual = directory.walkTopDown().filter { it.isFile }.map { it.relativeTo(directory).invariantSeparatorsPath }.toSet() - "SHA256SUMS.txt"
        require(actual == verified) { "Package inventory does not match checksums" }
        require("manifest.json" in verified && "style.json" in verified)
    }

    internal fun containedFile(root: File, name: String): File {
        require(name.isNotEmpty() && !name.startsWith('/') && '\\' !in name) { "Invalid resource path" }
        val canonicalRoot = root.canonicalFile
        val file = File(root, name).canonicalFile
        require(file.path.startsWith(canonicalRoot.path + File.separator)) { "Resource escapes package directory" }
        return file
    }

    private fun fileURL(file: File) = java.net.URI("file", "", file.absolutePath, null, null).toASCIIString()

    private fun digest(file: File): String {
        val hash = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { stream ->
            val buffer = ByteArray(1024 * 1024)
            while (true) { val count = stream.read(buffer); if (count < 0) break; hash.update(buffer, 0, count) }
        }
        return hash.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
    }
}
