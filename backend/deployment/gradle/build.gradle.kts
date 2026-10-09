import java.io.ByteArrayOutputStream
import java.io.OutputStream
import org.gradle.api.GradleException
import org.gradle.api.tasks.Exec

val backendPath = gradle.extra["backendPath"] as String

fun expectedNumOfPis(): Int? {
    val expected = providers.gradleProperty("EXPECTED_NUM_OF_PIS").orNull
        ?: if (gradle.extra.has("EXPECTED_NUM_OF_PIS")) {
            gradle.extra["EXPECTED_NUM_OF_PIS"].toString()
        } else {
            null
        }
        ?: return null

    return expected.toIntOrNull()
        ?: throw GradleException("EXPECTED_NUM_OF_PIS must be an integer, got '$expected'")
}

fun deployedPiCount(output: String): Int? {
    Regex("""Deployed on (\d+) Pis""").find(output)?.let {
        return it.groupValues[1].toInt()
    }

    Regex("""found (\d+) systems?""").find(output)?.let {
        return it.groupValues[1].toInt()
    }

    return null
}

val stdout = ByteArrayOutputStream()
val liveOutput = object : OutputStream() {
    override fun write(value: Int) {
        stdout.write(value)
        System.out.write(value)
    }

    override fun write(bytes: ByteArray, offset: Int, length: Int) {
        stdout.write(bytes, offset, length)
        System.out.write(bytes, offset, length)
    }

    override fun flush() {
        System.out.flush()
    }
}

tasks.register<Exec>("deployBackend") {
    workingDir = rootProject.projectDir
    standardInput = System.`in`
    standardOutput = liveOutput
    errorOutput = System.err
    isIgnoreExitValue = true
    environment("PYTHONUNBUFFERED", "1")
    environment("TERM", System.getenv("TERM") ?: "xterm-256color")
    environment("BLITZ_LOGGER_MODE", "plain")
    commandLine("python3", "$backendPath/deploy.py")

    doLast {
        val expected = expectedNumOfPis()
        if (expected == null) {
            logger.warn("EXPECTED_NUM_OF_PIS is not set; skipping deployed Pi count validation.")
        }

        if (executionResult.get().exitValue != 0) {
            throw GradleException("Failed to apply backend because deploy.py exited with status ${executionResult.get().exitValue}")
        }

        if (expected == null) {
            return@doLast
        }

        val deployed = deployedPiCount(stdout.toString())
            ?: throw GradleException("Failed to apply backend because the deployed Pi count could not be determined")

        if (deployed != expected) {
            println("")
            println("=============================================================")
            println("Failed to apply backend because it was not deployed on the expected number of Pis. Please set the expected number of Pis in the build.gradle file and try again (check 'EXPECTED_NUM_OF_PIS' variable).")
            println("Expected number of Pis: $expected")
            println("Deployed number of Pis: $deployed")
            println("=============================================================")
            println("")

            throw GradleException("Failed to apply backend because it was not deployed on the expected number of Pis (expected $expected Pis, deployed $deployed Pis)")
        }
    }
}

listOf(
    "cacheBackend" to "cache",
    "discoverBackend" to "discover",
    "buildBackend" to "build",
    "distributeBackend" to "distribute",
).forEach { (taskName, phase) ->
    tasks.register<Exec>(taskName) {
        workingDir = rootProject.projectDir
        standardInput = System.`in`
        environment("PYTHONUNBUFFERED", "1")
        environment("BLITZ_LOGGER_MODE", "plain")
        commandLine("python3", "$backendPath/deploy.py", phase)
    }
}
