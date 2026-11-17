import os
import sys
import json
import shutil
import hashlib
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse

APP_NAME = "Soundboard importer"
AUTHOR = "Made with ❤️ by Cozy"

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".ogg", ".flac",
    ".m4a", ".aac", ".opus", ".wma"
}

OUTPUT_DIR = Path.home() / "SoundboardImporter"
QUEUE_FILE = OUTPUT_DIR / "queue.json"
system = platform.system()


def clear():
    os.system("cls" if system == "Windows" else "clear")


def header():
    print("=" * 44)
    print(APP_NAME.center(44))
    print("=" * 44)
    print(AUTHOR.center(44))
    print("=" * 44)
    print()


def pause():
    input("\nPress Enter to continue...")


def open_folder(path):
    try:
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Linux":
            subprocess.Popen(["xdg-open", str(path)])
        else:
            print("Unsupported operating system.")
    except Exception as error:
        print(f"Could not open folder: {error}")


def get_downloads_folder():
    home = Path.home()
    downloads = home / "Downloads"

    config_file = home / ".config" / "user-dirs.dirs"

    if system == "Linux" and config_file.exists():
        try:
            for line in config_file.read_text().splitlines():
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    value = value.replace("$HOME", str(home))
                    downloads = Path(value)
                    break
        except OSError:
            pass

    return downloads


def load_queue():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if QUEUE_FILE.exists():
        try:
            data = json.loads(QUEUE_FILE.read_text())
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    return []


def save_queue():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=4))


queue = load_queue()
selected_app = None


def valid_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    return (
        parsed.scheme in ("http", "https")
        and (
            host == "myinstants.com"
            or host.endswith(".myinstants.com")
        )
    )


def add_soundboard():
    clear()
    header()

    print("ADD SOUNDS")
    print("-" * 44)

    url = input("\nPaste a Myinstants link:\n> ").strip()

    if not valid_url(url):
        print("\n[!] Invalid Myinstants URL.")
        pause()
        return

    if any(item["url"] == url for item in queue):
        print("\n[!] This link is already in the queue.")
        pause()
        return

    name = input("\nEnter a name for this soundboard: ").strip()

    if not name:
        name = f"Soundboard {len(queue) + 1}"

    queue.append({
        "name": name,
        "url": url
    })

    save_queue()

    print("\n[+] Soundboard added to queue!")
    print(f"[+] Current queue: {len(queue)} soundboard(s)")
    pause()


def file_hash(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def choose_destination():
    while True:
        clear()
        header()

        print("CHOOSE DOWNLOAD LOCATION\n")
        print("[1] Soundboard Importer folder")
        print("[2] Downloads folder")
        print("[3] Custom folder")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            return OUTPUT_DIR / selected_app

        elif choice == "2":
            return get_downloads_folder() / "Soundboard Importer" / selected_app

        elif choice == "3":
            custom = input("\nEnter destination folder:\n> ").strip().strip('"')

            if custom:
                return Path(custom).expanduser() / selected_app

            print("[!] Invalid folder.")
            pause()

        else:
            print("[!] Invalid option.")
            pause()


def process_queue():
    if not queue:
        print("\n[!] Your queue is empty.")
        pause()
        return

    destination = choose_destination()

    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"\n[!] Cannot create destination: {error}")
        pause()
        return

    seen_hashes = set()
    imported = 0
    skipped = 0
    failed = 0

    for index, board in enumerate(queue, start=1):
        clear()
        header()

        print(f"PROCESSING {board['name']}")
        print(f"Board {index}/{len(queue)}")
        print("-" * 44)

        print("\nEnter the folder containing your authorized audio downloads.")
        source_input = input("> ").strip().strip('"')

        if not source_input:
            print("[!] Skipped.")
            failed += 1
            pause()
            continue

        source = Path(source_input).expanduser()

        if not source.is_dir():
            print("[!] Folder does not exist.")
            failed += 1
            pause()
            continue

        safe_name = "".join(
            c for c in board["name"]
            if c.isalnum() or c in " -_"
        ).strip()

        if not safe_name:
            safe_name = f"Soundboard {index}"

        board_folder = destination / safe_name

        try:
            board_folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"[!] Cannot create folder: {error}")
            failed += 1
            pause()
            continue

        files = sorted(
            p for p in source.rglob("*")
            if p.is_file()
            and p.suffix.lower() in AUDIO_EXTENSIONS
        )

        if not files:
            print("[!] No supported audio files found.")
            failed += 1
            pause()
            continue

        print(f"\nFound {len(files)} audio files.\n")

        for file_index, file in enumerate(files, start=1):
            try:
                digest = file_hash(file)

                if digest in seen_hashes:
                    skipped += 1
                    continue

                seen_hashes.add(digest)

                target = board_folder / file.name

                if target.exists():
                    if file_hash(target) == digest:
                        skipped += 1
                        continue

                    target = board_folder / (
                        f"{file.stem}_{file_index}{file.suffix}"
                    )

                shutil.copy2(file, target)
                imported += 1

                print(
                    f"\r[+] Processed {file_index}/{len(files)}",
                    end="",
                    flush=True
                )

            except OSError as error:
                failed += 1
                print(f"\n[!] {file.name}: {error}")

        print("\n\n[+] Soundboard processed.")
        pause()

    clear()
    header()

    print("PROCESSING COMPLETE")
    print("=" * 44)
    print(f"Sounds copied: {imported}")
    print(f"Duplicates skipped: {skipped}")
    print(f"Errors/skipped boards: {failed}")
    print(f"\nDestination: {destination}")

    if imported:
        print("\nOpening destination folder...")
        open_folder(destination)

    queue.clear()
    save_queue()

    pause()


def queue_menu():
    while queue:
        clear()
        header()

        print("CURRENT QUEUE")
        print("-" * 44)

        for index, board in enumerate(queue, start=1):
            print(f"[{index}] {board['name']}")

        print("\n[1] Import current queue")
        print("[2] Add more soundboards")
        print("[3] Back to main menu")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            process_queue()
            return

        elif choice == "2":
            add_soundboard()

        elif choice == "3":
            return

        else:
            print("[!] Invalid option.")
            pause()


def select_application():
    global selected_app

    while True:
        clear()
        header()

        print(f"Detected OS: {system}\n")

        if system == "Windows":
            print("Choose your soundboard application:\n")
            print("[1] Soundpad")
            print("[2] Soundux")
            print("[3] Exit")

            choice = input("\nSelect option: ").strip()

            if choice == "1":
                selected_app = "Soundpad"
                return True

            elif choice == "2":
                selected_app = "Soundux"
                return True

            elif choice == "3":
                return False

        elif system == "Linux":
            print("Soundboard application:\n")
            print("[1] Soundux")
            print("[2] Exit")

            choice = input("\nSelect option: ").strip()

            if choice == "1":
                selected_app = "Soundux"
                return True

            elif choice == "2":
                return False

        else:
            print("[!] Unsupported operating system.")
            return False

        print("\n[!] Invalid selection.")
        pause()


def main():
    if not select_application():
        return

    while True:
        clear()
        header()

        print(f"Selected application: {selected_app}")
        print(f"Queued soundboards: {len(queue)}")

        print("\n[1] Add sounds")
        print("[2] Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            add_soundboard()

            if queue:
                queue_menu()

        elif choice == "2":
            print("\nThanks for using Soundboard importer!")
            break

        else:
            print("\n[!] Invalid option.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting Soundboard importer...")
        sys.exit(0)
