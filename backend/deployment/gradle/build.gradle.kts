import java.io.ByteArrayOutputStream
import org.gradle.api.GradleException

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
    Regex("""found (\d+) systems?""").find(output)?.let {
        return it.groupValues[1].toInt()
    }

    Regex("""Deployed on (\d+) Pis""").find(output)?.let {
        return it.groupValues[1].toInt()
    }

    return null
}

tasks.register("deployBackend") {
    doLast {
        val expected = expectedNumOfPis()
        if (expected == null) {
            logger.warn("EXPECTED_NUM_OF_PIS is not set; skipping deployed Pi count validation.")
        }

        val stdout = ByteArrayOutputStream()
        val stderr = ByteArrayOutputStream()
        val result = try {
            project.exec {
                workingDir = rootProject.projectDir
                standardInput = System.`in`
                standardOutput = stdout
                errorOutput = stderr
                isIgnoreExitValue = true
                environment("PYTHONUNBUFFERED", "1")
                environment("TERM", System.getenv("TERM") ?: "xterm-256color")
                environment("BLITZ_LOGGER_MODE", "plain")
                commandLine("python3", "$backendPath/deploy.py")
            }
        } catch (error: Exception) {
            print(stdout.toString())
            System.err.print(stderr.toString())
            throw GradleException("Failed to apply backend: ${error.message}", error)
        }

        print(stdout.toString())
        System.err.print(stderr.toString())

        if (result.exitValue != 0) {
            throw GradleException("Failed to apply backend because deploy.py exited with status ${result.exitValue}")
        }

        if (expected == null) {
            return@doLast
        }

        val output = "${stdout}\n${stderr}"
        val deployed = deployedPiCount(output)
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
