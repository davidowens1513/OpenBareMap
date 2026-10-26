plugins { id("com.android.library") }
android {
    namespace = "org.openbaremap.android"
    compileSdk { version = release(36) { minorApiLevel = 1 } }
    defaultConfig { minSdk = 23 }
    testOptions { unitTests.all { it.systemProperty("openbaremap.package", providers.gradleProperty("mapPackage").getOrElse("")) } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
dependencies { testImplementation("junit:junit:4.13.2"); testImplementation("org.json:json:20240303") }
