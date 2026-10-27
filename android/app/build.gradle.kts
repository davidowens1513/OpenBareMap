plugins { id("com.android.application") }
android {
    namespace = "org.openbaremap.demo"
    compileSdk { version = release(36) { minorApiLevel = 1 } }
    defaultConfig {
        applicationId = "org.openbaremap.demo"
        minSdk = 23
        targetSdk = 36
        versionCode = 20000
        versionName = "2.0.0"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
dependencies {
    implementation(project(":loader"))
    implementation("org.maplibre.gl:android-sdk-opengl:13.6.1")
}
