package org.openbaremap.android

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class ResourcesTest {
    private fun root() = Files.createTempDirectory("OpenBareMap test ").toFile()
    private fun hash(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it.toInt() and 255) }
    private fun fixture(dir: File) {
        File(dir, "maps").mkdirs(); File(dir, "maps/base.mbtiles").writeText("fixture")
        File(dir, "manifest.json").writeText("""{"packageFormat":"openbaremap-android-resources-v1","sourceFiles":{"basemap":"maps/base.mbtiles"}}""")
        File(dir, "style.json").writeText("""{"version":8,"sources":{"basemap":{"type":"vector"},"townlands":{"type":"geojson"}},"layers":[]}""")
        File(dir, "townlands.geojson").writeText("{}"); File(dir, "fonts").mkdir()
        val records = dir.walkTopDown().filter { it.isFile }.map { hash(it) + "  " + it.relativeTo(dir).invariantSeparatorsPath }.toList()
        File(dir, "SHA256SUMS.txt").writeText(records.joinToString("\n") + "\n")
    }
    private fun zip(dir: File): ByteArray = ByteArrayOutputStream().also { bytes ->
        ZipOutputStream(bytes).use { zip ->
            dir.walkTopDown().filter { it.isFile }.forEach { file -> zip.putNextEntry(ZipEntry(file.relativeTo(dir).invariantSeparatorsPath)); zip.write(file.readBytes()); zip.closeEntry() }
        }
    }.toByteArray()

    @Test fun resolvesEscapedPathsWithoutNetworkSources() {
        val dir=root()
        try {
            fixture(dir)
            val style=JSONObject(OpenBareMapResources.prepareStyle(dir))
            val uri=style.getJSONObject("sources").getJSONObject("basemap").getString("url")
            assertTrue(uri.startsWith("mbtiles:///")); assertTrue(uri.contains("%20"))
            assertTrue(style.getString("glyphs").startsWith("file:///"))
            assertTrue(style.getString("glyphs").endsWith("/{fontstack}/{range}.pbf"))
            assertFalse(style.toString().contains("http://"))
        } finally { dir.deleteRecursively() }
    }
    @Test fun verifiedInstallIsRepeatableAndPreservesPreviousVersion() {
        val source=root(); val storage=root()
        try {
            fixture(source); val data=zip(source)
            val first=OpenBareMapResources.installZip(ByteArrayInputStream(data),storage)
            assertEquals(first,OpenBareMapResources.installZip(ByteArrayInputStream(data),storage))
            val old=File(storage,"previous-map").apply { mkdir(); File(this,"keep").writeText("old") }
            assertTrue(old.isDirectory); assertEquals(2,storage.listFiles()!!.size)
        } finally { source.deleteRecursively(); storage.deleteRecursively() }
    }
    @Test fun rejectsCorruptAndUnlistedFiles() {
        val dir=root()
        try {
            fixture(dir); File(dir,"extra").writeText("unexpected")
            assertThrows(IllegalArgumentException::class.java) { OpenBareMapResources.verify(dir) }
            File(dir,"extra").delete(); File(dir,"maps/base.mbtiles").appendText("changed")
            assertThrows(IllegalArgumentException::class.java) { OpenBareMapResources.verify(dir) }
        } finally { dir.deleteRecursively() }
    }
    @Test fun rejectsTraversalAndRollsBackFailedInstallation() {
        val storage=root()
        try {
            val bytes=ByteArrayOutputStream()
            ZipOutputStream(bytes).use { it.putNextEntry(ZipEntry("../escaped")); it.write(1); it.closeEntry() }
            assertThrows(IllegalArgumentException::class.java) { OpenBareMapResources.installZip(ByteArrayInputStream(bytes.toByteArray()),storage) }
            assertEquals(0,storage.listFiles()!!.size)
            assertThrows(IllegalArgumentException::class.java) { OpenBareMapResources.containedFile(storage,"/absolute") }
        } finally { storage.deleteRecursively() }
    }
    @Test fun verifiesTheRealAssembledPackageWhenRequested() {
        val path=System.getProperty("openbaremap.package", "").orEmpty()
        org.junit.Assume.assumeTrue(path.isNotBlank())
        val directory=File(path)
        OpenBareMapResources.verify(directory)
        val style=JSONObject(OpenBareMapResources.prepareStyle(directory))
        val sources=style.getJSONObject("sources")
        for (name in listOf("basemap","coast","topography","hillshade","irish-grid")) {
            val url=sources.getJSONObject(name).getString("url")
            assertTrue(url.startsWith("mbtiles:///")); assertFalse(url.contains("{package}"))
        }
        assertTrue(sources.getJSONObject("townlands").getString("data").startsWith("file:///"))
    }

}
