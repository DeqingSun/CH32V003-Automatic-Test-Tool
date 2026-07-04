import os
import platform


def locate_minichlink():
    tool_binary_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolBinary")
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        binary_name = "minichlink_mac"
    elif system == "linux" and machine in ("aarch64", "arm64"):
        binary_name = "minichlink_pi"
    else:
        print(f"Unsupported platform for minichlink: {system} {machine}")
        return False

    minichlink_path = os.path.join(tool_binary_directory, binary_name)
    if not os.path.exists(minichlink_path):
        print(f"Minichlink not found: {minichlink_path}")
        return False
    return minichlink_path
