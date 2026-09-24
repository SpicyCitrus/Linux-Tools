import argparse
import configparser
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


APP_NAME = "Cozy Settings"
BRAND = "Made with ❤️ by Cozy"
BACKUP_FORMAT = 1

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
XFCE_CHANNELS = HOME / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml"

CONFIG_FILES = (
    GTK3_SETTINGS,
    GTK4_SETTINGS,
)

DE_ALIASES = {
    "GNOME": "GNOME",
    "GNOME-CLASSIC": "GNOME",
    "KDE": "KDE Plasma",
    "PLASMA": "KDE Plasma",
    "XFCE": "XFCE",
    "X-CINNAMON": "Cinnamon",
    "CINNAMON": "Cinnamon",
    "MATE": "MATE",
    "LXDE": "LXDE",
    "LXQT": "LXQt",
    "BUDGIE": "Budgie",
    "PANTHEON": "Pantheon",
    "COSMIC": "COSMIC",
}


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
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
    print(color("╔══════════════════════════════════════════════════╗", Colors.MAGENTA))
    print(color("║                  COZY SETTINGS                  ║", Colors.MAGENTA))
    print(color("╚══════════════════════════════════════════════════╝", Colors.MAGENTA))
    print()
    print(color(BRAND, Colors.DIM))
    print()


def pause():
    try:
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print()


def command_exists(command):
    return shutil.which(command) is not None


def run_command(command, timeout=10):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None


def get_desktop_environment():
    values = []

    for variable in (
        "XDG_CURRENT_DESKTOP",
        "XDG_SESSION_DESKTOP",
        "DESKTOP_SESSION",
    ):
        value = os.environ.get(variable, "")
        if value:
            values.extend(
                value.replace(";", ":").split(":")
            )

    for value in values:
        normalized = value.strip().upper()

        if normalized in DE_ALIASES:
            return DE_ALIASES[normalized]

        for key, name in DE_ALIASES.items():
            if key in normalized:
                return name

    if command_exists("gnome-shell"):
        return "GNOME"

    if command_exists("plasmashell"):
        return "KDE Plasma"

    if command_exists("xfce4-session"):
        return "XFCE"

    if command_exists("cinnamon"):
        return "Cinnamon"

    if command_exists("mate-session"):
        return "MATE"

    if command_exists("lxqt-session"):
        return "LXQt"

    if command_exists("startlxde"):
        return "LXDE"

    return "Unknown"


def get_session_type():
    session = os.environ.get("XDG_SESSION_TYPE")

    if session:
        return session.capitalize()

    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"

    if os.environ.get("DISPLAY"):
        return "X11"

    return "Unknown"


def get_desktop_version():
    desktop = get_desktop_environment()

    commands = {
        "GNOME": ["gnome-shell", "--version"],
        "KDE Plasma": ["plasmashell", "--version"],
        "XFCE": ["xfce4-session", "--version"],
        "Cinnamon": ["cinnamon", "--version"],
        "MATE": ["mate-session", "--version"],
    }

    command = commands.get(desktop)

    if not command:
        return "Unknown"

    result = run_command(command)

    if result is None:
        return "Unknown"

    output = result.stdout.strip() or result.stderr.strip()

    return output if output else "Unknown"


def ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_write(path, content):
    ensure_parent(path)

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)
        return True

    except OSError as exc:
        error(f"Could not write {path}: {exc}")

        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

        return False


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None


def get_ini(path):
    parser = configparser.ConfigParser()

    if not path.exists():
        return parser

    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error:
        return parser

    return parser


def get_ini_value(path, section, key):
    parser = get_ini(path)

    if parser.has_option(section, key):
        return parser.get(section, key)

    return None


def set_ini_value(path, section, key, value):
    parser = get_ini(path)

    if not parser.has_section(section):
        parser.add_section(section)

    parser.set(section, key, str(value))

    try:
        with tempfile.TemporaryFile(
            mode="w+",
            encoding="utf-8",
        ) as file:
            parser.write(file)
            file.seek(0)
            content = file.read()

        return atomic_write(path, content)

    except OSError as exc:
        error(f"Could not update {path}: {exc}")
        return False


def gsettings_get(schema, key):
    if not command_exists("gsettings"):
        return None

    result = run_command(
        ["gsettings", "get", schema, key]
    )

    if result is None or result.returncode != 0:
        return None

    return result.stdout.strip()


def gsettings_set(schema, key, value):
    if not command_exists("gsettings"):
        return False

    result = run_command(
        ["gsettings", "set", schema, key, value]
    )

    return result is not None and result.returncode == 0


def gsettings_reset(schema, key):
    if not command_exists("gsettings"):
        return False

    result = run_command(
        ["gsettings", "reset", schema, key]
    )

    return result is not None and result.returncode == 0


def discover_fonts():
    if not command_exists("fc-list"):
        return []

    result = run_command(
        [
            "fc-list",
            ":",
            "family",
            "-f",
            "%{family}\n",
        ],
        timeout=15,
    )

    if result is None or result.returncode != 0:
        return []

    fonts = set()

    for line in result.stdout.splitlines():
        for family in line.split(","):
            family = family.strip()

            if family:
                fonts.add(family)

    return sorted(fonts, key=str.casefold)


def discover_cursor_themes():
    directories = [
        HOME / ".icons",
        HOME / ".local" / "share" / "icons",
        Path("/usr/share/icons"),
        Path("/usr/local/share/icons"),
    ]

    themes = set()

    for directory in directories:
        if not directory.exists():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                if (child / "cursors").is_dir():
                    themes.add(child.name)

        except OSError:
            continue

    return sorted(themes, key=str.casefold)


def discover_icon_themes():
    directories = [
        HOME / ".icons",
        HOME / ".local" / "share" / "icons",
        Path("/usr/share/icons"),
        Path("/usr/local/share/icons"),
    ]

    themes = set()

    for directory in directories:
        if not directory.exists():
            continue

        try:
            for child in directory.iterdir():
                if not child.is_dir():
                    continue

                if (child / "index.theme").exists():
                    themes.add(child.name)

        except OSError:
            continue

    return sorted(themes, key=str.casefold)


def get_current_font():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "font-name",
        )

        if value:
            return value.strip("'")

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-font-name",
        )

        if value:
            return value

    return "Unknown"


def set_font(font):
    desktop = get_desktop_environment()

    success_count = 0

    if desktop == "GNOME":
        if gsettings_set(
            "org.gnome.desktop.interface",
            "font-name",
            font,
        ):
            success_count += 1

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        if set_ini_value(
            settings,
            "Settings",
            "gtk-font-name",
            font,
        ):
            success_count += 1

    return success_count > 0


def get_current_cursor():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "cursor-theme",
        )

        if value:
            return value.strip("'")

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-cursor-theme-name",
        )

        if value:
            return value

    return "Unknown"


def set_cursor(theme):
    desktop = get_desktop_environment()

    success_count = 0

    if desktop == "GNOME":
        if gsettings_set(
            "org.gnome.desktop.interface",
            "cursor-theme",
            f"'{theme}'",
        ):
            success_count += 1

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        if set_ini_value(
            settings,
            "Settings",
            "gtk-cursor-theme-name",
            theme,
        ):
            success_count += 1

    return success_count > 0


def get_current_icon_theme():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "icon-theme",
        )

        if value:
            return value.strip("'")

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        value = get_ini_value(
            settings,
            "Settings",
            "gtk-icon-theme",
        )

        if value:
            return value

    return "Unknown"


def set_icon_theme(theme):
    desktop = get_desktop_environment()

    success_count = 0

    if desktop == "GNOME":
        if gsettings_set(
            "org.gnome.desktop.interface",
            "icon-theme",
            f"'{theme}'",
        ):
            success_count += 1

    for settings in (
        GTK4_SETTINGS,
        GTK3_SETTINGS,
    ):
        if set_ini_value(
            settings,
            "Settings",
            "gtk-icon-theme",
            theme,
        ):
            success_count += 1

    return success_count > 0


def get_dark_mode():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "color-scheme",
        )

        if value:
            value = value.strip("'")

            if value == "prefer-dark":
                return "Dark"

            if value == "prefer-light":
                return "Light"

            return "Follow System"

    return "Unknown"


def set_dark_mode(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    values = {
        "Dark": "prefer-dark",
        "Light": "prefer-light",
        "Follow System": "default",
    }

    target = values.get(value)

    if target is None:
        return False

    return gsettings_set(
        "org.gnome.desktop.interface",
        "color-scheme",
        target,
    )


def get_text_scaling():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "text-scaling-factor",
        )

        if value:
            try:
                return f"{int(float(value) * 100)}%"
            except ValueError:
                pass

    return "100%"


def set_text_scaling(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    try:
        percent = int(value.rstrip("%"))
        factor = percent / 100
    except ValueError:
        return False

    return gsettings_set(
        "org.gnome.desktop.interface",
        "text-scaling-factor",
        str(factor),
    )


def get_cursor_size():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "cursor-size",
        )

        if value:
            return value

    return "Unknown"


def set_cursor_size(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    return gsettings_set(
        "org.gnome.desktop.interface",
        "cursor-size",
        str(value),
    )


def get_night_light():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.settings-daemon.plugins.color",
            "night-light-enabled",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_night_light(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.settings-daemon.plugins.color",
        "night-light-enabled",
        target,
    )


def get_animations():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "enable-animations",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_animations(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.interface",
        "enable-animations",
        target,
    )


def get_notifications():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.notifications",
            "show-banners",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_notifications(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.notifications",
        "show-banners",
        target,
    )


def get_clock_seconds():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "clock-show-seconds",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_clock_seconds(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.interface",
        "clock-show-seconds",
        target,
    )


def get_clock_date():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.interface",
            "clock-show-date",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_clock_date(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.interface",
        "clock-show-date",
        target,
    )


def get_workspace_mode():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.mutter",
            "dynamic-workspaces",
        )

        if value:
            return (
                "Dynamic"
                if value.lower() == "true"
                else "Static"
            )

    return "Unknown"


def set_workspace_mode(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Dynamic" else "false"

    return gsettings_set(
        "org.gnome.mutter",
        "dynamic-workspaces",
        target,
    )


def get_workspaces():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.wm.preferences",
            "num-workspaces",
        )

        if value:
            return value

    return "Unknown"


def set_workspaces(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    try:
        number = int(value)
    except ValueError:
        return False

    return gsettings_set(
        "org.gnome.desktop.wm.preferences",
        "num-workspaces",
        str(number),
    )


def get_wallpaper():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.background",
            "picture-uri",
        )

        if value:
            return value.strip("'")

    return "Unknown"


def set_wallpaper(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    path = Path(value).expanduser()

    if not path.exists() or not path.is_file():
        return False

    uri = path.resolve().as_uri()

    return gsettings_set(
        "org.gnome.desktop.background",
        "picture-uri",
        f"'{uri}'",
    )


def get_wallpaper_dark():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.background",
            "picture-uri-dark",
        )

        if value:
            return value.strip("'")

    return "Unknown"


def set_wallpaper_dark(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    path = Path(value).expanduser()

    if not path.exists() or not path.is_file():
        return False

    uri = path.resolve().as_uri()

    return gsettings_set(
        "org.gnome.desktop.background",
        "picture-uri-dark",
        f"'{uri}'",
    )


def get_pointer_speed():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.peripherals.mouse",
            "speed",
        )

        if value:
            return value

    return "Unknown"


def set_pointer_speed(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    try:
        number = float(value)
    except ValueError:
        return False

    return gsettings_set(
        "org.gnome.desktop.peripherals.mouse",
        "speed",
        str(number),
    )


def get_natural_scrolling():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.peripherals.mouse",
            "natural-scroll",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_natural_scrolling(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.peripherals.mouse",
        "natural-scroll",
        target,
    )


def get_touchpad_tap():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.peripherals.touchpad",
            "tap-to-click",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_touchpad_tap(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.peripherals.touchpad",
        "tap-to-click",
        target,
    )


def get_screen_lock():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.desktop.screensaver",
            "lock-enabled",
        )

        if value:
            return "Enabled" if value.lower() == "true" else "Disabled"

    return "Unknown"


def set_screen_lock(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    target = "true" if value == "Enabled" else "false"

    return gsettings_set(
        "org.gnome.desktop.screensaver",
        "lock-enabled",
        target,
    )


def get_power_button():
    desktop = get_desktop_environment()

    if desktop == "GNOME":
        value = gsettings_get(
            "org.gnome.settings-daemon.plugins.power",
            "power-button-action",
        )

        if value:
            return value.strip("'")

    return "Unknown"


def set_power_button(value):
    desktop = get_desktop_environment()

    if desktop != "GNOME":
        return False

    return gsettings_set(
        "org.gnome.settings-daemon.plugins.power",
        "power-button-action",
        f"'{value}'",
    )


def get_setting_registry():
    return {
        "Appearance": {
            "Accent Color": {
                "get": lambda: "Supported where available",
                "options": [],
                "set": None,
            },
            "Application Theme": {
                "get": lambda: get_ini_value(
                    GTK3_SETTINGS,
                    "Settings",
                    "gtk-theme",
                ) or "Unknown",
                "options": [],
                "set": None,
            },
            "Animations": {
                "get": get_animations,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_animations,
            },
            "Cursor Size": {
                "get": get_cursor_size,
                "options": [
                    "16",
                    "24",
                    "32",
                    "48",
                    "64",
                ],
                "set": set_cursor_size,
            },
            "Cursor Theme": {
                "get": get_current_cursor,
                "options": discover_cursor_themes(),
                "set": set_cursor,
            },
            "Dark / Light Mode": {
                "get": get_dark_mode,
                "options": [
                    "Dark",
                    "Follow System",
                    "Light",
                ],
                "set": set_dark_mode,
            },
            "Icon Theme": {
                "get": get_current_icon_theme,
                "options": discover_icon_themes(),
                "set": set_icon_theme,
            },
            "Interface Font": {
                "get": get_current_font,
                "options": discover_fonts(),
                "set": set_font,
            },
            "Text Scaling": {
                "get": get_text_scaling,
                "options": [
                    "80%",
                    "90%",
                    "100%",
                    "110%",
                    "125%",
                    "150%",
                    "175%",
                    "200%",
                ],
                "set": set_text_scaling,
            },
        },
        "Background": {
            "Wallpaper": {
                "get": get_wallpaper,
                "options": [],
                "set": set_wallpaper,
            },
            "Dark Wallpaper": {
                "get": get_wallpaper_dark,
                "options": [],
                "set": set_wallpaper_dark,
            },
        },
        "Keyboard": {
            "Keyboard Layout": {
                "get": lambda: "Use your desktop keyboard settings",
                "options": [],
                "set": None,
            },
        },
        "Mouse & Touchpad": {
            "Natural Scrolling": {
                "get": get_natural_scrolling,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_natural_scrolling,
            },
            "Pointer Speed": {
                "get": get_pointer_speed,
                "options": [
                    "-1",
                    "-0.5",
                    "0",
                    "0.5",
                    "1",
                ],
                "set": set_pointer_speed,
            },
            "Touchpad Tap to Click": {
                "get": get_touchpad_tap,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_touchpad_tap,
            },
        },
        "Notifications": {
            "Notifications": {
                "get": get_notifications,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_notifications,
            },
        },
        "Power": {
            "Power Button Action": {
                "get": get_power_button,
                "options": [
                    "interactive",
                    "suspend",
                    "hibernate",
                    "poweroff",
                    "nothing",
                ],
                "set": set_power_button,
            },
        },
        "Privacy": {
            "Screen Lock": {
                "get": get_screen_lock,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_screen_lock,
            },
        },
        "Sound": {
            "Output Device": {
                "get": lambda: get_default_sink(),
                "options": [],
                "set": set_default_sink,
            },
            "Output Volume": {
                "get": lambda: get_volume(),
                "options": [],
                "set": set_volume,
            },
        },
        "Windows": {
            "Clock Date": {
                "get": get_clock_date,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_clock_date,
            },
            "Clock Seconds": {
                "get": get_clock_seconds,
                "options": [
                    "Disabled",
                    "Enabled",
                ],
                "set": set_clock_seconds,
            },
        },
        "Workspaces": {
            "Number of Workspaces": {
                "get": get_workspaces,
                "options": [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "8",
                    "10",
                ],
                "set": set_workspaces,
            },
            "Workspace Mode": {
                "get": get_workspace_mode,
                "options": [
                    "Dynamic",
                    "Static",
                ],
                "set": set_workspace_mode,
            },
        },
    }


def get_default_sink():
    if command_exists("pactl"):
        result = run_command(
            [
                "pactl",
                "get-default-sink",
            ]
        )

        if result and result.returncode == 0:
            return result.stdout.strip()

    return "Unknown"


def set_default_sink(value):
    if not command_exists("pactl"):
        return False

    result = run_command(
        [
            "pactl",
            "set-default-sink",
            value,
        ]
    )

    return result is not None and result.returncode == 0


def get_volume():
    if not command_exists("pactl"):
        return "Unknown"

    result = run_command(
        [
            "pactl",
            "get-sink-volume",
            "@DEFAULT_SINK@",
        ]
    )

    if result is None or result.returncode != 0:
        return "Unknown"

    for part in result.stdout.split():
        if part.endswith("%"):
            return part

    return "Unknown"


def set_volume(value):
    if not command_exists("pactl"):
        return False

    try:
        number = int(value.rstrip("%"))
    except ValueError:
        return False

    if number < 0 or number > 150:
        return False

    result = run_command(
        [
            "pactl",
            "set-sink-volume",
            "@DEFAULT_SINK@",
            f"{number}%",
        ]
    )

    return result is not None and result.returncode == 0


def ask_confirmation(message):
    while True:
        try:
            answer = input(
                f"{message} [y/N]: "
            ).strip().lower()

        except KeyboardInterrupt:
            print()
            return False

        if answer in ("y", "yes"):
            return True

        if answer in ("", "n", "no"):
            return False

        print("Please answer yes or no.")


def timestamp():
    return datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )


def create_backup():
    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    registry = get_setting_registry()

    settings = {}

    for category, values in registry.items():
        for name, setting in values.items():
            try:
                current = setting["get"]()
            except Exception:
                current = "Unknown"

            settings[f"{category}/{name}"] = {
                "category": category,
                "name": name,
                "value": current,
            }

    snapshot = {
        "format": BACKUP_FORMAT,
        "tool": APP_NAME,
        "brand": BRAND,
        "created": datetime.datetime.now().astimezone().isoformat(),
        "desktop": get_desktop_environment(),
        "session": get_session_type(),
        "settings": settings,
    }

    filename = (
        BACKUP_DIR
        / f"cozy-backup-{timestamp()}.backup"
    )

    try:
        content = json.dumps(
            snapshot,
            indent=2,
            ensure_ascii=False,
        )

        if not atomic_write(filename, content):
            return None

        return filename

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        error(f"Could not create backup: {exc}")
        return None


def get_backups():
    if not BACKUP_DIR.exists():
        return []

    try:
        backups = list(
            BACKUP_DIR.glob("*.backup")
        )
    except OSError:
        return []

    def sort_key(path):
        try:
            return path.stat().st_mtime
        except OSError:
            return 0

    return sorted(
        backups,
        key=sort_key,
        reverse=True,
    )


def list_backups():
    backups = get_backups()

    print()
    print(color("Backups", Colors.BOLD))
    print()
    print(f"Location: {BACKUP_DIR}")
    print()

    if not backups:
        print("No backups found.")
        return

    for index, backup in enumerate(
        backups,
        1,
    ):
        try:
            size = backup.stat().st_size
            modified = datetime.datetime.fromtimestamp(
                backup.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            size = 0
            modified = "Unknown"

        print(
            f"  {index:2}. {backup.name}"
        )
        print(
            f"      {size:,} bytes | {modified}"
        )


def find_backup(identifier):
    backups = get_backups()

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
        content = path.read_text(
            encoding="utf-8"
        )

        data = json.loads(content)

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        error(f"Could not read backup: {exc}")
        return None

    if not isinstance(data, dict):
        error("Invalid backup.")
        return None

    if data.get("format") != BACKUP_FORMAT:
        error("Unsupported backup format.")
        return None

    if not isinstance(
        data.get("settings"),
        dict,
    ):
        error("Backup contains no settings.")
        return None

    return data


def set_setting(category, name, value):
    registry = get_setting_registry()

    category_settings = registry.get(category)

    if not category_settings:
        return False

    setting = category_settings.get(name)

    if not setting:
        return False

    setter = setting.get("set")

    if setter is None:
        return False

    try:
        return bool(setter(value))
    except Exception as exc:
        error(f"Could not change setting: {exc}")
        return False


def restore_backup(identifier):
    backup = find_backup(identifier)

    if backup is None:
        error("Backup not found.")
        return False

    data = load_backup(backup)

    if data is None:
        return False

    print()
    print(
        f"Backup created: "
        f"{data.get('created', 'Unknown')}"
    )
    print(
        f"Desktop: "
        f"{data.get('desktop', 'Unknown')}"
    )
    print()

    settings = data["settings"]

    for key, item in settings.items():
        print(
            f"  {key}: "
            f"{item.get('value', 'Unknown')}"
        )

    print()

    if not ask_confirmation(
        "Create a safety backup and restore this backup?"
    ):
        info("Restore cancelled.")
        return False

    safety = create_backup()

    if safety is None:
        error(
            "Could not create safety backup."
        )
        return False

    success(
        f"Safety backup created: {safety.name}"
    )

    failed = []

    for item in settings.values():
        category = item.get("category")
        name = item.get("name")
        value = item.get("value")

        if value in (
            None,
            "Unknown",
            "Supported where available",
        ):
            continue

        if set_setting(
            category,
            name,
            value,
        ):
            success(
                f"Restored {category} → {name}"
            )
        else:
            failed.append(
                f"{category} → {name}"
            )

    if failed:
        print()

        warning(
            "Some settings could not be restored:"
        )

        for item in failed:
            print(f"  - {item}")

        return False

    success("Backup restored successfully.")
    return True


def choose_from_list(items, title):
    print()
    print(color(title, Colors.BOLD))
    print()

    if not items:
        warning("No options available.")
        return None

    for index, item in enumerate(
        sorted(items, key=str.casefold),
        1,
    ):
        print(f"  {index:3}. {item}")

    print()
    print("    0. Back")
    print()

    while True:
        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            print()
            return None

        if choice == "0":
            return None

        if choice.isdigit():
            number = int(choice)

            if 1 <= number <= len(items):
                return sorted(
                    items,
                    key=str.casefold,
                )[number - 1]

        print("Please enter a valid option.")


def setting_menu(category, name, setting):
    while True:
        try:
            current = setting["get"]()
        except Exception:
            current = "Unknown"

        print()
        print(
            color(
                f"{category} → {name}",
                Colors.BOLD,
            )
        )
        print()
        print(f"Current: {current}")
        print()

        options = setting.get(
            "options",
            [],
        )

        if options:
            options = sorted(
                options,
                key=str.casefold,
            )

            for index, option in enumerate(
                options,
                1,
            ):
                print(
                    f"  {index:3}. {option}"
                )

        else:
            print(
                "  C. Enter custom value"
            )

        print()
        print("  0. Back")
        print()

        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "0":
            return

        if options:
            if not choice.isdigit():
                print("Please enter a valid option.")
                continue

            number = int(choice)

            if not 1 <= number <= len(options):
                print("Please enter a valid option.")
                continue

            new_value = options[number - 1]

        else:
            if choice.lower() != "c":
                print("Please enter C or 0.")
                continue

            try:
                new_value = input(
                    f"Enter new value [{current}]: "
                ).strip()
            except KeyboardInterrupt:
                print()
                continue

            if not new_value:
                continue

        print()
        print(f"Current: {current}")
        print(f"New:     {new_value}")
        print()

        if str(current) == str(new_value):
            info("This setting is already set to that value.")
            continue

        if not ask_confirmation(
            "Create a backup and apply this change?"
        ):
            info("Change cancelled.")
            continue

        backup = create_backup()

        if backup is None:
            error(
                "Could not create backup. "
                "Change cancelled."
            )
            continue

        success(
            f"Backup created: {backup.name}"
        )

        setter = setting.get("set")

        if setter is None:
            error(
                "This setting is currently "
                "display-only."
            )
            continue

        try:
            changed = setter(new_value)
        except Exception as exc:
            error(f"Could not apply change: {exc}")
            changed = False

        if changed:
            success(
                f"{name} changed to {new_value}"
            )
        else:
            error(
                f"Could not change {name}."
            )


def category_menu(category, settings):
    names = sorted(
        settings.keys(),
        key=str.casefold,
    )

    while True:
        print()
        print(color(category, Colors.BOLD))
        print()

        for index, name in enumerate(
            names,
            1,
        ):
            print(
                f"  {index:3}. {name}"
            )

        print()
        print("    0. Back")
        print()

        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "0":
            return

        if not choice.isdigit():
            print("Please enter a valid option.")
            continue

        number = int(choice)

        if not 1 <= number <= len(names):
            print("Please enter a valid option.")
            continue

        name = names[number - 1]

        setting_menu(
            category,
            name,
            settings[name],
        )


def search_settings(query):
    registry = get_setting_registry()

    query = query.casefold()

    results = []

    for category, settings in registry.items():
        for name in settings:
            combined = (
                f"{category} {name}"
            ).casefold()

            if query in combined:
                results.append(
                    (
                        category,
                        name,
                    )
                )

    return sorted(
        results,
        key=lambda item: (
            item[0].casefold(),
            item[1].casefold(),
        ),
    )


def search_menu():
    try:
        query = input(
            "\nSearch settings: "
        ).strip()
    except KeyboardInterrupt:
        print()
        return

    if not query:
        return

    results = search_settings(query)

    print()

    if not results:
        warning(
            f"No settings found for '{query}'."
        )
        return

    print(
        color(
            f"Search results for: {query}",
            Colors.BOLD,
        )
    )
    print()

    for index, (
        category,
        name,
    ) in enumerate(results, 1):
        print(
            f"  {index:3}. "
            f"{category} → {name}"
        )

    print()
    print("    0. Back")
    print()

    while True:
        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "0":
            return

        if not choice.isdigit():
            print("Please enter a valid option.")
            continue

        number = int(choice)

        if not 1 <= number <= len(results):
            print("Please enter a valid option.")
            continue

        category, name = results[number - 1]

        registry = get_setting_registry()

        setting_menu(
            category,
            name,
            registry[category][name],
        )

        return


def show_current():
    registry = get_setting_registry()

    print()
    print(color("Current Settings", Colors.BOLD))
    print()

    for category in sorted(
        registry,
        key=str.casefold,
    ):
        print(color(category, Colors.CYAN))

        settings = registry[category]

        for name in sorted(
            settings,
            key=str.casefold,
        ):
            try:
                value = settings[name]["get"]()
            except Exception:
                value = "Unknown"

            print(
                f"  {name}: {value}"
            )

        print()


def show_system():
    print()
    print(color("System Information", Colors.BOLD))
    print()

    print(
        f"  Desktop Environment : "
        f"{get_desktop_environment()}"
    )

    print(
        f"  Desktop Version     : "
        f"{get_desktop_version()}"
    )

    print(
        f"  Session             : "
        f"{get_session_type()}"
    )

    print(
        f"  Backup Directory    : "
        f"{BACKUP_DIR}"
    )

    print()

    print(
        color(
            "Available tools",
            Colors.BOLD,
        )
    )
    print()

    tools = [
        "gsettings",
        "fc-list",
        "pactl",
        "xrandr",
    ]

    for tool in tools:
        status = (
            "Available"
            if command_exists(tool)
            else "Not installed"
        )

        print(
            f"  {tool:10} : {status}"
        )


def main_menu():
    registry = get_setting_registry()

    while True:
        banner()

        desktop = get_desktop_environment()
        session = get_session_type()

        print(
            f"Desktop: {desktop}"
        )
        print(
            f"Session: {session}"
        )

        print()
        print(color("Settings", Colors.BOLD))
        print()

        categories = sorted(
            registry.keys(),
            key=str.casefold,
        )

        for index, category in enumerate(
            categories,
            1,
        ):
            print(
                f"  {index:2}. {category}"
            )

        print()
        print("  S. Search Settings")
        print("  V. View Current Settings")
        print("  I. System Information")
        print("  B. Backups")
        print("  R. Restore Backup")
        print("  Q. Quit")
        print()

        try:
            choice = input("Choose an option: ").strip()
        except KeyboardInterrupt:
            print()
            return

        if choice.lower() == "q":
            print()
            print(BRAND)
            print()
            return

        if choice.lower() == "s":
            search_menu()
            pause()
            continue

        if choice.lower() == "v":
            show_current()
            pause()
            continue

        if choice.lower() == "i":
            show_system()
            pause()
            continue

        if choice.lower() == "b":
            list_backups()
            pause()
            continue

        if choice.lower() == "r":
            list_backups()

            backups = get_backups()

            if backups:
                print()

                try:
                    selected = input(
                        "Enter backup number or filename "
                        "(0 to cancel): "
                    ).strip()
                except KeyboardInterrupt:
                    print()
                    continue

                if selected != "0":
                    restore_backup(selected)

            pause()
            continue

        if not choice.isdigit():
            warning("Invalid option.")
            pause()
            continue

        number = int(choice)

        if not 1 <= number <= len(categories):
            warning("Invalid option.")
            pause()
            continue

        category = categories[number - 1]

        category_menu(
            category,
            registry[category],
        )


def command_set(args):
    registry = get_setting_registry()

    category = args.category
    name = args.setting

    if category not in registry:
        error(f"Unknown category: {category}")
        return 1

    if name not in registry[category]:
        error(
            f"Unknown setting: "
            f"{category} → {name}"
        )
        return 1

    setting = registry[category][name]

    try:
        current = setting["get"]()
    except Exception:
        current = "Unknown"

    print()
    print(
        color(
            f"{category} → {name}",
            Colors.BOLD,
        )
    )
    print()
    print(f"Current: {current}")
    print(f"New:     {args.value}")
    print()

    if not ask_confirmation(
        "Create a backup and apply this change?"
    ):
        return 0

    backup = create_backup()

    if backup is None:
        error(
            "Could not create backup. "
            "Change cancelled."
        )
        return 1

    success(
        f"Backup created: {backup.name}"
    )

    setter = setting.get("set")

    if setter is None:
        error(
            "This setting cannot currently "
            "be changed."
        )
        return 1

    try:
        changed = setter(args.value)
    except Exception as exc:
        error(f"Could not apply change: {exc}")
        changed = False

    if not changed:
        error("Setting could not be changed.")
        return 1

    success(
        f"{name} changed to {args.value}"
    )

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Cozy Settings - a terminal-based "
            "Linux settings manager."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    subparsers.add_parser(
        "menu",
        help="Open the interactive settings menu",
    )

    subparsers.add_parser(
        "current",
        help="Show current settings",
    )

    subparsers.add_parser(
        "detect",
        help="Show detected desktop environment",
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
        help="Backup number or filename",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search settings",
    )

    search_parser.add_argument(
        "query",
        help="Search text",
    )

    set_parser = subparsers.add_parser(
        "set",
        help="Change a setting",
    )

    set_parser.add_argument(
        "category",
        help="Setting category",
    )

    set_parser.add_argument(
        "setting",
        help="Setting name",
    )

    set_parser.add_argument(
        "value",
        help="New value",
    )

    return parser


def command_search(query):
    results = search_settings(query)

    print()
    print(
        color(
            f"Search results for: {query}",
            Colors.BOLD,
        )
    )
    print()

    if not results:
        print("No settings found.")
        return 0

    for category, name in results:
        print(
            f"  {category} → {name}"
        )

    return 0


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
        banner()
        show_current()
        return 0

    if args.command == "detect":
        banner()
        show_system()
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

    if args.command == "search":
        return command_search(args.query)

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
