import argparse
import configparser
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "Cozy Linux Settings"
BRAND = "Made with ❤️ by Cozy"

SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR
HOME = Path.home()

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
CURSOR_INDEX = HOME / ".icons" / "default" / "index.theme"
XFCE_XSETTINGS = "xsettings"
KDE_CONFIG = HOME / ".config" / "kdeglobals"


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
    print(color("╔══════════════════════════════════════════════╗", Colors.MAGENTA))
    print(color("║             COZY LINUX SETTINGS              ║", Colors.MAGENTA))
    print(color("╚══════════════════════════════════════════════╝", Colors.MAGENTA))
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


def command_exists(command):
    return shutil.which(command) is not None


def run_command(command, timeout=10):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except (OSError, subprocess.SubprocessError):
        return 1, "", ""


def ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        error(f"Could not read {path}: {exc}")
        return None


def write_text(path, content):
    try:
        ensure_parent(path)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError as exc:
        error(f"Could not write {path}: {exc}")
        return False


def detect_desktop():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    session = os.environ.get("DESKTOP_SESSION", "")
    desktop_text = f"{desktop}:{session}".lower()

    if "gnome" in desktop_text:
        return "GNOME"

    if "kde" in desktop_text or "plasma" in desktop_text:
        return "KDE Plasma"

    if "xfce" in desktop_text:
        return "XFCE"

    if "cinnamon" in desktop_text:
        return "Cinnamon"

    if "mate" in desktop_text:
        return "MATE"

    if "lxqt" in desktop_text:
        return "LXQt"

    if "lxde" in desktop_text:
        return "LXDE"

    if "budgie" in desktop_text:
        return "Budgie"

    if command_exists("gnome-shell"):
        return "GNOME"

    if command_exists("plasmashell"):
        return "KDE Plasma"

    if command_exists("xfce4-session"):
        return "XFCE"

    if command_exists("cinnamon-session"):
        return "Cinnamon"

    if command_exists("mate-session"):
        return "MATE"

    if command_exists("lxqt-session"):
        return "LXQt"

    return "Generic Linux"


def get_session_type():
    return os.environ.get("XDG_SESSION_TYPE", "unknown")


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


def set_ini_value(path, section, key, value):
    parser = configparser.ConfigParser()

    if path.exists():
        try:
            parser.read(path, encoding="utf-8")
        except configparser.Error as exc:
            error(f"Could not parse {path}: {exc}")
            return False

    if not parser.has_section(section):
        parser.add_section(section)

    parser.set(section, key, str(value))

    try:
        ensure_parent(path)

        with path.open("w", encoding="utf-8") as file:
            parser.write(file)

        return True

    except OSError as exc:
        error(f"Could not write {path}: {exc}")
        return False


def gsettings_get(schema, key):
    if not command_exists("gsettings"):
        return None

    code, output, _ = run_command(
        ["gsettings", "get", schema, key]
    )

    if code != 0:
        return None

    return output


def gsettings_set(schema, key, value):
    if not command_exists("gsettings"):
        return False

    code, _, stderr = run_command(
        ["gsettings", "set", schema, key, value]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def kde_command():
    if command_exists("kwriteconfig6"):
        return "kwriteconfig6"

    if command_exists("kwriteconfig5"):
        return "kwriteconfig5"

    return None


def kde_read(group, key):
    command = kde_command()

    if not command:
        return None

    if command == "kwriteconfig6":
        read_command = "kreadconfig6"
    else:
        read_command = "kreadconfig5"

    if not command_exists(read_command):
        return None

    code, output, _ = run_command(
        [
            read_command,
            "--file",
            "kdeglobals",
            "--group",
            group,
            "--key",
            key
        ]
    )

    if code != 0:
        return None

    return output


def kde_write(group, key, value):
    command = kde_command()

    if not command:
        return False

    code, _, stderr = run_command(
        [
            command,
            "--file",
            "kdeglobals",
            "--group",
            group,
            "--key",
            key,
            str(value)
        ]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def xfce_get(channel, property_name):
    if not command_exists("xfconf-query"):
        return None

    code, output, _ = run_command(
        [
            "xfconf-query",
            "-c",
            channel,
            "-p",
            property_name
        ]
    )

    if code != 0:
        return None

    return output


def xfce_set(channel, property_name, value):
    if not command_exists("xfconf-query"):
        return False

    code, _, stderr = run_command(
        [
            "xfconf-query",
            "-c",
            channel,
            "-p",
            property_name,
            "-s",
            str(value)
        ]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def get_gtk_font():
    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
            "Settings",
            "gtk-font-name"
        )

        if value:
            return value

    return None


def set_gtk_font(font):
    values = {
        "gtk-font-name": font
    }

    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-font-name",
            values["gtk-font-name"]
        ):
            changed = True

    return changed


def get_gtk_theme():
    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
            "Settings",
            "gtk-theme-name"
        )

        if value:
            return value

    return None


def set_gtk_theme(theme):
    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-theme-name",
            theme
        ):
            changed = True

    return changed


def get_icon_theme():
    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
            "Settings",
            "gtk-icon-theme"
        )

        if value:
            return value

    return None


def set_icon_theme(theme):
    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-icon-theme",
            theme
        ):
            changed = True

    return changed


def get_cursor_theme():
    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
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

    return None


def set_cursor_theme(theme):
    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-cursor-theme-name",
            theme
        ):
            changed = True

    if write_text(
        CURSOR_INDEX,
        "[Icon Theme]\n"
        f"Inherits={theme}\n"
    ):
        changed = True

    return changed


def discover_theme_directories():
    return [
        HOME / ".themes",
        HOME / ".icons",
        HOME / ".local" / "share" / "themes",
        HOME / ".local" / "share" / "icons",
        Path("/usr/share/themes"),
        Path("/usr/share/icons"),
        Path("/usr/local/share/themes"),
        Path("/usr/local/share/icons")
    ]


def discover_gtk_themes():
    themes = set()

    for directory in discover_theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                if (child / "gtk-3.0").exists():
                    themes.add(child.name)

                elif (child / "gtk-4.0").exists():
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.lower)


def discover_icon_themes():
    themes = set()

    for directory in discover_theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if child.is_dir() and (child / "index.theme").exists():
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.lower)


def discover_cursor_themes():
    themes = set()

    for directory in discover_theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                if (child / "cursors").is_dir():
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(themes, key=str.lower)


def discover_fonts():
    directories = [
        HOME / ".fonts",
        HOME / ".local" / "share" / "fonts",
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts")
    ]

    fonts = set()

    for directory in directories:
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue

                if path.suffix.lower() not in (
                    ".ttf",
                    ".otf",
                    ".ttc"
                ):
                    continue

                name = path.stem.replace("-", " ").replace("_", " ")
                fonts.add(name)

        except (OSError, PermissionError):
            continue

    return sorted(fonts, key=str.lower)


def backup_filename():
    now = datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )

    return BACKUP_DIR / f"cozy-backup-{now}.backup"


def backup_paths():
    return [
        GTK3_SETTINGS,
        GTK4_SETTINGS,
        CURSOR_INDEX,
        KDE_CONFIG,
        HOME / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xsettings.xml",
        HOME / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfwm4.xml"
    ]


def create_backup():
    backup_path = backup_filename()

    snapshot = {
        "format": 2,
        "created": datetime.datetime.now().isoformat(),
        "tool": APP_NAME,
        "brand": BRAND,
        "desktop": detect_desktop(),
        "files": {},
        "gsettings": {},
        "kde": {},
        "xfce": {}
    }

    for path in backup_paths():
        key = str(path)

        if path.exists():
            content = read_text(path)

            if content is None:
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

    gsettings_keys = [
        (
            "org.gnome.desktop.interface",
            "font-name"
        ),
        (
            "org.gnome.desktop.interface",
            "gtk-theme"
        ),
        (
            "org.gnome.desktop.interface",
            "icon-theme"
        ),
        (
            "org.gnome.desktop.interface",
            "cursor-theme"
        ),
        (
            "org.gnome.desktop.interface",
            "color-scheme"
        ),
        (
            "org.gnome.desktop.interface",
            "text-scaling-factor"
        ),
        (
            "org.cinnamon.desktop.interface",
            "font-name"
        ),
        (
            "org.cinnamon.desktop.interface",
            "gtk-theme"
        ),
        (
            "org.cinnamon.desktop.interface",
            "icon-theme"
        ),
        (
            "org.cinnamon.desktop.interface",
            "cursor-theme"
        ),
        (
            "org.mate.interface",
            "font-name"
        ),
        (
            "org.mate.interface",
            "gtk-theme"
        ),
        (
            "org.mate.interface",
            "icon-theme"
        ),
        (
            "org.mate.peripherals-mouse",
            "cursor-theme"
        )
    ]

    for schema, key in gsettings_keys:
        value = gsettings_get(schema, key)

        if value is not None:
            snapshot["gsettings"][f"{schema}|{key}"] = value

    kde_values = [
        ("General", "ColorScheme"),
        ("General", "font"),
        ("Icons", "Theme"),
        ("KDE", "widgetStyle")
    ]

    for group, key in kde_values:
        value = kde_read(group, key)

        if value is not None:
            snapshot["kde"][f"{group}|{key}"] = value

    xfce_values = [
        ("xsettings", "/Gtk/FontName"),
        ("xsettings", "/Net/ThemeName"),
        ("xsettings", "/Net/IconThemeName"),
        ("xsettings", "/Gtk/CursorThemeName"),
        ("xsettings", "/Gtk/CursorThemeSize"),
        ("xsettings", "/Xft/DPI")
    ]

    for channel, key in xfce_values:
        value = xfce_get(channel, key)

        if value is not None:
            snapshot["xfce"][f"{channel}|{key}"] = value

    try:
        ensure_parent(backup_path)

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
    info("Creating backup before changing settings...")

    backup = create_backup()

    if backup:
        success(
            f"Backup created in script directory: {backup.name}"
        )
        return True

    error("Backup failed.")
    return False


def list_backups():
    backups = sorted(
        BACKUP_DIR.glob("cozy-backup-*.backup"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("No backups found in the Python script directory.")
        return

    print()
    print(color("Available backups", Colors.BOLD))
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
        BACKUP_DIR.glob("cozy-backup-*.backup"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

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

    if data.get("format") not in (1, 2):
        error("Unsupported backup format.")
        return False

    files = data.get("files", {})

    if not isinstance(files, dict):
        error("Backup file data is invalid.")
        return False

    safety_backup = create_backup()

    if safety_backup:
        success(
            f"Safety backup created: {safety_backup.name}"
        )
    else:
        error("Could not create safety backup.")
        return False

    try:
        for filename, file_data in files.items():
            target = Path(filename)

            if not isinstance(file_data, dict):
                raise ValueError(
                    f"Invalid backup entry: {filename}"
                )

            exists = file_data.get("exists", False)

            if exists:
                content = file_data.get("content")

                if not isinstance(content, str):
                    raise ValueError(
                        f"Invalid content: {filename}"
                    )

                ensure_parent(target)

                target.write_text(
                    content,
                    encoding="utf-8"
                )

            elif target.exists():
                target.unlink()

        for identifier, value in data.get(
            "gsettings",
            {}
        ).items():
            if "|" not in identifier:
                continue

            schema, key = identifier.split("|", 1)

            if command_exists("gsettings"):
                run_command(
                    [
                        "gsettings",
                        "set",
                        schema,
                        key,
                        value
                    ]
                )

        for identifier, value in data.get(
            "kde",
            {}
        ).items():
            if "|" not in identifier:
                continue

            group, key = identifier.split("|", 1)

            kde_write(
                group,
                key,
                value
            )

        for identifier, value in data.get(
            "xfce",
            {}
        ).items():
            if "|" not in identifier:
                continue

            channel, key = identifier.split("|", 1)

            xfce_set(
                channel,
                key,
                value
            )

        success(f"Restored {path.name}")
        return True

    except (OSError, ValueError) as exc:
        error(f"Restore failed: {exc}")
        error(
            f"Safety backup remains available as "
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


def get_dark_mode():
    desktop = detect_desktop()

    if desktop in ("GNOME", "Cinnamon", "MATE"):
        schema = {
            "GNOME": "org.gnome.desktop.interface",
            "Cinnamon": "org.cinnamon.desktop.interface",
            "MATE": "org.mate.interface"
        }[desktop]

        value = gsettings_get(
            schema,
            "color-scheme"
        )

        if value:
            return value

    if desktop == "XFCE":
        theme = xfce_get(
            "xsettings",
            "/Net/ThemeName"
        )

        if theme:
            if "dark" in theme.lower():
                return "dark"

            return "light"

    return "unknown"


def set_dark_mode(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "color-scheme",
            "'prefer-dark'" if value == "dark" else "'default'"
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "color-scheme",
            "'prefer-dark'" if value == "dark" else "'prefer-light'"
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "gtk-theme",
            "'Adwaita-dark'" if value == "dark" else "'Adwaita'"
        )

    if desktop == "XFCE":
        current = xfce_get(
            "xsettings",
            "/Net/ThemeName"
        )

        if not current:
            return False

        if value == "dark":
            if "dark" not in current.lower():
                candidate = f"{current}-dark"
            else:
                candidate = current
        else:
            candidate = current.replace(
                "-Dark",
                ""
            ).replace(
                "-dark",
                ""
            )

        return xfce_set(
            "xsettings",
            "/Net/ThemeName",
            candidate
        )

    return False


def get_font():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "font-name"
        )

    if desktop == "Cinnamon":
        return gsettings_get(
            "org.cinnamon.desktop.interface",
            "font-name"
        )

    if desktop == "MATE":
        return gsettings_get(
            "org.mate.interface",
            "font-name"
        )

    if desktop == "XFCE":
        return xfce_get(
            "xsettings",
            "/Gtk/FontName"
        )

    if desktop == "KDE Plasma":
        return kde_read(
            "General",
            "font"
        )

    return get_gtk_font()


def set_font(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "font-name",
            f"'{value}'"
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "font-name",
            f"'{value}'"
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "font-name",
            f"'{value}'"
        )

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Gtk/FontName",
            value
        )

    if desktop == "KDE Plasma":
        return kde_write(
            "General",
            "font",
            value
        )

    return set_gtk_font(value)


def get_theme():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "gtk-theme"
        )

    if desktop == "Cinnamon":
        return gsettings_get(
            "org.cinnamon.desktop.interface",
            "gtk-theme"
        )

    if desktop == "MATE":
        return gsettings_get(
            "org.mate.interface",
            "gtk-theme"
        )

    if desktop == "XFCE":
        return xfce_get(
            "xsettings",
            "/Net/ThemeName"
        )

    if desktop == "KDE Plasma":
        return kde_read(
            "General",
            "ColorScheme"
        )

    return get_gtk_theme()


def set_theme(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "gtk-theme",
            f"'{value}'"
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "gtk-theme",
            f"'{value}'"
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "gtk-theme",
            f"'{value}'"
        )

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Net/ThemeName",
            value
        )

    if desktop == "KDE Plasma":
        return kde_write(
            "General",
            "ColorScheme",
            value
        )

    return set_gtk_theme(value)


def get_icon_theme():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "icon-theme"
        )

    if desktop == "Cinnamon":
        return gsettings_get(
            "org.cinnamon.desktop.interface",
            "icon-theme"
        )

    if desktop == "MATE":
        return gsettings_get(
            "org.mate.interface",
            "icon-theme"
        )

    if desktop == "XFCE":
        return xfce_get(
            "xsettings",
            "/Net/IconThemeName"
        )

    if desktop == "KDE Plasma":
        return kde_read(
            "Icons",
            "Theme"
        )

    return get_icon_theme()


def set_icon(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "icon-theme",
            f"'{value}'"
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "icon-theme",
            f"'{value}'"
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "icon-theme",
            f"'{value}'"
        )

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Net/IconThemeName",
            value
        )

    if desktop == "KDE Plasma":
        return kde_write(
            "Icons",
            "Theme",
            value
        )

    return set_icon_theme(value)


def get_cursor():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "cursor-theme"
        )

    if desktop == "Cinnamon":
        return gsettings_get(
            "org.cinnamon.desktop.interface",
            "cursor-theme"
        )

    if desktop == "MATE":
        return gsettings_get(
            "org.mate.peripherals-mouse",
            "cursor-theme"
        )

    if desktop == "XFCE":
        return xfce_get(
            "xsettings",
            "/Gtk/CursorThemeName"
        )

    return get_cursor_theme()


def set_cursor(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "cursor-theme",
            f"'{value}'"
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "cursor-theme",
            f"'{value}'"
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.peripherals-mouse",
            "cursor-theme",
            f"'{value}'"
        )

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Gtk/CursorThemeName",
            value
        )

    return set_cursor_theme(value)


def get_scale():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "text-scaling-factor"
        )

    if desktop == "XFCE":
        dpi = xfce_get(
            "xsettings",
            "/Xft/DPI"
        )

        if dpi:
            try:
                return str(round(int(dpi) / 96, 2))
            except ValueError:
                return dpi

    return "1.0"


def set_scale(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "text-scaling-factor",
            value
        )

    if desktop == "XFCE":
        try:
            dpi = int(round(float(value) * 96))
        except ValueError:
            return False

        return xfce_set(
            "xsettings",
            "/Xft/DPI",
            str(dpi)
        )

    return False


def get_settings():
    desktop = detect_desktop()

    settings = [
        {
            "name": "Application Icon Theme",
            "key": "icons",
            "get": get_icon_theme,
            "set": set_icon,
            "options": discover_icon_themes
        },
        {
            "name": "Color Theme",
            "key": "theme",
            "get": get_theme,
            "set": set_theme,
            "options": discover_gtk_themes
        },
        {
            "name": "Cursor Theme",
            "key": "cursor",
            "get": get_cursor,
            "set": set_cursor,
            "options": discover_cursor_themes
        },
        {
            "name": "Dark Mode",
            "key": "dark_mode",
            "get": get_dark_mode,
            "set": set_dark_mode,
            "options": lambda: ["dark", "light"]
        },
        {
            "name": "Font",
            "key": "font",
            "get": get_font,
            "set": set_font,
            "options": discover_fonts
        },
        {
            "name": "Interface Scale",
            "key": "scale",
            "get": get_scale,
            "set": set_scale,
            "options": lambda: [
                "0.75",
                "0.80",
                "0.90",
                "1.00",
                "1.10",
                "1.20",
                "1.25",
                "1.50",
                "1.75",
                "2.00"
            ]
        }
    ]

    if desktop == "KDE Plasma":
        settings = [
            setting
            for setting in settings
            if setting["key"] not in ("dark_mode", "scale")
        ]

    if desktop == "MATE":
        settings = [
            setting
            for setting in settings
            if setting["key"] != "scale"
        ]

    if desktop == "LXQt":
        settings = [
            setting
            for setting in settings
            if setting["key"] in (
                "font",
                "icons",
                "cursor"
            )
        ]

    if desktop == "Generic Linux":
        settings = [
            setting
            for setting in settings
            if setting["key"] in (
                "font",
                "icons",
                "cursor",
                "theme"
            )
        ]

    return sorted(
        settings,
        key=lambda item: item["name"].lower()
    )


def verify_setting(setting, expected):
    try:
        current = setting["get"]()
    except Exception:
        return False

    if current is None:
        return False

    return str(current).strip("'\"") == str(expected).strip("'\"")


def choose_setting(settings):
    print()
    print(color("Available settings", Colors.BOLD))
    print()

    for index, setting in enumerate(settings, 1):
        try:
            current = setting["get"]()
        except Exception:
            current = None

        if current is None:
            current = "not configured"

        print(
            f"  {index:2}. "
            f"{setting['name']} "
            f"{color(f'[{current}]', Colors.DIM)}"
        )

    print()
    print("   0. Back")
    print()

    while True:
        try:
            choice = input("Select a setting: ").strip()
        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(settings):
                return settings[number - 1]

        print("Please enter a valid number.")


def choose_option(setting):
    options = setting["options"]()

    if not options:
        warning(
            f"No available options were found for "
            f"{setting['name']}."
        )
        return None

    options = sorted(
        set(str(option) for option in options),
        key=str.lower
    )

    current = setting["get"]()

    print()
    print(color(setting["name"], Colors.BOLD))
    print()

    if current is not None:
        print(f"Current: {current}")
        print()

    for index, option in enumerate(options, 1):
        marker = ""

        if current is not None:
            if str(current).strip("'\"") == str(option).strip("'\""):
                marker = "  ← current"

        print(
            f"  {index:2}. {option}{marker}"
        )

    print()
    print("   0. Back")
    print()

    while True:
        try:
            choice = input("Select an option: ").strip()
        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(options):
                return options[number - 1]

        print("Please enter a valid number.")


def change_setting(setting):
    value = choose_option(setting)

    if value is None:
        return

    print()
    print(
        f"Change {setting['name']} to: "
        f"{value}"
    )

    if not ask_confirmation("Apply this change?"):
        info("Change cancelled.")
        return

    if not automatic_backup():
        return

    try:
        changed = setting["set"](value)
    except Exception as exc:
        error(
            f"Setting could not be changed: {exc}"
        )
        return

    if not changed:
        error(
            f"{setting['name']} could not be changed."
        )
        return

    if verify_setting(setting, value):
        success(
            f"{setting['name']} changed to {value}"
        )
    else:
        warning(
            f"{setting['name']} was written, "
            f"but verification failed."
        )

    info(
        "Some applications may need to be restarted "
        "for the change to appear."
    )


def show_current():
    desktop = detect_desktop()
    session = get_session_type()

    print()
    print(color("System information", Colors.BOLD))
    print()
    print(f"  Desktop : {desktop}")
    print(f"  Session : {session}")
    print(f"  Script  : {SCRIPT_DIR}")
    print()

    print(color("Current settings", Colors.BOLD))
    print()

    for setting in get_settings():
        try:
            value = setting["get"]()
        except Exception:
            value = None

        if value is None or value == "":
            value = "not configured"

        print(
            f"  {setting['name']:<25} {value}"
        )


def settings_menu():
    while True:
        banner()

        desktop = detect_desktop()

        print(
            color(
                f"Desktop detected: {desktop}",
                Colors.CYAN
            )
        )

        settings = get_settings()

        setting = choose_setting(settings)

        if setting is None:
            return

        change_setting(setting)

        pause()


def restore_interactive():
    list_backups()

    backups = sorted(
        BACKUP_DIR.glob("cozy-backup-*.backup"),
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
        choice = input(
            "Enter backup number or filename "
            "(0 to cancel): "
        ).strip()
    except KeyboardInterrupt:
        print()
        return

    if choice == "0":
        return

    path = find_backup(choice)

    if path is None:
        error("Backup not found.")
        return

    if not ask_confirmation(
        f"Delete {path.name}?"
    ):
        info("Deletion cancelled.")
        return

    delete_backup(choice)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Cozy Linux Settings - a terminal-based "
            "Linux desktop settings tool."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    subparsers.add_parser(
        "menu",
        help="Open the settings menu"
    )

    subparsers.add_parser(
        "current",
        help="Show current desktop and settings"
    )

    subparsers.add_parser(
        "backups",
        help="List backups"
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore a backup"
    )

    restore_parser.add_argument(
        "backup",
        help="Backup number or filename"
    )

    delete_parser = subparsers.add_parser(
        "delete-backup",
        help="Delete a backup"
    )

    delete_parser.add_argument(
        "backup",
        help="Backup number or filename"
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        settings_menu()
        return 0

    if args.command == "menu":
        settings_menu()
        return 0

    if args.command == "current":
        banner()
        show_current()
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(130)
# not tested
