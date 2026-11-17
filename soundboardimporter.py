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


def load_queue():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    return []


def save_queue(queue):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=4))


queue = load_queue()


def valid_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    return (
        parsed.scheme in ("http", "https")
        and (host == "myinstants.com"
             or host.endswith(".myinstants.com"))
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

    save_queue(queue)

    print("\n[+] Soundboard added to queue!")
    print(f"[+] Current queue: {len(queue)} soundboard(s)")

    queue_menu()


def queue_menu():
    while True:
        print("\n" + "-" * 44)
        print(f"Current queue: {len(queue)} soundboard(s)")
        print("-" * 44)
        print("[1] Import current queue")
        print("[2] Add more soundboards")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            process_queue()
            return

        elif choice == "2":
            add_soundboard()
            return

        else:
            print("[!] Invalid option.")


def file_hash(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def process_queue():
    if not queue:
        print("\n[!] Your queue is empty.")
        pause()
        return

    print("\nPROCESSING SOUND BOARDS")
    print("=" * 44)

    destination = OUTPUT_DIR / selected_app
    destination.mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    imported = 0
    skipped = 0

    for index, board in enumerate(queue, start=1):
        print(f"\n[{index}/{len(queue)}] {board['name']}")
        print(f"URL: {board['url']}")

        print("\nEnter the folder containing your authorized audio downloads.")
        source_input = input("> ").strip().strip('"')

        if not source_input:
            print("[!] Skipped.")
            continue

        source = Path(source_input).expanduser()

        if not source.is_dir():
            print("[!] Folder does not exist.")
            continue

        safe_name = "".join(
            c for c in board["name"]
            if c.isalnum() or c in " -_"
        ).strip()

        if not safe_name:
            safe_name = f"Soundboard {index}"

        board_folder = destination / safe_name
        board_folder.mkdir(parents=True, exist_ok=True)

        files = [
            p for p in source.rglob("*")
            if p.is_file()
            and p.suffix.lower() in AUDIO_EXTENSIONS
        ]

        if not files:
            print("[!] No supported audio files found.")
            continue

        print(f"\nFound {len(files)} audio files.")

        for file_index, file in enumerate(files, start=1):
            try:
                digest = file_hash(file)

                if digest in seen_hashes:
                    skipped += 1
                    continue

                seen_hashes.add(digest)

                target = board_folder / file.name

                if target.exists():
                    target = (
                        board_folder /
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
                print(f"\n[!] Could not copy {file.name}: {error}")

        print("\n[+] Soundboard processed.")

    print("\n" + "=" * 44)
    print("PROCESSING COMPLETE")
    print("=" * 44)
    print(f"Sounds prepared: {imported}")
    print(f"Duplicates skipped: {skipped}")
    print(f"Output directory: {destination}")

    if imported:
        print("\nOpening your soundboard folder...")
        open_folder(destination)

    queue.clear()
    save_queue(queue)

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
            print("[!] This operating system is not supported.")
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

        elif choice == "2":
            print("\nThanks for using Soundboard importer!")
            break

        else:
            print("\n[!] Invalid option.")
            pause()


selected_app = None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting Soundboard importer...")
        sys.exit(0)
