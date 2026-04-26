def parse_output_flags(output: str, expected_flags: list[str]) -> dict[str, str]:
    """
    Parse the output of a command and return a dictionary of flags and their values.

    Args:
        output: The output of the command to parse.
        expected_flags: A list of flags to expect in the output.

    Returns:
        A dictionary of flags and their values.

    Example:
    output:
      LINUX_DISTRO=ubuntu-22_04
      C_LIB_VERSION=2.35
      RESULT_PATH=/work/build/release/2.35/ubuntu-22_04/rust/test
    expected_flags: ["LINUX_DISTRO", "C_LIB_VERSION", "RESULT_PATH"]
    returns:
      {
        "LINUX_DISTRO": "ubuntu-22_04",
        "C_LIB_VERSION": "2.35",
        "RESULT_PATH": "/work/build/release/2.35/ubuntu-22_04/rust/test"
      }
    """
    flags = {}
    for line in output.splitlines():
        for flag in expected_flags:
            if line.startswith(flag + "="):
                flags[flag] = line.removeprefix(flag + "=")
                break
    return flags
