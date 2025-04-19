import psutil


def get_system_name() -> str:
    with open("name.txt", "r") as f:
        return f.read().strip()


def get_top_10_processes() -> list[psutil.Process]:
    processes = sorted(
        psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
        key=lambda p: p.info["cpu_percent"],
        reverse=True,
    )

    return processes[:10]
