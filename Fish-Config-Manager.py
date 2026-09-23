from pathlib import Path
import shutil
import subprocess


CONFIG_DIR = Path.home() / ".config" / "fish"
CONFIG_FILE = CONFIG_DIR / "config.fish"
BACKUP_FILE = CONFIG_DIR / "config.fish.backup"


def print_header():
    print("Made with ❤️ by Cozy")
    print()
    print("Fish Shell Startup Manager")
    print("--------------------------")
    print(f"Config: {CONFIG_FILE}")
    print()


def ensure_config():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not CONFIG_FILE.exists():
            CONFIG_FILE.write_text("", encoding="utf-8")

        return True

    except OSError as error:
        print(f"\nError creating Fish configuration: {error}")
        return False


def read_config():
    try:
        return CONFIG_FILE.read_text(encoding="utf-8")
    except OSError as error:
        print(f"\nError reading Fish config: {error}")
        return ""


def save_config(contents):
    try:
        if CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, BACKUP_FILE)

        temporary_file = CONFIG_FILE.with_suffix(".tmp")

        temporary_file.write_text(
            contents,
            encoding="utf-8"
        )

        temporary_file.replace(CONFIG_FILE)

        print("\nFish configuration saved.")

        if BACKUP_FILE.exists():
            print("Backup created at:")
            print(f"  {BACKUP_FILE}")

        return True

    except OSError as error:
        print(f"\nError saving Fish config: {error}")
        return False


def show_config():
    contents = read_config()

    print()
    print("Current Fish configuration")
    print("==========================")
    print()

    if not contents.strip():
        print("(config.fish is empty)")
    else:
        print(contents.rstrip())

    print()


def is_startup_command(line):
    stripped = line.strip()

    if not stripped:
        return False

    if stripped.startswith("#"):
        return False

    if stripped.startswith("if "):
        return False

    if stripped.startswith("for "):
        return False

    if stripped.startswith("while "):
        return False

    if stripped.startswith("function "):
        return False

    if stripped.startswith("switch "):
        return False

    if stripped == "end":
        return False

    if stripped == "else":
        return False

    if stripped.startswith("case "):
        return False

    if stripped.startswith("set "):
        return False

    if stripped.startswith("alias "):
        return False

    if stripped.startswith("abbr "):
        return False

    return True


def get_startup_commands():
    contents = read_config()
    lines = contents.splitlines()

    commands = []

    for line_number, line in enumerate(lines, start=1):
        if is_startup_command(line):
            commands.append({
                "line": line_number,
                "command": line.strip()
            })

    return commands


def show_startup_commands():
    commands = get_startup_commands()

    print()
    print("Things automatically running from config.fish")
    print("==============================================")
    print()

    if not commands:
        print("No startup commands were detected.")
        print()
        return

    for index, item in enumerate(commands, start=1):
        print(
            f"{index:>3}. "
            f"Line {item['line']}: "
            f"{item['command']}"
        )

    print()


def add_startup_command():
    print()
    print("Add Startup Command")
    print("===================")
    print()
    print("Enter the command you want Fish to run")
    print("when an interactive Fish shell starts.")
    print()
    print("Examples:")
    print("  neofetch")
    print("  fastfetch")
    print("  source ~/.config/fish/functions/example.fish")
    print()

    command = input("Command: ").strip()

    if not command:
        print("\nNo command entered.")
        return

    contents = read_config()

    if contents and not contents.endswith("\n"):
        contents += "\n"

    contents += command + "\n"

    save_config(contents)


def remove_startup_command():
    commands = get_startup_commands()

    if not commands:
        print("\nNo startup commands were detected.")
        return

    print()
    print("Startup commands:")
    print()

    for index, item in enumerate(commands, start=1):
        print(f"{index:>3}. {item['command']}")

    print()

    choice = input(
        "Enter the number to remove, or 'all' to remove all: "
    ).strip().lower()

    if choice == "all":
        confirmation = input(
            "Are you sure you want to remove all "
            "detected startup commands? [yes/no] "
        ).strip().lower()

        if confirmation not in {"yes", "y"}:
            print("\nCancelled.")
            return

        contents = read_config()
        lines = contents.splitlines()

        command_lines = {
            item["line"]
            for item in commands
        }

        new_lines = [
            line
            for number, line in enumerate(lines, start=1)
            if number not in command_lines
        ]

        new_contents = "\n".join(new_lines)

        if contents.endswith("\n"):
            new_contents += "\n"

        save_config(new_contents)
        return

    try:
        number = int(choice)
    except ValueError:
        print("\nInvalid selection.")
        return

    if number < 1 or number > len(commands):
        print("\nInvalid selection.")
        return

    selected = commands[number - 1]

    print()
    print(f"Selected: {selected['command']}")
    print()

    confirmation = input(
        "Remove this startup command? [yes/no] "
    ).strip().lower()

    if confirmation not in {"yes", "y"}:
        print("\nCancelled.")
        return

    contents = read_config()
    lines = contents.splitlines()

    target_line = selected["line"]

    new_lines = [
        line
        for number, line in enumerate(lines, start=1)
        if number != target_line
    ]

    new_contents = "\n".join(new_lines)

    if contents.endswith("\n"):
        new_contents += "\n"

    save_config(new_contents)


def edit_config():
    print()
    print("Edit config.fish")
    print("================")
    print()

    editor = None

    for program in ["nano", "vim", "vi", "micro"]:
        if shutil.which(program):
            editor = program
            break

    if editor is None:
        print("No supported terminal editor was found.")
        print("Install nano, vim, vi, or micro.")
        return

    try:
        subprocess.run(
            [editor, str(CONFIG_FILE)],
            check=False
        )
    except OSError as error:
        print(f"Could not open editor: {error}")


def restore_backup():
    if not BACKUP_FILE.exists():
        print("\nNo backup file exists.")
        return

    print()
    print("Backup found:")
    print(f"  {BACKUP_FILE}")
    print()

    confirmation = input(
        "Restore the backup over config.fish? [yes/no] "
    ).strip().lower()

    if confirmation not in {"yes", "y"}:
        print("\nCancelled.")
        return

    try:
        shutil.copy2(
            BACKUP_FILE,
            CONFIG_FILE
        )

        print("\nBackup restored successfully.")

    except OSError as error:
        print(f"\nCould not restore backup: {error}")


def main():
    print_header()

    if not ensure_config():
        return

    while True:
        print("What would you like to do?")
        print()
        print("1. Show current Fish config")
        print("2. Show automatic startup commands")
        print("3. Add a startup command")
        print("4. Remove a startup command")
        print("5. Edit config.fish manually")
        print("6. Restore backup")
        print("7. Exit")
        print()

        choice = input("Select 1-7: ").strip()

        if choice == "1":
            show_config()

        elif choice == "2":
            show_startup_commands()

        elif choice == "3":
            add_startup_command()

        elif choice == "4":
            remove_startup_command()

        elif choice == "5":
            edit_config()

        elif choice == "6":
            restore_backup()

        elif choice == "7":
            print("\nGoodbye.")
            break

        else:
            print("\nInvalid selection. Please choose 1-7.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
#not tested
