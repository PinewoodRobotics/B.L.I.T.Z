val backendPath = gradle.extra["backendPath"] as String

tasks.register<Exec>("deployBlitz") {
    workingDir = rootProject.projectDir
    commandLine("python3", "$backendPath/deploy.py")
}
