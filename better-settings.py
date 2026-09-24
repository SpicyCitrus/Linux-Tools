import argparse
import configparser
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "Cozy Settings"
BRAND = "Made with ❤️ by Cozy"

SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR
HOME = Path.home()

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
GTK2_SETTINGS = HOME / ".gtkrc-2.0"
CURSOR_INDEX = HOME / ".icons" / "default" / "index.theme"
KDE_GLOBALS = HOME / ".config" / "kdeglobals"
KDE_KDEGLOBALS = HOME / ".config" / "kdeglobals"
XFCE_XSETTINGS = HOME / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xsettings.xml"
XFCE_XFWM = HOME / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfwm4.xml"


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
    print(color("║                COZY SETTINGS                 ║", Colors.MAGENTA))
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


def run_command(command, timeout=15):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )

        return (
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip()
        )

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

    if "kde" in desktop_text or "plasma" in desktop_text:
        return "KDE Plasma"

    if "gnome" in desktop_text:
        return "GNOME"

    if "cinnamon" in desktop_text:
        return "Cinnamon"

    if "xfce" in desktop_text:
        return "XFCE"

    if "mate" in desktop_text:
        return "MATE"

    if "lxqt" in desktop_text:
        return "LXQt"

    if "lxde" in desktop_text:
        return "LXDE"

    if "budgie" in desktop_text:
        return "Budgie"

    if command_exists("plasmashell"):
        return "KDE Plasma"

    if command_exists("gnome-shell"):
        return "GNOME"

    if command_exists("cinnamon-session"):
        return "Cinnamon"

    if command_exists("xfce4-session"):
        return "XFCE"

    if command_exists("mate-session"):
        return "MATE"

    if command_exists("lxqt-session"):
        return "LXQt"

    return "Generic Linux"


def session_type():
    return os.environ.get("XDG_SESSION_TYPE", "unknown")


def get_ini_value(path, section, key):
    if not path.exists():
        return None

    parser = configparser.ConfigParser(
        interpolation=None
    )

    try:
        parser.read(path, encoding="utf-8")
    except (OSError, configparser.Error):
        return None

    if parser.has_option(section, key):
        return parser.get(section, key)

    return None


def set_ini_value(path, section, key, value):
    parser = configparser.ConfigParser(
        interpolation=None
    )

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


def gsettings_schema_exists(schema):
    if not command_exists("gsettings"):
        return False

    code, output, _ = run_command(
        ["gsettings", "list-keys", schema]
    )

    return code == 0 and bool(output)


def kde_read(group, key):
    command = None

    if command_exists("kreadconfig6"):
        command = "kreadconfig6"
    elif command_exists("kreadconfig5"):
        command = "kreadconfig5"

    if not command:
        return None

    code, output, _ = run_command(
        [
            command,
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
    command = None

    if command_exists("kwriteconfig6"):
        command = "kwriteconfig6"
    elif command_exists("kwriteconfig5"):
        command = "kwriteconfig5"

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
        value = kde_read(
            "General",
            "font"
        )

        if value:
            return value

        return kde_read(
            "General",
            "font"
        )

    return get_ini_value(
        GTK3_SETTINGS,
        "Settings",
        "gtk-font-name"
    )


def set_font(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "font-name",
            value
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "font-name",
            value
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "font-name",
            value
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

    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-font-name",
            value
        ):
            changed = True

    return changed


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

    return get_ini_value(
        GTK3_SETTINGS,
        "Settings",
        "gtk-theme-name"
    )


def set_theme(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "gtk-theme",
            value
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "gtk-theme",
            value
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "gtk-theme",
            value
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

    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-theme-name",
            value
        ):
            changed = True

    return changed


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

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
            "Settings",
            "gtk-icon-theme"
        )

        if value:
            return value

    return None


def set_icon_theme(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "icon-theme",
            value
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "icon-theme",
            value
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.interface",
            "icon-theme",
            value
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

    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-icon-theme",
            value
        ):
            changed = True

    return changed


def get_cursor_theme():
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

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        value = get_ini_value(
            path,
            "Settings",
            "gtk-cursor-theme-name"
        )

        if value:
            return value

    return None


def set_cursor_theme(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "cursor-theme",
            value
        )

    if desktop == "Cinnamon":
        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "cursor-theme",
            value
        )

    if desktop == "MATE":
        return gsettings_set(
            "org.mate.peripherals-mouse",
            "cursor-theme",
            value
        )

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Gtk/CursorThemeName",
            value
        )

    changed = False

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        if set_ini_value(
            path,
            "Settings",
            "gtk-cursor-theme-name",
            value
        ):
            changed = True

    if write_text(
        CURSOR_INDEX,
        "[Icon Theme]\n"
        f"Inherits={value}\n"
    ):
        changed = True

    return changed


def get_cursor_size():
    desktop = detect_desktop()

    if desktop == "XFCE":
        return xfce_get(
            "xsettings",
            "/Gtk/CursorThemeSize"
        )

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "cursor-size"
        )

    return None


def set_cursor_size(value):
    desktop = detect_desktop()

    if desktop == "XFCE":
        return xfce_set(
            "xsettings",
            "/Gtk/CursorThemeSize",
            value
        )

    if desktop == "GNOME":
        return gsettings_set(
            "org.gnome.desktop.interface",
            "cursor-size",
            value
        )

    return False


def get_dark_mode():
    desktop = detect_desktop()

    if desktop == "GNOME":
        return gsettings_get(
            "org.gnome.desktop.interface",
            "color-scheme"
        )

    if desktop == "Cinnamon":
        return gsettings_get(
            "org.cinnamon.desktop.interface",
            "color-scheme"
        )

    if desktop == "XFCE":
        theme = get_theme()

        if theme and "dark" in theme.lower():
            return "dark"

        return "light"

    return None


def set_dark_mode(value):
    desktop = detect_desktop()

    if desktop == "GNOME":
        if value == "Dark":
            return gsettings_set(
                "org.gnome.desktop.interface",
                "color-scheme",
                "prefer-dark"
            )

        return gsettings_set(
            "org.gnome.desktop.interface",
            "color-scheme",
            "default"
        )

    if desktop == "Cinnamon":
        if value == "Dark":
            return gsettings_set(
                "org.cinnamon.desktop.interface",
                "color-scheme",
                "prefer-dark"
            )

        return gsettings_set(
            "org.cinnamon.desktop.interface",
            "color-scheme",
            "prefer-light"
        )

    if desktop == "XFCE":
        current = get_theme()

        if not current:
            return False

        if value == "Dark":
            if "dark" in current.lower():
                target = current
            else:
                target = current + "-dark"
        else:
            target = current.replace(
                "-dark",
                ""
            ).replace(
                "-Dark",
                ""
            )

        return set_theme(target)

    return False


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

    return None


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
            dpi = str(
                int(
                    round(
                        float(value) * 96
                    )
                )
            )
        except ValueError:
            return False

        return xfce_set(
            "xsettings",
            "/Xft/DPI",
            dpi
        )

    return False


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

                name = path.stem.replace(
                    "-",
                    " "
                ).replace(
                    "_",
                    " "
                )

                fonts.add(name)

        except (OSError, PermissionError):
            continue

    return sorted(
        fonts,
        key=str.lower
    )


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

                if (
                    (child / "gtk-3.0").exists()
                    or
                    (child / "gtk-4.0").exists()
                ):
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(
        themes,
        key=str.lower
    )


def discover_icon_themes():
    themes = set()

    for directory in discover_theme_directories():
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for child in directory.iterdir():
                if (
                    child.is_dir()
                    and
                    (child / "index.theme").exists()
                ):
                    themes.add(child.name)

        except (OSError, PermissionError):
            continue

    return sorted(
        themes,
        key=str.lower
    )


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

    return sorted(
        themes,
        key=str.lower
    )


def get_brightness():
    if command_exists("brightnessctl"):
        code, output, _ = run_command(
            ["brightnessctl", "-m"]
        )

        if code == 0 and output:
            parts = output.split(",")

            if len(parts) >= 4:
                return parts[3]

    return None


def set_brightness(value):
    if not command_exists("brightnessctl"):
        return False

    code, _, stderr = run_command(
        [
            "brightnessctl",
            "set",
            value
        ]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def get_volume():
    if not command_exists("pactl"):
        return None

    code, output, _ = run_command(
        [
            "pactl",
            "get-sink-volume",
            "@DEFAULT_SINK@"
        ]
    )

    if code != 0:
        return None

    for part in output.split():
        if part.endswith("%"):
            return part

    return None


def set_volume(value):
    if not command_exists("pactl"):
        return False

    code, _, stderr = run_command(
        [
            "pactl",
            "set-sink-volume",
            "@DEFAULT_SINK@",
            value
        ]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def discover_wallpapers():
    directories = [
        HOME / "Pictures",
        HOME / "Pictures" / "Wallpapers",
        HOME / ".local" / "share" / "backgrounds",
        Path("/usr/share/backgrounds")
    ]

    wallpapers = []

    for directory in directories:
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue

                if path.suffix.lower() in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                ):
                    wallpapers.append(str(path))

        except (OSError, PermissionError):
            continue

    return sorted(
        set(wallpapers),
        key=str.lower
    )


def get_hostname():
    return os.uname().nodename


def set_hostname(value):
    if not command_exists("hostnamectl"):
        return False

    code, _, stderr = run_command(
        [
            "hostnamectl",
            "set-hostname",
            value
        ]
    )

    if code != 0:
        if stderr:
            error(stderr)
        return False

    return True


def get_settings_tree():
    desktop = detect_desktop()

    appearance = [
        {
            "name": "Application Icon Theme",
            "get": get_icon_theme,
            "set": set_icon_theme,
            "options": discover_icon_themes
        },
        {
            "name": "Color Theme",
            "get": get_theme,
            "set": set_theme,
            "options": discover_gtk_themes
        },
        {
            "name": "Cursor Size",
            "get": get_cursor_size,
            "set": set_cursor_size,
            "options": lambda: [
                "16",
                "24",
                "32",
                "48",
                "64",
                "96"
            ]
        },
        {
            "name": "Cursor Theme",
            "get": get_cursor_theme,
            "set": set_cursor_theme,
            "options": discover_cursor_themes
        },
        {
            "name": "Dark Mode",
            "get": get_dark_mode,
            "set": set_dark_mode,
            "options": lambda: [
                "Dark",
                "Light"
            ]
        },
        {
            "name": "Font",
            "get": get_font,
            "set": set_font,
            "options": discover_fonts
        },
        {
            "name": "Interface Scale",
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

    display = [
        {
            "name": "Brightness",
            "get": get_brightness,
            "set": set_brightness,
            "options": lambda: [
                "10%",
                "20%",
                "30%",
                "40%",
                "50%",
                "60%",
                "70%",
                "80%",
                "90%",
                "100%"
            ]
        }
    ]

    sound = [
        {
            "name": "Output Volume",
            "get": get_volume,
            "set": set_volume,
            "options": lambda: [
                "10%",
                "20%",
                "30%",
                "40%",
                "50%",
                "60%",
                "70%",
                "80%",
                "90%",
                "100%"
            ]
        }
    ]

    system = [
        {
            "name": "Hostname",
            "get": get_hostname,
            "set": set_hostname,
            "options": lambda: []
        }
    ]

    if desktop == "KDE Plasma":
        appearance = [
            setting
            for setting in appearance
            if setting["name"] not in (
                "Dark Mode",
                "Interface Scale"
            )
        ]

    if desktop == "MATE":
        appearance = [
            setting
            for setting in appearance
            if setting["name"] != "Interface Scale"
        ]

    if desktop not in (
        "GNOME",
        "Cinnamon",
        "XFCE"
    ):
        appearance = [
            setting
            for setting in appearance
            if setting["name"] not in (
                "Dark Mode",
                "Interface Scale"
            )
        ]

    return {
        "Appearance": sorted(
            appearance,
            key=lambda item: item["name"].lower()
        ),
        "Display": sorted(
            display,
            key=lambda item: item["name"].lower()
        ),
        "Sound": sorted(
            sound,
            key=lambda item: item["name"].lower()
        ),
        "System": sorted(
            system,
            key=lambda item: item["name"].lower()
        )
    }


def backup_filename():
    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )

    return (
        BACKUP_DIR
        /
        f"Cozy-Settings-{timestamp}.backup"
    )


def backup_paths():
    return [
        GTK2_SETTINGS,
        GTK3_SETTINGS,
        GTK4_SETTINGS,
        CURSOR_INDEX,
        KDE_GLOBALS,
        XFCE_XSETTINGS,
        XFCE_XFWM
    ]


def create_backup():
    backup_path = backup_filename()

    snapshot = {
        "format": 3,
        "created": datetime.datetime.now().isoformat(),
        "tool": APP_NAME,
        "brand": BRAND,
        "desktop": detect_desktop(),
        "session": session_type(),
        "files": {},
        "gsettings": {},
        "kde": {},
        "xfce": {}
    }

    for path in backup_paths():
        filename = str(path)

        if path.exists():
            content = read_text(path)

            if content is None:
                error(
                    f"Could not back up {path}"
                )
                return None

            snapshot["files"][filename] = {
                "exists": True,
                "content": content
            }
        else:
            snapshot["files"][filename] = {
                "exists": False,
                "content": None
            }

    gsettings_values = [
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
            "cursor-size"
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
            "org.cinnamon.desktop.interface",
            "color-scheme"
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

    for schema, key in gsettings_values:
        value = gsettings_get(
            schema,
            key
        )

        if value is not None:
            snapshot["gsettings"][
                f"{schema}|{key}"
            ] = value

    kde_values = [
        ("General", "ColorScheme"),
        ("General", "font"),
        ("Icons", "Theme")
    ]

    for group, key in kde_values:
        value = kde_read(
            group,
            key
        )

        if value is not None:
            snapshot["kde"][
                f"{group}|{key}"
            ] = value

    xfce_values = [
        (
            "xsettings",
            "/Gtk/FontName"
        ),
        (
            "xsettings",
            "/Net/ThemeName"
        ),
        (
            "xsettings",
            "/Net/IconThemeName"
        ),
        (
            "xsettings",
            "/Gtk/CursorThemeName"
        ),
        (
            "xsettings",
            "/Gtk/CursorThemeSize"
        ),
        (
            "xsettings",
            "/Xft/DPI"
        )
    ]

    for channel, key in xfce_values:
        value = xfce_get(
            channel,
            key
        )

        if value is not None:
            snapshot["xfce"][
                f"{channel}|{key}"
            ] = value

    try:
        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

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
        error(
            f"Could not create backup: {exc}"
        )
        return None


def automatic_backup():
    info(
        "Creating Cozy-Settings backup..."
    )

    backup = create_backup()

    if backup:
        success(
            f"Backup created: {backup.name}"
        )
        return True

    error(
        "Backup failed. Change cancelled."
    )

    return False


def list_backups():
    backups = sorted(
        BACKUP_DIR.glob(
            "Cozy-Settings-*.backup"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print(
            "No Cozy-Settings backups found "
            "in the script directory."
        )
        return

    print()
    print(
        color(
            "Cozy-Settings backups",
            Colors.BOLD
        )
    )
    print()

    for index, path in enumerate(
        backups,
        1
    ):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        print(
            f"  {index:2}. "
            f"{path.name} "
            f"({size} bytes)"
        )


def find_backup(identifier):
    backups = sorted(
        BACKUP_DIR.glob(
            "Cozy-Settings-*.backup"
        ),
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
        and candidate.name.startswith(
            "Cozy-Settings-"
        )
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
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError
    ) as exc:
        error(
            f"Could not read backup: {exc}"
        )
        return False

    if data.get("format") not in (
        1,
        2,
        3
    ):
        error(
            "Unsupported backup format."
        )
        return False

    safety_backup = create_backup()

    if safety_backup is None:
        error(
            "Could not create safety backup."
        )
        error(
            "Restore cancelled."
        )
        return False

    success(
        f"Safety backup created: "
        f"{safety_backup.name}"
    )

    try:
        files = data.get(
            "files",
            {}
        )

        if not isinstance(files, dict):
            raise ValueError(
                "Invalid file data."
            )

        for filename, file_data in files.items():
            target = Path(filename)

            if not isinstance(
                file_data,
                dict
            ):
                raise ValueError(
                    f"Invalid entry: {filename}"
                )

            exists = file_data.get(
                "exists",
                False
            )

            if exists:
                content = file_data.get(
                    "content"
                )

                if not isinstance(
                    content,
                    str
                ):
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

            schema, key = identifier.split(
                "|",
                1
            )

            if command_exists(
                "gsettings"
            ):
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

            group, key = identifier.split(
                "|",
                1
            )

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

            channel, key = identifier.split(
                "|",
                1
            )

            xfce_set(
                channel,
                key,
                value
            )

        success(
            f"Restored {path.name}"
        )

        info(
            "Some desktop applications may need "
            "to be restarted."
        )

        return True

    except (
        OSError,
        ValueError
    ) as exc:
        error(
            f"Restore failed: {exc}"
        )
        error(
            f"Safety backup remains available: "
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
        success(
            f"Deleted {path.name}"
        )
        return True
    except OSError as exc:
        error(
            f"Could not delete backup: {exc}"
        )
        return False


def setting_value(setting):
    try:
        value = setting["get"]()
    except Exception:
        return None

    if value is None or value == "":
        return "not configured"

    return str(value).strip(
        "'\""
    )


def choose_option(setting):
    options = setting["options"]()

    if not options:
        warning(
            f"No available options were found "
            f"for {setting['name']}."
        )
        return None

    options = sorted(
        set(str(option) for option in options),
        key=str.lower
    )

    current = setting_value(
        setting
    )

    print()
    print(
        color(
            setting["name"],
            Colors.BOLD
        )
    )
    print()

    print(
        f"Current: {current}"
    )
    print()

    for index, option in enumerate(
        options,
        1
    ):
        marker = ""

        if (
            current != "not configured"
            and
            current == str(option).strip(
                "'\""
            )
        ):
            marker = "  ← current"

        print(
            f"  {index:2}. "
            f"{option}"
            f"{marker}"
        )

    print()
    print("   0. Back")
    print()

    while True:
        try:
            choice = input(
                "Select an option: "
            ).strip()
        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(options):
                return options[
                    number - 1
                ]

        print(
            "Please enter a valid number."
        )


def verify_setting(setting, expected):
    current = setting_value(
        setting
    )

    expected = str(expected).strip(
        "'\""
    )

    if current == expected:
        return True

    if (
        setting["name"] == "Output Volume"
        and current
    ):
        return current == expected

    if (
        setting["name"] == "Brightness"
        and current
    ):
        return current == expected

    return False


def change_setting(setting):
    value = choose_option(
        setting
    )

    if value is None:
        return

    print()
    print(
        f"Selected: "
        f"{setting['name']} → {value}"
    )

    if not ask_confirmation(
        "Apply this setting?"
    ):
        info(
            "Change cancelled."
        )
        return

    if not automatic_backup():
        return

    try:
        changed = setting["set"](
            value
        )
    except Exception as exc:
        error(
            f"Could not apply setting: "
            f"{exc}"
        )
        return

    if not changed:
        error(
            f"{setting['name']} could not "
            f"be changed."
        )
        return

    if verify_setting(
        setting,
        value
    ):
        success(
            f"{setting['name']} changed "
            f"to {value}"
        )
    else:
        warning(
            f"{setting['name']} was written, "
            f"but verification did not match."
        )

        info(
            "The desktop may require a restart "
            "or session reload."
        )


def category_menu(category, settings):
    while True:
        print()
        print(
            color(
                category,
                Colors.BOLD
            )
        )
        print()

        for index, setting in enumerate(
            settings,
            1
        ):
            current = setting_value(
                setting
            )

            print(
                f"  {index:2}. "
                f"{setting['name']:<28} "
                f"{color(f'[{current}]', Colors.DIM)}"
            )

        print()
        print("   0. Back")
        print()

        try:
            choice = input(
                "Select a setting: "
            ).strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "0":
            return

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(settings):
                change_setting(
                    settings[number - 1]
                )
                pause()
                continue

        print(
            "Please enter a valid number."
        )


def main_menu():
    while True:
        banner()

        desktop = detect_desktop()

        print(
            f"Desktop: "
            f"{color(desktop, Colors.CYAN)}"
        )

        print(
            f"Session: "
            f"{color(session_type(), Colors.CYAN)}"
        )

        print()

        tree = get_settings_tree()

        categories = sorted(
            tree.keys(),
            key=str.lower
        )

        print(
            color(
                "Settings",
                Colors.BOLD
            )
        )
        print()

        for index, category in enumerate(
            categories,
            1
        ):
            print(
                f"  {index:2}. "
                f"{category}"
            )

        print()
        print(
            f"  {len(categories) + 1:2}. "
            f"Backups"
        )

        print(
            f"  {len(categories) + 2:2}. "
            f"Current Settings"
        )

        print(
            f"  {len(categories) + 3:2}. "
            f"Exit"
        )

        print()

        try:
            choice = input(
                "Choose a category: "
            ).strip()
        except KeyboardInterrupt:
            print()
            return

        if not choice.isdigit():
            warning(
                "Please enter a valid number."
            )
            continue

        number = int(choice)

        if 1 <= number <= len(categories):
            category = categories[
                number - 1
            ]

            category_menu(
                category,
                tree[category]
            )

        elif number == len(categories) + 1:
            backup_menu()

        elif number == len(categories) + 2:
            show_current()
            pause()

        elif number == len(categories) + 3:
            print()
            print(BRAND)
            print()
            return

        else:
            warning(
                "Invalid option."
            )


def show_current():
    banner()

    print(
        color(
            "Current system settings",
            Colors.BOLD
        )
    )

    print()
    print(
        f"Desktop: {detect_desktop()}"
    )
    print(
        f"Session: {session_type()}"
    )
    print()

    tree = get_settings_tree()

    for category in sorted(
        tree.keys(),
        key=str.lower
    ):
        print(
            color(
                category,
                Colors.BOLD
            )
        )

        for setting in tree[category]:
            print(
                f"  "
                f"{setting['name']:<28} "
                f"{setting_value(setting)}"
            )

        print()


def backup_menu():
    while True:
        banner()

        print(
            color(
                "Backup Management",
                Colors.BOLD
            )
        )

        print()
        print(
            f"Backup directory: "
            f"{BACKUP_DIR}"
        )
        print()

        print("  1. Create backup")
        print("  2. List backups")
        print("  3. Restore backup")
        print("  4. Delete backup")
        print("  0. Back")
        print()

        try:
            choice = input(
                "Choose an option: "
            ).strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "1":
            backup = create_backup()

            if backup:
                success(
                    f"Backup created: "
                    f"{backup.name}"
                )
            else:
                error(
                    "Backup creation failed."
                )

            pause()

        elif choice == "2":
            list_backups()
            pause()

        elif choice == "3":
            restore_interactive()
            pause()

        elif choice == "4":
            delete_backup_interactive()
            pause()

        elif choice == "0":
            return

        else:
            warning(
                "Invalid option."
            )


def restore_interactive():
    list_backups()

    backups = sorted(
        BACKUP_DIR.glob(
            "Cozy-Settings-*.backup"
        ),
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

    restore_backup(
        choice
    )


def delete_backup_interactive():
    list_backups()

    backups = sorted(
        BACKUP_DIR.glob(
            "Cozy-Settings-*.backup"
        ),
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

    path = find_backup(
        choice
    )

    if path is None:
        error(
            "Backup not found."
        )
        return

    if not ask_confirmation(
        f"Delete {path.name}?"
    ):
        info(
            "Deletion cancelled."
        )
        return

    delete_backup(
        choice
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Cozy Settings - terminal Linux "
            "settings manager."
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
        help="Show current settings"
    )

    subparsers.add_parser(
        "backup",
        help="Create a backup"
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
        main_menu()
        return 0

    if args.command == "menu":
        main_menu()
        return 0

    if args.command == "current":
        show_current()
        return 0

    if args.command == "backup":
        backup = create_backup()

        if backup:
            success(
                f"Backup created: "
                f"{backup.name}"
            )
            return 0

        return 1

    if args.command == "backups":
        list_backups()
        return 0

    if args.command == "restore":
        return (
            0
            if restore_backup(
                args.backup
            )
            else 1
        )

    if args.command == "delete-backup":
        return (
            0
            if delete_backup(
                args.backup
            )
            else 1
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(
            main()
        )
    except KeyboardInterrupt:
        print(
            "\n\nCancelled."
        )
        sys.exit(130)
# not tested
