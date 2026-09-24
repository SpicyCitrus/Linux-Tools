import argparse
import configparser
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


APP_NAME = "Cozy Theme Tool"
BRAND = "Made with ❤️ by Cozy"
BACKUP_FORMAT = 2

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
CURSOR_INDEX = HOME / ".icons" / "default" / "index.theme"

MANAGED_FILES = (
    GTK3_SETTINGS,
    GTK4_SETTINGS,
    CURSOR_INDEX,
)


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
        error(f"Cannot create backup directory: {exc}")
        return False


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        error(f"Could not read {path}: {exc}")
        return None


def atomic_write_text(path, content):
    ensure_parent(path)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, path)
        return True

    except OSError as exc:
        error(f"Could not write {path}: {exc}")

        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

        return False


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
        with tempfile.TemporaryFile(
            mode="w+",
            encoding="utf-8",
        ) as file:
            parser.write(file)
            file.seek(0)
            output = file.read()

        return atomic_write_text(path, output)

    except (OSError, configparser.Error) as exc:
        error(f"Could not prepare {path}: {exc}")
        return False


def discover_fonts():
    try:
        result = subprocess.run(
            [
                "fc-list",
                ":",
                "family",
                "-f",
                "%{family}\\n",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (
        FileNotFoundError,
        subprocess.SubprocessError,
        OSError,
    ):
        return []

    fonts = set()

    for line in result.stdout.splitlines():
        for family in line.split(","):
            family = family.strip()

            if family:
                fonts.add(family)

    return sorted(fonts, key=str.casefold)


def get_current_font():
    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-font-name",
        )

        if value:
            return value

    return None


def set_font(font):
    values = {
        ("Settings", "gtk-font-name"): font,
    }

    results = []

    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        results.append(
            set_ini_values(settings, values)
        )

    return all(results)


def get_current_cursor_theme():
    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-cursor-theme-name",
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
        ("Settings", "gtk-cursor-theme-name"): theme,
    }

    results = []

    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        results.append(
            set_ini_values(settings, values)
        )

    try:
        content = (
            "[Icon Theme]\n"
            f"Inherits={theme}\n"
        )

        cursor_ok = atomic_write_text(
            CURSOR_INDEX,
            content,
        )
    except OSError as exc:
        error(f"Could not configure cursor theme: {exc}")
        cursor_ok = False

    return all(results) and cursor_ok


def get_current_icon_theme():
    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-icon-theme",
        )

        if value:
            return value

    return None


def set_icon_theme(theme):
    values = {
        ("Settings", "gtk-icon-theme"): theme,
    }

    results = []

    for settings in (GTK3_SETTINGS, GTK4_SETTINGS):
        results.append(
            set_ini_values(settings, values)
        )

    return all(results)


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

    return sorted(themes, key=str.casefold)


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

                if (
                    cursor_directory.exists()
                    and cursor_directory.is_dir()
                ):
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.casefold)


def timestamp():
    return datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )


def backup_filename():
    return BACKUP_DIR / f"cozy-backup-{timestamp()}.backup"


def normalized_managed_path(path):
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser().absolute()


def create_backup():
    if not ensure_backup_directory():
        return None

    snapshot = {
        "format": BACKUP_FORMAT,
        "created": datetime.datetime.now().astimezone().isoformat(),
        "tool": APP_NAME,
        "brand": BRAND,
        "files": {},
    }

    for path in MANAGED_FILES:
        key = str(normalized_managed_path(path))

        if path.exists():
            if not path.is_file():
                error(f"Cannot back up non-file path: {path}")
                return None

            content = read_text(path)

            if content is None:
                error(f"Could not back up {path}")
                return None

            snapshot["files"][key] = {
                "exists": True,
                "content": content,
            }
        else:
            snapshot["files"][key] = {
                "exists": False,
                "content": None,
            }

    backup_path = backup_filename()

    try:
        serialized = json.dumps(
            snapshot,
            indent=2,
            ensure_ascii=False,
        )

        if not atomic_write_text(
            backup_path,
            serialized,
        ):
            return None

        return backup_path

    except (OSError, TypeError, ValueError) as exc:
        error(f"Could not create backup: {exc}")
        return None


def automatic_backup():
    print()
    info("Creating automatic backup...")

    backup = create_backup()

    if backup:
        success(
            f"Automatic backup created: {backup.name}"
        )
        return True

    warning("The automatic backup failed.")
    print()
    print(
        "Changes cannot safely continue without a backup."
    )
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
        success(
            f"Manual backup created: {manual_backup.name}"
        )
        return True

    error("Manual backup also failed.")
    print()

    if ask_confirmation("Continue WITHOUT a backup?"):
        warning(
            "You chose to continue without a backup."
        )
        return True

    error("Changes cancelled.")
    return False


def get_backups():
    if not BACKUP_DIR.exists():
        return []

    try:
        backups = list(BACKUP_DIR.glob("*.backup"))
    except OSError:
        return []

    def modification_time(path):
        try:
            return path.stat().st_mtime
        except OSError:
            return 0

    return sorted(
        backups,
        key=modification_time,
        reverse=True,
    )


def list_backups():
    if not ensure_backup_directory():
        return

    backups = get_backups()

    if not backups:
        print("No .backup files found.")
        print(f"Backup directory: {BACKUP_DIR}")
        return

    print()
    print(color("Available backups:", Colors.BOLD))
    print()
    print(f"  Location: {BACKUP_DIR}")
    print()

    for index, path in enumerate(backups, 1):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        print(
            f"  {index:2}. {path.name} "
            f"({size:,} bytes)"
        )


def find_backup(identifier):
    backups = get_backups()

    if not backups:
        return None

    if identifier.isdigit():
        number = int(identifier)

        if 1 <= number <= len(backups):
            return backups[number - 1]

        return None

    candidate = BACKUP_DIR / Path(identifier).name

    if (
        candidate.exists()
        and candidate.is_file()
        and candidate.suffix == ".backup"
        and candidate.parent == BACKUP_DIR
    ):
        return candidate

    return None


def load_backup(path):
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        error(f"Could not read backup: {exc}")
        return None

    if not isinstance(data, dict):
        error("Backup is not a valid object.")
        return None

    if data.get("format") not in (1, BACKUP_FORMAT):
        error(
            "Unsupported backup format: "
            f"{data.get('format')}"
        )
        return None

    files = data.get("files")

    if not isinstance(files, dict):
        error("Backup is missing its file data.")
        return None

    allowed = {
        str(normalized_managed_path(path))
        for path in MANAGED_FILES
    }

    for filename in files:
        try:
            normalized = str(
                normalized_managed_path(Path(filename))
            )
        except OSError:
            error(f"Invalid backup path: {filename}")
            return None

        if normalized not in allowed:
            error(
                "Backup contains an unmanaged file: "
                f"{filename}"
            )
            return None

    return data


def restore_snapshot(data):
    files = data["files"]

    for path in MANAGED_FILES:
        filename = str(
            normalized_managed_path(path)
        )

        file_data = files.get(filename)

        if file_data is None:
            for old_filename, candidate in files.items():
                try:
                    if (
                        normalized_managed_path(
                            Path(old_filename)
                        )
                        == normalized_managed_path(path)
                    ):
                        file_data = candidate
                        break
                except OSError:
                    continue

        if file_data is None:
            continue

        if not isinstance(file_data, dict):
            raise ValueError(
                f"Invalid file record for {path}"
            )

        exists = file_data.get("exists", False)

        if exists:
            content = file_data.get("content")

            if not isinstance(content, str):
                raise ValueError(
                    f"Invalid content for {path}"
                )

            if not atomic_write_text(path, content):
                raise OSError(
                    f"Could not restore {path}"
                )

        elif path.exists():
            if not path.is_file():
                raise OSError(
                    f"Cannot remove non-file path: {path}"
                )

            path.unlink()

    return True


def restore_backup(identifier):
    path = find_backup(identifier)

    if path is None:
        error("Backup not found.")
        return False

    data = load_backup(path)

    if data is None:
        return False

    print()
    info(
        "Creating safety backup before restoring..."
    )

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
                "Manual safety backup created: "
                f"{safety_backup.name}"
            )
    else:
        success(
            "Safety backup created: "
            f"{safety_backup.name}"
        )

    try:
        restore_snapshot(data)
        success(f"Restored: {path.name}")
        return True

    except (OSError, ValueError) as exc:
        error(f"Restore failed: {exc}")

        if safety_backup:
            print()
            warning(
                "The restore may have been partially applied."
            )
            info(
                "Your pre-restore backup is:"
            )
            print(f"  {safety_backup.name}")

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
    font = get_current_font()

    print()
    print(
        color(
            "Current theme configuration",
            Colors.BOLD,
        )
    )
    print()

    print(
        "  Font         : "
        + (
            font
            if font
            else color("not configured", Colors.DIM)
        )
    )

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


def choose_item(items, title, prompt):
    print()
    print(color(title, Colors.BOLD))
    print()

    if not items:
        warning("Nothing was found.")
        return None

    for index, item in enumerate(items, 1):
        print(f"  {index:3}. {item}")

    print()
    print("    0. Cancel")
    print()

    while True:
        try:
            choice = input(prompt).strip()

        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(items):
                return items[number - 1]

        print("Please enter a valid number.")


def choose_theme(themes, title):
    return choose_item(
        themes,
        title,
        "Select a theme: ",
    )


def change_font_interactive():
    fonts = discover_fonts()

    if not fonts:
        warning(
            "Could not find installed fonts using fc-list."
        )
        print()
        print(
            'Use: python cozy_theme.py set --font "Noto Sans 11"'
        )
        return

    font_family = choose_item(
        fonts,
        "Installed font families",
        "Select a font: ",
    )

    if not font_family:
        return

    print()

    try:
        size = input("Font size [11]: ").strip()
    except KeyboardInterrupt:
        print()
        return

    if not size:
        size = "11"

    if not size.isdigit() or int(size) <= 0:
        error("Font size must be a positive whole number.")
        return

    font = f"{font_family} {size}"

    print()
    print(f"Selected font: {font}")

    if not ask_confirmation("Apply this font?"):
        info("Change cancelled.")
        return

    if not automatic_backup():
        return

    if set_font(font):
        success(
            f"Application font changed to: {font}"
        )
        info(
            "Restart GTK applications for the change "
            "to appear."
        )
    else:
        error("Application font could not be changed.")


def change_cursor_interactive():
    themes = discover_cursor_themes()

    theme = choose_theme(
        themes,
        "Installed cursor themes",
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
            "Restart applications or log in again if "
            "the change does not appear immediately."
        )
    else:
        error("Cursor theme could not be changed.")


def change_icon_interactive():
    themes = discover_icon_themes()

    theme = choose_theme(
        themes,
        "Installed application icon themes",
    )

    if not theme:
        return

    print()
    print(f"Selected icon theme: {theme}")

    if not automatic_backup():
        return

    if set_icon_theme(theme):
        success(
            "Application icon theme changed to: "
            f"{theme}"
        )
        info(
            "Restart applications for the change "
            "to appear."
        )
    else:
        error(
            "Application icon theme could not be changed."
        )


def change_all_interactive():
    fonts = discover_fonts()
    cursors = discover_cursor_themes()
    icons = discover_icon_themes()

    font_family = choose_item(
        fonts,
        "Installed font families",
        "Select a font: ",
    )

    if not font_family:
        return

    try:
        size = input("Font size [11]: ").strip()
    except KeyboardInterrupt:
        print()
        return

    if not size:
        size = "11"

    if not size.isdigit() or int(size) <= 0:
        error("Font size must be a positive whole number.")
        return

    cursor = choose_theme(
        cursors,
        "Installed cursor themes",
    )

    if not cursor:
        return

    icons_selected = choose_theme(
        icons,
        "Installed application icon themes",
    )

    if not icons_selected:
        return

    font = f"{font_family} {size}"

    print()
    print(f"Selected font   : {font}")
    print(f"Selected cursor : {cursor}")
    print(f"Selected icons  : {icons_selected}")
    print()

    if not ask_confirmation("Apply all changes?"):
        info("Changes cancelled.")
        return

    if not automatic_backup():
        return

    font_ok = set_font(font)
    cursor_ok = set_cursor_theme(cursor)
    icon_ok = set_icon_theme(icons_selected)

    print()

    if font_ok:
        success(f"Font changed to: {font}")
    else:
        error("Font could not be changed.")

    if cursor_ok:
        success(
            f"Cursor theme changed to: {cursor}"
        )
    else:
        error("Cursor theme could not be changed.")

    if icon_ok:
        success(
            "Application icon theme changed to: "
            f"{icons_selected}"
        )
    else:
        error(
            "Application icon theme could not be changed."
        )

    if font_ok or cursor_ok or icon_ok:
        info(
            "Restart GTK applications for all changes "
            "to appear."
        )


def restore_interactive():
    list_backups()

    backups = get_backups()

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

    if not get_backups():
        return

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
        print("  1. Change application font")
        print("  2. Change cursor/mouse theme")
        print("  3. Change application icon theme")
        print("  4. Change font, cursor and icons")
        print("  5. Restore backup")
        print("  6. List backups")
        print("  7. Delete backup")
        print("  0. Exit")
        print()

        try:
            choice = input("Choose an option: ").strip()

        except KeyboardInterrupt:
            print()
            return

        if choice == "1":
            change_font_interactive()
            pause()

        elif choice == "2":
            change_cursor_interactive()
            pause()

        elif choice == "3":
            change_icon_interactive()
            pause()

        elif choice == "4":
            change_all_interactive()
            pause()

        elif choice == "5":
            restore_interactive()
            pause()

        elif choice == "6":
            list_backups()
            pause()

        elif choice == "7":
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


def command_list_fonts():
    fonts = discover_fonts()

    print(color("Installed font families:", Colors.BOLD))
    print()

    if not fonts:
        print("  No fonts found.")
        print(
            "  Make sure fontconfig/fc-list is installed."
        )
        return

    for font in fonts:
        print(f"  {font}")


def command_set(args):
    if (
        not args.cursor
        and not args.icons
        and not args.font
    ):
        error(
            "Specify --font, --cursor, --icons, "
            "or any combination."
        )
        return 1

    changes = []

    if args.font:
        changes.append(f"font '{args.font}'")

    if args.cursor:
        changes.append(
            f"cursor theme '{args.cursor}'"
        )

    if args.icons:
        changes.append(
            f"icon theme '{args.icons}'"
        )

    if args.font:
        print(
            color(
                "Requested GTK font:",
                Colors.BOLD,
            )
        )
        print(f"  {args.font}")
        print()

    if args.cursor:
        themes = discover_cursor_themes()

        print(
            color(
                "Installed cursor themes:",
                Colors.BOLD,
            )
        )
        print()

        if themes:
            for theme in themes:
                print(f"  • {theme}")
        else:
            print("  No installed cursor themes found.")

        print()

    if args.icons:
        themes = discover_icon_themes()

        print(
            color(
                "Installed application icon themes:",
                Colors.BOLD,
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
        "Apply " + ", ".join(changes) + "?"
    ):
        info("Changes cancelled.")
        return 0

    if not automatic_backup():
        return 1

    success_count = 0

    if args.font:
        if set_font(args.font):
            success(
                f"Font set to: {args.font}"
            )
            success_count += 1
        else:
            error("Font could not be changed.")

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
                "Application icon theme set to: "
                f"{args.icons}"
            )
            success_count += 1
        else:
            error(
                "Application icon theme could not be changed."
            )

    if success_count:
        info(
            "Restart GTK applications for changes "
            "to appear."
        )

    return 0 if success_count else 1


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Cozy Theme Tool - configure Linux GTK fonts, "
            "cursor themes and application icon themes."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    set_parser = subparsers.add_parser(
        "set",
        help=(
            "Change GTK font, cursor and/or icon theme"
        ),
    )

    set_parser.add_argument(
        "--font",
        metavar="FONT",
        help=(
            'Set the GTK application font, e.g. '
            '"Noto Sans 11"'
        ),
    )

    set_parser.add_argument(
        "--cursor",
        metavar="THEME",
        help="Set the cursor/mouse theme",
    )

    set_parser.add_argument(
        "--icons",
        metavar="THEME",
        help="Set the application icon theme",
    )

    subparsers.add_parser(
        "current",
        help="Show current theme configuration",
    )

    themes_parser = subparsers.add_parser(
        "themes",
        help="List installed themes",
    )

    themes_parser.add_argument(
        "type",
        choices=["cursor", "icons"],
        help="Theme type to list",
    )

    subparsers.add_parser(
        "fonts",
        help="List installed font families",
    )

    subparsers.add_parser(
        "backups",
        help="List backups",
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore a backup",
    )

    restore_parser.add_argument(
        "backup",
        help="Backup filename or number",
    )

    delete_parser = subparsers.add_parser(
        "delete-backup",
        help="Delete a backup",
    )

    delete_parser.add_argument(
        "backup",
        help="Backup filename or number",
    )

    subparsers.add_parser(
        "menu",
        help="Open the interactive menu",
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

    if args.command == "fonts":
        command_list_fonts()
        return 0

    if args.command == "themes":
        command_list_themes(args.type)
        return 0

    if args.command == "backups":
        list_backups()
        return 0

    if args.command == "restore":
        return (
            0
            if restore_backup(args.backup)
            else 1
        )

    if args.command == "delete-backup":
        return (
            0
            if delete_backup(args.backup)
            else 1
        )

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
