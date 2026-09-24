import argparse
import configparser
import datetime
import json
import sys
from pathlib import Path


APP_NAME = "Cozy Theme Tool"
BRAND = "Made with ❤️ by Cozy"

SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR
HOME = Path.home()

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
CURSOR_INDEX = HOME / ".icons" / "default" / "index.theme"


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def color(text, value):
    if not sys.stdout.isatty():
        return text
    return f"{value}{text}{Colors.RESET}"


def success(message):
    print(color(f"✓ {message}", Colors.GREEN))


def error(message):
    print(color(f"✗ {message}", Colors.RED), file=sys.stderr)


def info(message):
    print(color(f"• {message}", Colors.CYAN))


def warning(message):
    print(color(f"! {message}", Colors.YELLOW))


def banner():
    print()
    print(color("╔══════════════════════════════════════════╗", Colors.MAGENTA))
    print(color("║          COZY THEME TOOL                 ║", Colors.MAGENTA))
    print(color("╚══════════════════════════════════════════╝", Colors.MAGENTA))
    print()
    print(color(BRAND, Colors.DIM))
    print()


def pause():
    try:
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print()


def ask_confirmation(message):
    while True:
        try:
            answer = input(f"{message} [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            print()
            return False

        if answer in ("y", "yes"):
            return True

        if answer in ("", "n", "no"):
            return False

        print("Please answer yes or no.")


def ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_backup_directory():
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as exc:
        error(f"Cannot access script directory: {exc}")
        return False


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        error(f"Could not read {path}: {exc}")
        return None


def get_ini_value(path, section, key):
    if not path.exists():
        return None

    parser = configparser.ConfigParser()

    try:
        parser.read(path, encoding="utf-8")
    except (OSError, configparser.Error):
        return None

    if parser.has_option(section, key):
        return parser.get(section, key)

    return None


def set_ini_values(path, values):
    parser = configparser.ConfigParser()

    if path.exists():
        try:
            parser.read(path, encoding="utf-8")
        except configparser.Error as exc:
            error(f"Could not parse {path}: {exc}")
            return False

    for (section, key), value in values.items():
        if not parser.has_section(section):
            parser.add_section(section)

        parser.set(section, key, value)

    try:
        ensure_parent(path)

        with path.open("w", encoding="utf-8") as file:
            parser.write(file)

        return True

    except OSError as exc:
        error(f"Could not write {path}: {exc}")
        return False


def get_current_cursor_theme():
    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-cursor-theme-name"
        )

        if value:
            return value

    if CURSOR_INDEX.exists():
        content = read_text(CURSOR_INDEX)

        if content:
            for line in content.splitlines():
                line = line.strip()

                if line.lower().startswith("inherits="):
                    return line.split("=", 1)[1].strip()

                if line.lower().startswith("inheriting="):
                    return line.split("=", 1)[1].strip()

    return None


def set_cursor_theme(theme):
    values = {
        ("Settings", "gtk-cursor-theme-name"): theme
    }

    changed = False

    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_values(settings, values):
            changed = True

    try:
        ensure_parent(CURSOR_INDEX)

        CURSOR_INDEX.write_text(
            "[Icon Theme]\n"
            f"Inherits={theme}\n",
            encoding="utf-8"
        )

        changed = True

    except OSError as exc:
        error(f"Could not configure cursor theme: {exc}")

    return changed


def get_current_icon_theme():
    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-icon-theme"
        )

        if value:
            return value

    return None


def set_icon_theme(theme):
    values = {
        ("Settings", "gtk-icon-theme"): theme
    }

    changed = False

    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_values(settings, values):
            changed = True

    return changed


def theme_directories():
    return [
        HOME / ".icons",
        HOME / ".local" / "share" / "icons",
        HOME / ".local" / "share" / "themes",
        Path("/usr/share/icons"),
        Path("/usr/share/themes"),
        Path("/usr/local/share/icons"),
        Path("/usr/local/share/themes"),
    ]


def discover_icon_themes():
    themes = set()

    for directory in theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                if (child / "index.theme").exists():
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.lower)


def discover_cursor_themes():
    themes = set()

    for directory in theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                cursor_directory = child / "cursors"

                if cursor_directory.exists() and cursor_directory.is_dir():
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.lower)


def timestamp():
    return datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )


def backup_filename():
    return BACKUP_DIR / f"cozy-backup-{timestamp()}.backup"


def create_backup():
    if not ensure_backup_directory():
        return None

    backup_path = backup_filename()

    snapshot = {
        "format": 1,
        "created": datetime.datetime.now().isoformat(),
        "tool": APP_NAME,
        "brand": BRAND,
        "files": {}
    }

    paths = [
        GTK3_SETTINGS,
        GTK4_SETTINGS,
        CURSOR_INDEX,
    ]

    for path in paths:
        key = str(path)

        if path.exists():
            content = read_text(path)

            if content is None:
                error(f"Could not back up {path}")
                return None

            snapshot["files"][key] = {
                "exists": True,
                "content": content
            }
        else:
            snapshot["files"][key] = {
                "exists": False,
                "content": None
            }

    try:
        backup_path.write_text(
            json.dumps(
                snapshot,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return backup_path

    except OSError as exc:
        error(f"Could not create backup: {exc}")
        return None


def automatic_backup():
    print()
    info("Creating automatic backup...")

    backup = create_backup()

    if backup:
        success(f"Automatic backup created: {backup.name}")
        return True

    warning("The automatic backup failed.")
    print()
    print("Changes cannot safely continue without a backup.")
    print()

    if not ask_confirmation(
        "Would you like to attempt a manual backup now?"
    ):
        error("Changes cancelled.")
        return False

    print()
    info("Attempting manual backup...")

    manual_backup = create_backup()

    if manual_backup:
        success(f"Manual backup created: {manual_backup.name}")
        return True

    error("Manual backup also failed.")
    print()

    if ask_confirmation("Continue WITHOUT a backup?"):
        warning("You chose to continue without a backup.")
        return True

    error("Changes cancelled.")
    return False


def list_backups():
    backups = sorted(
        BACKUP_DIR.glob("*.backup"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("No .backup files found in the script directory.")
        return

    print()
    print(color("Available backups:", Colors.BOLD))
    print()

    for index, path in enumerate(backups, 1):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        print(
            f"  {index:2}. {path.name} "
            f"({size} bytes)"
        )


def find_backup(identifier):
    backups = sorted(
        BACKUP_DIR.glob("*.backup"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:
        return None

    if identifier.isdigit():
        number = int(identifier)

        if 1 <= number <= len(backups):
            return backups[number - 1]

        return None

    candidate = BACKUP_DIR / identifier

    if (
        candidate.exists()
        and candidate.is_file()
        and candidate.suffix == ".backup"
    ):
        return candidate

    return None


def restore_backup(identifier):
    path = find_backup(identifier)

    if path is None:
        error("Backup not found.")
        return False

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        error(f"Could not read backup: {exc}")
        return False

    if data.get("format") != 1:
        error("Unsupported backup format.")
        return False

    files = data.get("files")

    if not isinstance(files, dict):
        error("Backup is missing its file data.")
        return False

    print()
    info("Creating safety backup before restoring...")

    safety_backup = create_backup()

    if safety_backup is None:
        warning("Safety backup failed.")
        print()

        if not ask_confirmation(
            "Attempt a manual safety backup?"
        ):
            error("Restore cancelled.")
            return False

        safety_backup = create_backup()

        if safety_backup is None:
            error("Manual safety backup failed.")

            if not ask_confirmation(
                "Restore without a safety backup?"
            ):
                error("Restore cancelled.")
                return False

            warning(
                "You chose to restore without a safety backup."
            )
        else:
            success(
                f"Manual safety backup created: "
                f"{safety_backup.name}"
            )
    else:
        success(
            f"Safety backup created: "
            f"{safety_backup.name}"
        )

    try:
        for filename, file_data in files.items():
            target = Path(filename)

            exists = file_data.get("exists", False)
            content = file_data.get("content")

            if exists:
                if not isinstance(content, str):
                    raise ValueError(
                        f"Invalid content for {filename}"
                    )

                ensure_parent(target)

                target.write_text(
                    content,
                    encoding="utf-8"
                )

            elif target.exists():
                target.unlink()

        success(f"Restored: {path.name}")
        return True

    except (OSError, ValueError) as exc:
        error(f"Restore failed: {exc}")

        if safety_backup:
            error(
                f"Your safety backup is available as "
                f"{safety_backup.name}"
            )

        return False


def delete_backup(identifier):
    path = find_backup(identifier)

    if path is None:
        error("Backup not found.")
        return False

    try:
        path.unlink()
        success(f"Deleted {path.name}")
        return True

    except OSError as exc:
        error(f"Could not delete backup: {exc}")
        return False


def show_current():
    cursor = get_current_cursor_theme()
    icons = get_current_icon_theme()

    print()
    print(color("Current theme configuration", Colors.BOLD))
    print()

    print(
        "  Cursor theme : "
        + (
            cursor
            if cursor
            else color("not configured", Colors.DIM)
        )
    )

    print(
        "  Icon theme   : "
        + (
            icons
            if icons
            else color("not configured", Colors.DIM)
        )
    )


def choose_theme(themes, title):
    print()
    print(color(title, Colors.BOLD))
    print()

    if not themes:
        warning("No installed themes were found.")
        return None

    for index, theme in enumerate(themes, 1):
        print(f"  {index:2}. {theme}")

    print()
    print("   0. Cancel")
    print()

    while True:
        try:
            choice = input("Select a theme: ").strip()

        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(themes):
                return themes[number - 1]

        print("Please enter a valid number.")


def change_cursor_interactive():
    themes = discover_cursor_themes()

    theme = choose_theme(
        themes,
        "Installed cursor themes"
    )

    if not theme:
        return

    print()
    print(f"Selected cursor theme: {theme}")

    if not automatic_backup():
        return

    if set_cursor_theme(theme):
        success(
            f"Cursor theme changed to: {theme}"
        )
        info(
            "You may need to restart applications "
            "for the change to appear."
        )
    else:
        error("Cursor theme could not be changed.")


def change_icon_interactive():
    themes = discover_icon_themes()

    theme = choose_theme(
        themes,
        "Installed application icon themes"
    )

    if not theme:
        return

    print()
    print(f"Selected icon theme: {theme}")

    if not automatic_backup():
        return

    if set_icon_theme(theme):
        success(
            f"Application icon theme changed to: {theme}"
        )
        info(
            "You may need to restart applications "
            "for the change to appear."
        )
    else:
        error(
            "Application icon theme could not be changed."
        )


def change_both_interactive():
    cursor_themes = discover_cursor_themes()

    cursor = choose_theme(
        cursor_themes,
        "Installed cursor themes"
    )

    if not cursor:
        return

    icon_themes = discover_icon_themes()

    icons = choose_theme(
        icon_themes,
        "Installed application icon themes"
    )

    if not icons:
        return

    print()
    print(f"Selected cursor theme: {cursor}")
    print(f"Selected icon theme: {icons}")

    if not automatic_backup():
        return

    cursor_ok = set_cursor_theme(cursor)
    icon_ok = set_icon_theme(icons)

    print()

    if cursor_ok:
        success(
            f"Cursor theme changed to: {cursor}"
        )
    else:
        error("Cursor theme could not be changed.")

    if icon_ok:
        success(
            f"Application icon theme changed to: {icons}"
        )
    else:
        error(
            "Application icon theme could not be changed."
        )

    if cursor_ok or icon_ok:
        info(
            "You may need to restart applications "
            "for changes to appear."
        )


def restore_interactive():
    list_backups()

    backups = sorted(
        BACKUP_DIR.glob("*.backup"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:
        return

    print()

    try:
        choice = input(
            "Enter backup number or filename "
            "(0 to cancel): "
        ).strip()

    except KeyboardInterrupt:
        print()
        return

    if choice == "0":
        return

    restore_backup(choice)


def delete_backup_interactive():
    list_backups()

    print()

    try:
        selected = input(
            "Enter backup number or filename "
            "(0 to cancel): "
        ).strip()

    except KeyboardInterrupt:
        print()
        return

    if selected == "0":
        return

    path = find_backup(selected)

    if path is None:
        error("Backup not found.")
        return

    if not ask_confirmation(
        f"Delete {path.name}?"
    ):
        info("Deletion cancelled.")
        return

    delete_backup(selected)


def menu():
    while True:
        banner()
        show_current()

        print()
        print(color("Menu", Colors.BOLD))
        print()
        print("  1. Change cursor/mouse theme")
        print("  2. Change application icon theme")
        print("  3. Change both")
        print("  4. Restore backup")
        print("  5. List backups")
        print("  6. Delete backup")
        print("  0. Exit")
        print()

        try:
            choice = input("Choose an option: ").strip()

        except KeyboardInterrupt:
            print()
            return

        if choice == "1":
            change_cursor_interactive()
            pause()

        elif choice == "2":
            change_icon_interactive()
            pause()

        elif choice == "3":
            change_both_interactive()
            pause()

        elif choice == "4":
            restore_interactive()
            pause()

        elif choice == "5":
            list_backups()
            pause()

        elif choice == "6":
            delete_backup_interactive()
            pause()

        elif choice == "0":
            print()
            print(BRAND)
            print()
            return

        else:
            warning("Invalid option.")
            pause()


def command_list_themes(theme_type):
    if theme_type == "cursor":
        themes = discover_cursor_themes()
        title = "Installed cursor themes"
    else:
        themes = discover_icon_themes()
        title = "Installed application icon themes"

    print(color(title + ":", Colors.BOLD))
    print()

    if not themes:
        print("  None found.")
        return

    for theme in themes:
        print(f"  {theme}")


def command_set(args):
    if not args.cursor and not args.icons:
        error(
            "Specify --cursor, --icons, or both."
        )
        return 1

    if args.cursor:
        themes = discover_cursor_themes()

        print(
            color(
                "Installed cursor themes:",
                Colors.BOLD
            )
        )
        print()

        if themes:
            for theme in themes:
                print(f"  • {theme}")
        else:
            print("  No installed cursor themes found.")

        print()

        if not ask_confirmation(
            f"Set cursor theme to '{args.cursor}'?"
        ):
            info("Change cancelled.")
            return 0

    if args.icons:
        themes = discover_icon_themes()

        print(
            color(
                "Installed application icon themes:",
                Colors.BOLD
            )
        )
        print()

        if themes:
            for theme in themes:
                print(f"  • {theme}")
        else:
            print(
                "  No installed application icon themes found."
            )

        print()

        if not ask_confirmation(
            f"Set application icon theme to '{args.icons}'?"
        ):
            info("Change cancelled.")
            return 0

    if not automatic_backup():
        return 1

    success_count = 0

    if args.cursor:
        if set_cursor_theme(args.cursor):
            success(
                f"Cursor theme set to: {args.cursor}"
            )
            success_count += 1
        else:
            error(
                "Cursor theme could not be changed."
            )

    if args.icons:
        if set_icon_theme(args.icons):
            success(
                f"Application icon theme set to: "
                f"{args.icons}"
            )
            success_count += 1
        else:
            error(
                "Application icon theme could not be changed."
            )

    if success_count:
        info(
            "You may need to restart applications "
            "for changes to appear."
        )

    return 0 if success_count else 1


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Cozy Theme Tool - change Linux cursor and "
            "application icon themes."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    set_parser = subparsers.add_parser(
        "set",
        help="Change cursor and/or icon theme"
    )

    set_parser.add_argument(
        "--cursor",
        metavar="THEME",
        help="Set the cursor/mouse theme"
    )

    set_parser.add_argument(
        "--icons",
        metavar="THEME",
        help="Set the application icon theme"
    )

    subparsers.add_parser(
        "current",
        help="Show current theme configuration"
    )

    themes_parser = subparsers.add_parser(
        "themes",
        help="List installed themes"
    )

    themes_parser.add_argument(
        "type",
        choices=["cursor", "icons"],
        help="Theme type to list"
    )

    subparsers.add_parser(
        "backups",
        help="List .backup files"
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore a .backup file"
    )

    restore_parser.add_argument(
        "backup",
        help="Backup filename or number"
    )

    delete_parser = subparsers.add_parser(
        "delete-backup",
        help="Delete a backup"
    )

    delete_parser.add_argument(
        "backup",
        help="Backup filename or number"
    )

    subparsers.add_parser(
        "menu",
        help="Open the interactive menu"
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        menu()
        return 0

    if args.command == "menu":
        menu()
        return 0

    if args.command == "current":
        banner()
        show_current()
        print()
        return 0

    if args.command == "themes":
        command_list_themes(args.type)
        return 0

    if args.command == "backups":
        list_backups()
        return 0

    if args.command == "restore":
        return 0 if restore_backup(args.backup) else 1

    if args.command == "delete-backup":
        return 0 if delete_backup(args.backup) else 1

    if args.command == "set":
        return command_set(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(130)
# not tested
