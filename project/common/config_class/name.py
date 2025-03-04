def get_system_name() -> str:
    with open("name.txt", "r") as f:
        return f.read().strip()
