import argparse
import configparser
import json
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "Cozy Ricing"
FOOTER = "Made with ❤️ by Cozy"

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups"
DATA_FILE = BASE_DIR / "data.json"

USER_APPS_DIR = Path.home() / ".local" / "share" / "applications"


def ensure_dirs():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    USER_APPS_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    if not DATA_FILE.exists():
        return {}

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"Warning: could not read {DATA_FILE}")
        return {}


def save_data(data):
    DATA_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )


def get_application_dirs():
    directories = [
        USER_APPS_DIR,
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications"),
    ]

    return [
        directory
        for directory in directories
        if directory.exists()
    ]


def read_desktop_file(path):
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
    )

    parser.optionxform = str
    parser.read(path, encoding="utf-8")

    if "Desktop Entry" not in parser:
        return None

    return parser


def find_applications():
    applications = {}

    for directory in get_application_dirs():
        for desktop_file in directory.glob("*.desktop"):
            desktop_id = desktop_file.name

            if desktop_id in applications:
                continue

            try:
                parser = read_desktop_file(desktop_file)

                if parser is None:
                    continue

                entry = parser["Desktop Entry"]

                if entry.get("Type", "Application") != "Application":
                    continue

                if entry.get("NoDisplay", "").lower() == "true":
                    continue

                name = entry.get("Name", desktop_id)
                icon = entry.get("Icon", "")

                applications[desktop_id] = {
                    "id": desktop_id,
                    "name": name,
                    "icon": icon,
                    "path": str(desktop_file),
                }

            except (OSError, configparser.Error):
                continue

    return sorted(
        applications.values(),
        key=lambda app: app["name"].lower(),
    )


def find_application(desktop_id):
    for application in find_applications():
        if application["id"] == desktop_id:
            return application

    return None


def refresh_desktop_database():
    command = shutil.which("update-desktop-database")

    if not command:
        return

    try:
        subprocess.run(
            [command, str(USER_APPS_DIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def backup_desktop_file(desktop_id, source):
    backup_path = BACKUP_DIR / desktop_id

    if backup_path.exists():
        raise RuntimeError(
            f"A backup already exists: {backup_path}"
        )

    shutil.copy2(source, backup_path)

    return backup_path


def set_icon(desktop_id, icon_path):
    ensure_dirs()

    application = find_application(desktop_id)

    if application is None:
        print(f"Error: application '{desktop_id}' was not found.")
        print("Run './cozy_ricing.py list' to see available applications.")
        return False

    icon_path = Path(icon_path).expanduser().resolve()

    if not icon_path.exists():
        print(f"Error: icon does not exist: {icon_path}")
        return False

    if not icon_path.is_file():
        print(f"Error: icon is not a file: {icon_path}")
        return False

    data = load_data()

    if desktop_id in data:
        print(
            f"Error: {application['name']} is already customized."
        )
        print(
            f"Use './cozy_ricing.py restore {desktop_id}' "
            "before changing it again."
        )
        return False

    original_path = Path(application["path"])

    backup_path = backup_desktop_file(
        desktop_id,
        original_path,
    )

    target_path = USER_APPS_DIR / desktop_id

    shutil.copy2(
        original_path,
        target_path,
    )

    try:
        parser = read_desktop_file(target_path)

        if parser is None:
            raise RuntimeError(
                f"Could not parse desktop file: {target_path}"
            )

        entry = parser["Desktop Entry"]

        original_icon = entry.get("Icon", "")
        entry["Icon"] = str(icon_path)

        with target_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            parser.write(
                file,
                space_around_delimiters=False,
            )

    except Exception:
        if target_path.exists():
            target_path.unlink()

        if backup_path.exists():
            backup_path.unlink()

        raise

    data[desktop_id] = {
        "application_name": application["name"],
        "desktop_id": desktop_id,
        "original_path": str(original_path),
        "override_path": str(target_path),
        "backup_path": str(backup_path),
        "original_icon": original_icon,
        "new_icon": str(icon_path),
    }

    save_data(data)
    refresh_desktop_database()

    print()
    print(f"✓ Icon changed for {application['name']}")
    print(f"  New icon: {icon_path}")
    print(f"  Backup:   {backup_path}")
    print()
    print(FOOTER)

    return True


def restore_icon(desktop_id):
    ensure_dirs()

    data = load_data()

    if desktop_id not in data:
        print(
            f"Error: no Cozy Ricing backup exists for '{desktop_id}'."
        )
        return False

    customization = data[desktop_id]

    backup_path = Path(customization["backup_path"])
    override_path = Path(customization["override_path"])

    if not backup_path.exists():
        print(f"Error: backup is missing: {backup_path}")
        return False

    if override_path.exists():
        override_path.unlink()

    del data[desktop_id]
    save_data(data)

    refresh_desktop_database()

    print()
    print(
        f"✓ Restored {customization['application_name']}"
    )
    print(f"  Original icon: {customization['original_icon']}")
    print()
    print(FOOTER)

    return True


def list_applications():
    applications = find_applications()

    if not applications:
        print("No applications found.")
        return

    print(f"{APP_NAME} - Applications")
    print("=" * 50)
    print()

    for application in applications:
        print(f"{application['id']}")
        print(f"  Name: {application['name']}")
        print(f"  Icon: {application['icon']}")
        print(f"  File: {application['path']}")
        print()

    print(FOOTER)


def list_customizations():
    data = load_data()

    if not data:
        print("No customized applications.")
        print()
        print(FOOTER)
        return

    print(f"{APP_NAME} - Customized Applications")
    print("=" * 50)
    print()

    for desktop_id, customization in data.items():
        print(f"{desktop_id}")
        print(f"  Name:       {customization['application_name']}")
        print(f"  New icon:   {customization['new_icon']}")
        print(f"  Backup:     {customization['backup_path']}")
        print()

    print(FOOTER)


def main():
    parser = argparse.ArgumentParser(
        prog="cozy-ricing",
        description=(
            "Cozy Ricing - a simple Linux CLI application "
            "icon customization tool."
        ),
        epilog=FOOTER,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "list",
        help="List installed applications.",
    )

    subparsers.add_parser(
        "customized",
        help="List applications customized by Cozy Ricing.",
    )

    set_parser = subparsers.add_parser(
        "set",
        help="Change an application's icon.",
    )

    set_parser.add_argument(
        "desktop_id",
        help="Application desktop ID, e.g. firefox.desktop",
    )

    set_parser.add_argument(
        "icon",
        help="Path to the new icon image.",
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore an application's original icon.",
    )

    restore_parser.add_argument(
        "desktop_id",
        help="Application desktop ID, e.g. firefox.desktop",
    )

    args = parser.parse_args()

    try:
        if args.command == "list":
            list_applications()

        elif args.command == "customized":
            list_customizations()

        elif args.command == "set":
            success = set_icon(
                args.desktop_id,
                args.icon,
            )

            if not success:
                sys.exit(1)

        elif args.command == "restore":
            success = restore_icon(
                args.desktop_id,
            )

            if not success:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)

    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
# not tested
