from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys


BACKUP_FILE = Path.home() / ".linux_font_manager_backup.json"


COLORS = {
    "1": ("White", "#FFFFFF"),
    "2": ("Black", "#000000"),
    "3": ("Red", "#FF0000"),
    "4": ("Green", "#00FF00"),
    "5": ("Blue", "#0000FF"),
    "6": ("Yellow", "#FFFF00"),
    "7": ("Cyan", "#00FFFF"),
    "8": ("Magenta", "#FF00FF"),
    "9": ("Orange", "#FFA500"),
    "10": ("Purple", "#800080"),
    "11": ("Pink", "#FFC0CB"),
    "12": ("Gray", "#808080"),
}


def print_header():
    print("Made with ❤️ by Cozy")
    print()
    print("Linux Desktop Font & Color Manager")
    print("-----------------------------------")
    print()


def command_exists(command):
    return shutil.which(command) is not None


def run_command(command, check=False):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check,
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except (OSError, subprocess.SubprocessError) as error:
        return 1, "", str(error)


def detect_desktop_environment():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    session = os.environ.get("DESKTOP_SESSION", "")

    values = f"{desktop}:{session}".lower()

    if "kde" in values or "plasma" in values:
        return "KDE Plasma"

    if "cinnamon" in values:
        return "Cinnamon"

    if "xfce" in values:
        return "XFCE"

    if "mate" in values:
        return "MATE"

    if "lxqt" in values:
        return "LXQt"

    if "lxde" in values:
        return "LXDE"

    if "budgie" in values:
        return "Budgie"

    if "deepin" in values or "dde" in values:
        return "Deepin"

    if "gnome" in values:
        return "GNOME"

    if command_exists("kreadconfig6"):
        return "KDE Plasma"

    if command_exists("xfconf-query"):
        return "XFCE"

    if command_exists("gsettings"):
        if command_exists("gnome-shell"):
            return "GNOME"

    return "Unknown"


def get_font_list():
    if not command_exists("fc-list"):
        return []

    code, output, error = run_command(
        ["fc-list", ":", "family"]
    )

    if code != 0:
        return []

    fonts = set()

    for line in output.splitlines():
        for family in line.split(","):
            family = family.strip()

            if family:
                fonts.add(family)

    return sorted(fonts, key=str.lower)


def show_fonts(fonts):
    print()
    print("Available Fonts")
    print("================")
    print()

    columns = 2
    rows = (len(fonts) + columns - 1) // columns

    for row in range(rows):
        line = ""

        for column in range(columns):
            index = row + column * rows

            if index < len(fonts):
                line += f"{index + 1:>4}. {fonts[index]:<40}"

        print(line.rstrip())

    print()
    print(f"Total fonts found: {len(fonts)}")
    print()


def select_font(fonts):
    while True:
        choice = input(
            "Enter a font number or type 'search': "
        ).strip()

        if choice.lower() == "search":
            search = input("Search for a font: ").strip().lower()

            if not search:
                continue

            matches = [
                font
                for font in fonts
                if search in font.lower()
            ]

            if not matches:
                print("\nNo matching fonts were found.\n")
                continue

            print()
            print("Matching Fonts")
            print("==============")
            print()

            for index, font in enumerate(matches, start=1):
                print(f"{index:>3}. {font}")

            print()

            selected = input(
                "Select a font number or press Enter to search again: "
            ).strip()

            if not selected:
                continue

            try:
                number = int(selected)
            except ValueError:
                print("\nInvalid selection.\n")
                continue

            if 1 <= number <= len(matches):
                return matches[number - 1]

            print("\nInvalid selection.\n")
            continue

        try:
            number = int(choice)
        except ValueError:
            print("\nInvalid selection.\n")
            continue

        if 1 <= number <= len(fonts):
            return fonts[number - 1]

        print("\nInvalid font number.\n")


def preview_font(font):
    print()
    print("Font Preview")
    print("============")
    print()
    print(f"Selected font: {font}")
    print()
    print("Hello World")
    print()
    print(
        "The actual font appearance depends on the terminal."
    )
    print(
        "The selected desktop font will be applied after confirmation."
    )
    print()


def is_hex_color(value):
    if not value.startswith("#"):
        return False

    if len(value) not in (4, 7):
        return False

    return all(
        character in "0123456789abcdefABCDEF"
        for character in value[1:]
    )


def normalize_color(value):
    if len(value) == 4:
        return "#" + "".join(
            character * 2
            for character in value[1:]
        ).upper()

    return value.upper()


def select_color():
    print()
    print("Font Color")
    print("==========")
    print()

    for number, color in COLORS.items():
        print(
            f"{number:>2}. "
            f"{color[0]:<10} "
            f"{color[1]}"
        )

    print("13. Custom HEX color")
    print()

    while True:
        choice = input("Select a color: ").strip()

        if choice in COLORS:
            return COLORS[choice]

        if choice == "13":
            while True:
                value = input(
                    "Enter HEX color, for example #3498DB: "
                ).strip()

                if is_hex_color(value):
                    value = normalize_color(value)
                    return "Custom", value

                print("\nInvalid HEX color.\n")

        print("\nInvalid selection.\n")


def color_to_ansi(color):
    value = color.lstrip("#")

    if len(value) != 6:
        return ""

    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return ""

    return f"\033[38;2;{red};{green};{blue}m"


def preview_selection(font, color_name, color):
    ansi = color_to_ansi(color)

    print()
    print("Final Preview")
    print("=============")
    print()
    print(f"Font:  {font}")
    print(f"Color: {color_name} ({color})")
    print()

    if ansi:
        print(f"{ansi}Hello World\033[0m")
    else:
        print("Hello World")

    print()


def gsettings_get(schema, key):
    if not command_exists("gsettings"):
        return None

    code, output, error = run_command(
        ["gsettings", "get", schema, key]
    )

    if code != 0:
        return None

    return output


def gsettings_set(schema, key, value):
    if not command_exists("gsettings"):
        return False

    code, output, error = run_command(
        ["gsettings", "set", schema, key, value]
    )

    return code == 0


def set_gsettings_if_available(schema, key, value):
    current = gsettings_get(schema, key)

    if current is None:
        return False, None

    return gsettings_set(schema, key, value), current


def get_gnome_settings():
    settings = {}

    candidates = [
        ("org.gnome.desktop.interface", "font-name"),
        ("org.gnome.desktop.interface", "document-font-name"),
        ("org.gnome.desktop.interface", "monospace-font-name"),
    ]

    for schema, key in candidates:
        value = gsettings_get(schema, key)

        if value is not None:
            settings[f"{schema}|{key}"] = value

    return settings


def apply_gnome_font(font):
    targets = [
        (
            "org.gnome.desktop.interface",
            "font-name",
            f"{font} 11",
        ),
        (
            "org.gnome.desktop.interface",
            "document-font-name",
            f"{font} 11",
        ),
        (
            "org.gnome.desktop.interface",
            "monospace-font-name",
            f"{font} 11",
        ),
    ]

    changed = False

    for schema, key, value in targets:
        current = gsettings_get(schema, key)

        if current is None:
            continue

        if gsettings_set(schema, key, value):
            changed = True

    return changed


def apply_cinnamon_font(font):
    targets = [
        (
            "org.cinnamon.desktop.interface",
            "font-name",
            f"{font} 10",
        ),
        (
            "org.cinnamon.desktop.interface",
            "document-font-name",
            f"{font} 10",
        ),
        (
            "org.cinnamon.desktop.interface",
            "monospace-font-name",
            f"{font} 10",
        ),
    ]

    changed = False

    for schema, key, value in targets:
        current = gsettings_get(schema, key)

        if current is None:
            continue

        if gsettings_set(schema, key, value):
            changed = True

    return changed


def xfconf_get(channel, property_name):
    if not command_exists("xfconf-query"):
        return None

    code, output, error = run_command(
        [
            "xfconf-query",
            "-c",
            channel,
            "-p",
            property_name,
        ]
    )

    if code != 0:
        return None

    return output


def xfconf_set(channel, property_name, value):
    if not command_exists("xfconf-query"):
        return False

    code, output, error = run_command(
        [
            "xfconf-query",
            "-c",
            channel,
            "-p",
            property_name,
            "-s",
            value,
        ]
    )

    return code == 0


def apply_xfce_font(font):
    targets = [
        (
            "xsettings",
            "/Gtk/FontName",
            f"{font} 10",
        ),
    ]

    changed = False

    for channel, property_name, value in targets:
        current = xfconf_get(channel, property_name)

        if current is None:
            continue

        if xfconf_set(channel, property_name, value):
            changed = True

    return changed


def apply_mate_font(font):
    targets = [
        (
            "org.mate.interface",
            "font-name",
            f"{font} 10",
        ),
        (
            "org.mate.interface",
            "document-font-name",
            f"{font} 10",
        ),
        (
            "org.mate.interface",
            "monospace-font-name",
            f"{font} 10",
        ),
    ]

    changed = False

    for schema, key, value in targets:
        current = gsettings_get(schema, key)

        if current is None:
            continue

        if gsettings_set(schema, key, value):
            changed = True

    return changed


def apply_budgie_font(font):
    return apply_gnome_font(font)


def apply_deepin_font(font):
    targets = [
        (
            "com.deepin.dde.appearance",
            "font",
            font,
        ),
    ]

    changed = False

    for schema, key, value in targets:
        current = gsettings_get(schema, key)

        if current is None:
            continue

        if gsettings_set(schema, key, value):
            changed = True

    if not changed:
        changed = apply_gnome_font(font)

    return changed


def apply_kde_font(font):
    if not command_exists("kwriteconfig6"):
        if not command_exists("kwriteconfig5"):
            return False

    writer = (
        "kwriteconfig6"
        if command_exists("kwriteconfig6")
        else "kwriteconfig5"
    )

    font_value = f"{font},11,-1,5,50,0,0,0,0,0"

    commands = [
        [
            writer,
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "font",
            font_value,
        ],
        [
            writer,
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "menuFont",
            font_value,
        ],
        [
            writer,
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "smallestReadableFont",
            font_value,
        ],
        [
            writer,
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "toolBarFont",
            font_value,
        ],
        [
            writer,
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "fixed",
            font_value,
        ],
    ]

    changed = False

    for command in commands:
        code, output, error = run_command(command)

        if code == 0:
            changed = True

    if changed and command_exists("kbuildsycoca6"):
        run_command(["kbuildsycoca6"])

    elif changed and command_exists("kbuildsycoca5"):
        run_command(["kbuildsycoca5"])

    return changed


def apply_lxqt_font(font):
    if not command_exists("lxqt-config"):
        return False

    print()
    print(
        "LXQt detected. Its font configuration is handled through "
        "the LXQt desktop settings."
    )
    print(
        "Please use LXQt Appearance settings to apply the font."
    )

    return False


def apply_lxde_font(font):
    if command_exists("lxappearance"):
        print()
        print(
            "LXDE detected. Opening LXAppearance so you can "
            "apply the selected font."
        )

        try:
            subprocess.Popen(["lxappearance"])
            return True
        except OSError:
            return False

    return False


def get_gtk_css_paths():
    paths = []

    home = Path.home()

    paths.append(
        home / ".config" / "gtk-3.0" / "gtk.css"
    )

    paths.append(
        home / ".config" / "gtk-4.0" / "gtk.css"
    )

    return paths


def backup_file_if_exists(path, backups):
    if not path.exists():
        return

    backup_path = path.with_name(
        path.name + ".linux-font-manager.backup"
    )

    try:
        shutil.copy2(path, backup_path)
        backups[str(path)] = str(backup_path)
    except OSError:
        pass


def apply_gtk_color(color):
    css_paths = get_gtk_css_paths()

    changed = False

    for path in css_paths:
        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            existing = ""

            if path.exists():
                existing = path.read_text(
                    encoding="utf-8"
                )

            marker = "/* Cozy Linux Font Manager */"

            rule = (
                f"{marker}\n"
                f"* {{\n"
                f"    color: {color};\n"
                f"}}\n"
                f"{marker} END\n"
            )

            start_marker = marker
            end_marker = f"{marker} END"

            pattern = re.compile(
                re.escape(start_marker)
                + r".*?"
                + re.escape(end_marker)
                + r"\n?",
                re.DOTALL,
            )

            if pattern.search(existing):
                updated = pattern.sub(
                    rule,
                    existing,
                    count=1,
                )
            else:
                if existing and not existing.endswith("\n"):
                    existing += "\n"

                updated = existing + "\n" + rule

            path.write_text(
                updated,
                encoding="utf-8",
            )

            changed = True

        except OSError:
            continue

    return changed


def create_backup(desktop):
    backup = {
        "desktop": desktop,
        "files": {},
        "gsettings": {},
    }

    if desktop in {
        "GNOME",
        "Cinnamon",
        "MATE",
        "Budgie",
        "Deepin",
    }:
        settings = [
            (
                "org.gnome.desktop.interface",
                "font-name",
            ),
            (
                "org.gnome.desktop.interface",
                "document-font-name",
            ),
            (
                "org.gnome.desktop.interface",
                "monospace-font-name",
            ),
            (
                "org.cinnamon.desktop.interface",
                "font-name",
            ),
            (
                "org.cinnamon.desktop.interface",
                "document-font-name",
            ),
            (
                "org.cinnamon.desktop.interface",
                "monospace-font-name",
            ),
            (
                "org.mate.interface",
                "font-name",
            ),
            (
                "org.mate.interface",
                "document-font-name",
            ),
            (
                "org.mate.interface",
                "monospace-font-name",
            ),
        ]

        for schema, key in settings:
            value = gsettings_get(schema, key)

            if value is not None:
                backup["gsettings"][
                    f"{schema}|{key}"
                ] = value

    for path in get_gtk_css_paths():
        if path.exists():
            backup_file_if_exists(
                path,
                backup["files"],
            )

    try:
        BACKUP_FILE.write_text(
            json.dumps(
                backup,
                indent=4,
            ),
            encoding="utf-8",
        )

        return True

    except OSError as error:
        print(f"\nCould not create backup: {error}")
        return False


def apply_font_for_desktop(desktop, font):
    if desktop == "GNOME":
        return apply_gnome_font(font)

    if desktop == "KDE Plasma":
        return apply_kde_font(font)

    if desktop == "XFCE":
        return apply_xfce_font(font)

    if desktop == "Cinnamon":
        return apply_cinnamon_font(font)

    if desktop == "MATE":
        return apply_mate_font(font)

    if desktop == "Budgie":
        return apply_budgie_font(font)

    if desktop == "Deepin":
        return apply_deepin_font(font)

    if desktop == "LXQt":
        return apply_lxqt_font(font)

    if desktop == "LXDE":
        return apply_lxde_font(font)

    return False


def restore_backup():
    if not BACKUP_FILE.exists():
        print("\nNo backup was found.")
        return

    try:
        backup = json.loads(
            BACKUP_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError) as error:
        print(f"\nCould not read backup: {error}")
        return

    restored = 0

    for setting, value in backup.get(
        "gsettings",
        {}
    ).items():
        parts = setting.split("|", 1)

        if len(parts) != 2:
            continue

        schema, key = parts

        if gsettings_set(
            schema,
            key,
            value,
        ):
            restored += 1

    for original, backup_path in backup.get(
        "files",
        {}
    ).items():
        original_path = Path(original)
        backup_file = Path(backup_path)

        if not backup_file.exists():
            continue

        try:
            shutil.copy2(
                backup_file,
                original_path,
            )

            restored += 1

        except OSError:
            continue

    print()
    print(f"Restored {restored} setting(s)/file(s).")


def apply_selection(desktop, font, color_name, color):
    print()
    print("Selected Settings")
    print("=================")
    print()
    print(f"Desktop: {desktop}")
    print(f"Font:    {font}")
    print(f"Color:   {color_name} ({color})")
    print()

    confirmation = input(
        "Apply these settings? [yes/no] "
    ).strip().lower()

    if confirmation not in {"yes", "y"}:
        print("\nCancelled.")
        return

    print()
    print("Creating backup...")

    if not create_backup(desktop):
        print(
            "\nThe backup could not be created."
        )
        print(
            "Nothing was changed."
        )
        return

    print("Backup created.")

    print()
    print("Applying font...")

    font_changed = apply_font_for_desktop(
        desktop,
        font,
    )

    if font_changed:
        print("Font applied successfully.")
    else:
        print(
            "The font could not be automatically "
            "applied for this desktop environment."
        )

    print()
    print("Applying color...")

    color_changed = apply_gtk_color(color)

    if color_changed:
        print(
            "GTK text color configuration updated."
        )
    else:
        print(
            "The color could not be applied automatically."
        )

    print()
    print("Finished.")
    print()
    print("Backup:")
    print(f"  {BACKUP_FILE}")
    print()
    print(
        "Some applications may need to be restarted "
        "before the changes appear."
    )


def show_system_information(desktop, fonts):
    print()
    print("System Information")
    print("==================")
    print()
    print(f"Detected desktop: {desktop}")
    print(f"Available fonts:  {len(fonts)}")
    print(f"Home directory:   {Path.home()}")
    print()

    if desktop == "Unknown":
        print(
            "The desktop environment could not be identified."
        )
        print(
            "Font changes may need to be configured manually."
        )
        print()


def main():
    print_header()

    desktop = detect_desktop_environment()
    fonts = get_font_list()

    print(f"Detected desktop environment: {desktop}")
    print()

    if not fonts:
        print(
            "No fonts could be detected."
        )
        print(
            "Make sure fontconfig is installed."
        )
        return 1

    while True:
        print("What would you like to do?")
        print()
        print("1. Choose font and color")
        print("2. Show available fonts")
        print("3. Show system information")
        print("4. Restore previous settings")
        print("5. Exit")
        print()

        choice = input(
            "Select 1-5: "
        ).strip()

        if choice == "1":
            show_fonts(fonts)

            font = select_font(fonts)

            preview_font(font)

            color_name, color = select_color()

            preview_selection(
                font,
                color_name,
                color,
            )

            apply_selection(
                desktop,
                font,
                color_name,
                color,
            )

            print()
            input(
                "Press Enter to return to the menu..."
            )
            print()

        elif choice == "2":
            show_fonts(fonts)

            input(
                "Press Enter to return to the menu..."
            )
            print()

        elif choice == "3":
            show_system_information(
                desktop,
                fonts,
            )

            input(
                "Press Enter to return to the menu..."
            )
            print()

        elif choice == "4":
            restore_backup()

            print()
            input(
                "Press Enter to return to the menu..."
            )
            print()

        elif choice == "5":
            print("\nGoodbye.")
            return 0

        else:
            print(
                "\nInvalid selection. "
                "Please choose 1-5.\n"
            )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(130)
      # not tested dont go after me if this nukes your DE
