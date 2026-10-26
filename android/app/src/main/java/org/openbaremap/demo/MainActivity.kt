package org.openbaremap.demo

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.os.Build
import android.view.WindowInsets
import android.view.ViewGroup
import android.widget.*
import org.maplibre.android.MapLibre
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.Style
import org.openbaremap.android.OpenBareMapResources
import java.io.File
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var mapView: MapView
    private lateinit var status: TextView
    private lateinit var importButton: Button
    private var map: MapLibreMap? = null
    private var current: File? = null
    private val worker = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(this)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            } else {
                @Suppress("DEPRECATION")
                view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            }
            insets
        }
        val controls = LinearLayout(this)
        importButton = Button(this).apply { text = "Import map"; setOnClickListener { chooseMap() } }
        controls.addView(importButton)
        controls.addView(Button(this).apply { text = "Legend"; setOnClickListener { showLegend() } })
        controls.addView(Button(this).apply { text = "Credits"; setOnClickListener { showCredits() } })
        root.addView(controls)
        status = TextView(this).apply { text = "Choose the OpenBareMap offline package to begin."; setPadding(16, 8, 16, 8); textSize = 14f }
        root.addView(status)
        mapView = MapView(this); mapView.onCreate(savedInstanceState)
        mapView.addOnDidFailLoadingMapListener { message -> status.text = "Map could not load: $message" }
        root.addView(mapView, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
        mapView.getMapAsync { ready ->
            map = ready
            ready.cameraPosition = CameraPosition.Builder().target(LatLng(53.4, -8.15)).zoom(7.0).build()
            val saved = getPreferences(MODE_PRIVATE).getString("mapDirectory", null)
            if (saved != null && File(saved).isDirectory) loadMap(File(saved), true)
        }
    }

    private fun chooseMap() {
        startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE); type = "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/zip", "application/octet-stream", "application/x-zip-compressed"))
        }, 10)
    }
    @Deprecated("Activity result API retained for this minimal platform Activity")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 10 || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        importButton.isEnabled = false; status.text = "Importing offline map…"
        worker.execute {
            try {
                var lastUpdate = 0L
                val installed = contentResolver.openInputStream(uri)!!.use { input ->
                    OpenBareMapResources.installZip(input, File(filesDir, "maps")) { bytes ->
                        val now = System.currentTimeMillis()
                        if (now - lastUpdate > 400) { lastUpdate = now; runOnUiThread { status.text = "Importing map · ${bytes / 1048576} MB" } }
                    }
                }
                getPreferences(MODE_PRIVATE).edit().putString("mapDirectory", installed.absolutePath).apply()
                loadMap(installed, false)
            } catch (failure: Exception) { runOnUiThread { status.text = "Import failed: ${failure.message}"; importButton.isEnabled = true } }
        }
    }
    private fun loadMap(directory: File, verify: Boolean) {
        runOnUiThread { importButton.isEnabled = false; status.text = "Checking offline map…" }
        worker.execute {
            try {
                if (verify) OpenBareMapResources.verify(directory)
                val style = OpenBareMapResources.prepareStyle(directory)
                runOnUiThread {
                    if (isFinishing || isDestroyed) return@runOnUiThread
                    current = directory
                    map?.setStyle(Style.Builder().fromJson(style)) { status.text = "Offline map ready"; importButton.isEnabled = true }
                }
            } catch (failure: Exception) { runOnUiThread { status.text = "Map could not load: ${failure.message}"; importButton.isEnabled = true } }
        }
    }
    private fun showCredits() {
        val text = current?.let { File(it, "ATTRIBUTION.txt").takeIf(File::isFile)?.readText() }
            ?: "OpenBareMap · © OpenStreetMap contributors. Import the map for full data-source credits."
        AlertDialog.Builder(this).setTitle("Map credits").setMessage(text).setPositiveButton("Close", null).show()
    }
    private fun showLegend() {
        val file = current?.let { File(it, "legend/openbaremap-legend.png") }
        if (file?.isFile != true) { status.text = "Import the map to view its legend."; return }
        val image = ImageView(this).apply { setImageURI(android.net.Uri.fromFile(file)); adjustViewBounds = true }
        val scroll = ScrollView(this).apply { addView(image) }
        AlertDialog.Builder(this).setTitle("Map legend").setView(scroll).setPositiveButton("Close", null).show()
    }
    override fun onStart() { super.onStart(); mapView.onStart() }
    override fun onResume() { super.onResume(); mapView.onResume() }
    override fun onPause() { mapView.onPause(); super.onPause() }
    override fun onStop() { mapView.onStop(); super.onStop() }
    override fun onLowMemory() { super.onLowMemory(); mapView.onLowMemory() }
    override fun onSaveInstanceState(outState: Bundle) { super.onSaveInstanceState(outState); mapView.onSaveInstanceState(outState) }
    override fun onDestroy() { mapView.onDestroy(); worker.shutdown(); super.onDestroy() }
}
