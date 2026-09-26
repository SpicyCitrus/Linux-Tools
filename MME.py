import json
import os
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

CONFIG_FILE = SCRIPT_DIR / "mme_config.json"

CRYPTO_DIR = SCRIPT_DIR / "Crypto"
XMRIG_DIR = CRYPTO_DIR / "xmrig"
BUILD_DIR = XMRIG_DIR / "build"
XMRIG_BINARY = BUILD_DIR / "xmrig"

MINER_URL = "gulf.moneroocean.stream:10128"


def default_config():
    return {
        "token": "",
        "device_name": ""
    }


def load_config():
    if not CONFIG_FILE.exists():
        return default_config()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)

        if "token" not in config:
            config["token"] = ""

        if "device_name" not in config:
            config["device_name"] = ""

        return config

    except (json.JSONDecodeError, OSError):
        print("Warning: Could not read the configuration file.")
        return default_config()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass

        return True

    except OSError as error:
        print(f"Could not save configuration: {error}")
        return False


def clear_screen():
    os.system("clear")


def pause():
    input("\nPress Enter to continue...")


def run_bash(command):
    print()
    print(f"$ {command}")
    print()

    result = subprocess.run(
        ["bash", "-c", command],
        check=False
    )

    if result.returncode != 0:
        print()
        print(f"Command failed with exit code {result.returncode}.")
        return False

    return True


def build():
    clear_screen()

    print("======================================")
    print("        Auto Builder for MME")
    print("        Made with ❤️ by Cozy")
    print("======================================")
    print()

    print("Script directory:")
    print(f"  {SCRIPT_DIR}")
    print()

    print("Config file:")
    print(f"  {CONFIG_FILE}")
    print()

    print("Starting build...")
    print()

    CRYPTO_DIR.mkdir(parents=True, exist_ok=True)

    if not run_bash("sudo apt update"):
        pause()
        return

    if not run_bash("sudo apt upgrade -y"):
        pause()
        return

    install_command = (
        "sudo apt install "
        "git "
        "build-essential "
        "cmake "
        "libuv1-dev "
        "libssl-dev "
        "libhwloc-dev "
        "-y"
    )

    if not run_bash(install_command):
        pause()
        return

    if XMRIG_DIR.exists():
        print()
        print("XMRig directory already exists.")
        print(f"Using: {XMRIG_DIR}")
    else:
        clone_command = (
            f"cd {CRYPTO_DIR} && "
            "git clone https://github.com/xmrig/xmrig.git"
        )

        if not run_bash(clone_command):
            pause()
            return

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    cmake_command = f"cd {BUILD_DIR} && cmake .."

    if not run_bash(cmake_command):
        pause()
        return

    make_command = f"cd {BUILD_DIR} && make -j$(nproc)"

    if not run_bash(make_command):
        pause()
        return

    if not CONFIG_FILE.exists():
        save_config(default_config())

    print()
    print("======================================")
    print("             BUILD COMPLETE")
    print("======================================")
    print()
    print("The API has been installed.")
    print("You may now use the Start Selection!")
    print()
    print("XMRig location:")
    print(f"  {XMRIG_BINARY}")
    print()
    print("Config location:")
    print(f"  {CONFIG_FILE}")

    pause()


def set_change_token():
    clear_screen()

    print("======================================")
    print("        Set / Change Token")
    print("======================================")
    print()

    config = load_config()

    if config.get("token"):
        print("Current token/wallet address:")
        print(config["token"])
        print()

    if config.get("device_name"):
        print("Current device name:")
        print(config["device_name"])
        print()

    print("--------------------------------------")
    print()

    token = input("Enter your token/wallet address: ").strip()

    if not token:
        print()
        print("Token/wallet address cannot be empty.")
        pause()
        return

    print()

    device_name = input("Enter a device name: ").strip()

    if not device_name:
        print()
        print("Device name cannot be empty.")
        pause()
        return

    config["token"] = token
    config["device_name"] = device_name

    if save_config(config):
        print()
        print("======================================")
        print("       CONFIGURATION SAVED")
        print("======================================")
        print()
        print(f"Token/wallet: {token}")
        print(f"Device name:  {device_name}")
        print()
        print("Saved to:")
        print(CONFIG_FILE)

    pause()


def start():
    clear_screen()

    print("======================================")
    print("                Start")
    print("======================================")
    print()

    config = load_config()

    token = config.get("token", "").strip()
    device_name = config.get("device_name", "").strip()

    if not token:
        print("No token/wallet address has been configured.")
        print()
        print("Please use:")
        print("  Set / Change Token")
        print()
        pause()
        return

    if not device_name:
        print("No device name has been configured.")
        print()
        print("Please use:")
        print("  Set / Change Token")
        print()
        pause()
        return

    if not XMRIG_BINARY.exists():
        print("XMRig has not been built yet.")
        print()
        print("Please select Build first.")
        print()
        pause()
        return

    print("Starting")
    print()

    time.sleep(5)

    print()
    print("Launching XMRig...")
    print(f"Server: {MINER_URL}")
    print(f"Device: {device_name}")
    print()

    command = [
        str(XMRIG_BINARY),
        "-o",
        MINER_URL,
        "-u",
        token,
        "-p",
        device_name
    ]

    try:
        result = subprocess.run(
            command,
            check=False
        )

        print()
        print(f"XMRig exited with code {result.returncode}.")

    except KeyboardInterrupt:
        print()
        print("XMRig stopped.")

    except OSError as error:
        print()
        print(f"Could not start XMRig: {error}")

    pause()


def main_menu():
    while True:
        clear_screen()

        print("======================================")
        print("        Auto Builder for MME")
        print("        Made with ❤️ by Cozy")
        print("======================================")
        print()
        print(" [1] Build")
        print(" [2] Start")
        print(" [3] Set / Change Token")
        print(" [4] Exit")
        print()

        choice = input("Select an option: ").strip()

        if choice == "1":
            build()

        elif choice == "2":
            start()

        elif choice == "3":
            set_change_token()

        elif choice == "4":
            clear_screen()
            print("Goodbye!")
            sys.exit(0)

        else:
            print()
            print("Invalid selection.")
            time.sleep(1)


if __name__ == "__main__":
    main_menu()
# not tested also please only use on your own machines
