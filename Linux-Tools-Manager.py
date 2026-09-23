import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPO_OWNER = "SpicyCitrus"
REPO_NAME = "Linux-Tools"
REPO_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

MANIFEST_FILE = ".linux_tools_manifest.json"
CONFIG_FILE = ".ltm_config.json"

LTM_FILE_NAMES = {
    "linux_tools_manager.py",
    "linux-tools-manager.py",
    "ltm.py"
}

LTM_LOGO = r"""
.-""""""""-.
.-'            '-.
.'                  '.
/                      \
/                        \
|                          |
|          L T M           |
|                          |
\                        /
'.                  .'
'-.            .-'
'-.______.-'
"""


DEFAULT_CONFIG = {
    "auto_update": False,
    "auto_cleanup": False,
    "silence_updates": False
}


def get_ltm_directory():
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def get_config_path():
    return get_ltm_directory() / CONFIG_FILE


def get_manifest_path():
    return Path.cwd() / MANIFEST_FILE


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Linux-Tools-Manager"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def download_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Linux-Tools-Manager"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:
        return response.read()


def load_config():
    path = get_config_path()

    if not path.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            data = {}

    except (
        OSError,
        json.JSONDecodeError
    ):
        data = {}

    config = DEFAULT_CONFIG.copy()

    for key in DEFAULT_CONFIG:
        if key in data:
            config[key] = bool(
                data[key]
            )

    if data != config:
        save_config(config)

    return config


def save_config(config):
    path = get_config_path()
    temporary_path = path.with_suffix(
        ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            config,
            file,
            indent=4
        )
        file.write("\n")

    temporary_path.replace(path)


def load_manifest():
    path = get_manifest_path()

    if not path.exists():
        return {}

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {}

        return data

    except (
        OSError,
        json.JSONDecodeError
    ):
        return {}


def save_manifest(manifest):
    path = get_manifest_path()
    temporary_path = path.with_suffix(
        ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            manifest,
            file,
            indent=4
        )
        file.write("\n")

    temporary_path.replace(path)


def get_default_branch():
    data = get_json(
        REPO_API_URL
    )

    return data.get(
        "default_branch",
        "main"
    )


def get_repo_files():
    branch = get_default_branch()

    tree_url = (
        f"{REPO_API_URL}/git/trees/"
        f"{urllib.parse.quote(branch, safe='')}"
        f"?recursive=1"
    )

    data = get_json(
        tree_url
    )

    if data.get("truncated"):
        raise RuntimeError(
            "The GitHub repository tree is too large "
            "to retrieve completely."
        )

    files = []

    for item in data.get(
        "tree",
        []
    ):
        if item.get("type") != "blob":
            continue

        path = item.get("path")

        if not path:
            continue

        files.append({
            "path": path,
            "name": Path(path).name,
            "sha": item.get("sha"),
            "url": (
                f"https://raw.githubusercontent.com/"
                f"{REPO_OWNER}/{REPO_NAME}/"
                f"{urllib.parse.quote(branch, safe='')}/"
                f"{urllib.parse.quote(path, safe='/')}"
            )
        })

    files.sort(
        key=lambda item: item["path"].lower()
    )

    return files, branch


def calculate_hash(data):
    return hashlib.sha256(data).hexdigest()


def calculate_file_hash(path):
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def get_terminal_width():
    try:
        return shutil.get_terminal_size(
            (80, 24)
        ).columns
    except Exception:
        return 80


def print_right_aligned_logo():
    width = get_terminal_width()

    for line in LTM_LOGO.strip(
        "\n"
    ).splitlines():
        padding = max(
            0,
            width - len(line) - 2
        )

        print(
            " " * padding + line
        )


def print_header():
    print()

    print_right_aligned_logo()

    print()
    print("Made with ❤️ by Cozy")
    print()
    print("Linux Tools Manager")
    print("-------------------")
    print(
        f"Repository:   "
        f"{REPO_OWNER}/{REPO_NAME}"
    )
    print(
        f"Current path: "
        f"{Path.cwd()}"
    )
    print()


def confirm(prompt):
    while True:
        answer = input(
            f"{prompt} [yes/no] "
        ).strip().lower()

        if answer in {
            "yes",
            "y"
        }:
            return True

        if answer in {
            "no",
            "n"
        }:
            return False

        print(
            "Please enter yes or no."
        )


def find_ltm_file(files):
    current_name = Path(
        sys.argv[0]
    ).name.lower()

    for item in files:
        if item["name"].lower() == current_name:
            return item

    for item in files:
        if item["name"].lower() in {
            name.lower()
            for name in LTM_FILE_NAMES
        }:
            return item

    return None


def find_backup_files():
    backup_files = []

    try:
        for path in Path.cwd().iterdir():
            if not path.is_file():
                continue

            if path.name.endswith(
                ".backup"
            ):
                backup_files.append(
                    path
                )

    except OSError:
        return []

    backup_files.sort(
        key=lambda path: path.name.lower()
    )

    return backup_files


def cleanup_backups(
    ask_confirmation=True
):
    backup_files = find_backup_files()

    if not backup_files:
        if ask_confirmation:
            print()
            print(
                "No backup files were found."
            )
            print()

        return 0

    if ask_confirmation:
        print()
        print(
            "========================================"
        )
        print(
            "                 CleanUP"
        )
        print(
            "========================================"
        )
        print()

        print(
            "Backup files found:"
        )
        print()

        for index, path in enumerate(
            backup_files,
            start=1
        ):
            print(
                f"  {index:>3}. "
                f"{path.name}"
            )

        print()
        print(
            f"Total backup files: "
            f"{len(backup_files)}"
        )
        print()

        print(
            "WARNING: This will permanently "
            "delete these backup files."
        )

        print()

        if not confirm(
            "Delete all backup files"
        ):
            print()
            print(
                "CleanUP cancelled."
            )
            print()
            return 0

    deleted = 0
    failed = 0

    for path in backup_files:
        try:
            path.unlink()
            deleted += 1

            if ask_confirmation:
                print(
                    f"  Deleted: {path.name}"
                )

        except OSError as error:
            failed += 1

            if ask_confirmation:
                print(
                    f"  Could not delete "
                    f"{path.name}: {error}"
                )

    if ask_confirmation:
        print()
        print(
            "CleanUP complete."
        )
        print(
            f"Deleted: {deleted}"
        )
        print(
            f"Failed:  {failed}"
        )
        print()

    return deleted


def update_ltm(
    ltm_item,
    remote_data,
    config
):
    local_path = Path(
        sys.argv[0]
    ).resolve()

    if not local_path.exists():
        return False

    backup_path = local_path.with_name(
        local_path.name + ".backup"
    )

    temporary_path = local_path.with_name(
        local_path.name
        + ".linux-tools.tmp"
    )

    if backup_path.exists():
        try:
            backup_path.unlink()
        except OSError:
            pass

    try:
        shutil.copy2(
            local_path,
            backup_path
        )

    except OSError as error:
        print(
            f"Could not create LTM backup: "
            f"{error}"
        )
        return False

    try:
        temporary_path.write_bytes(
            remote_data
        )

        temporary_path.replace(
            local_path
        )

    except OSError as error:
        print(
            f"Could not update LTM: "
            f"{error}"
        )

        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except OSError:
            pass

        return False

    print(
        "Linux Tools Manager was updated."
    )

    if config["auto_cleanup"]:
        try:
            backup_path.unlink()

            print(
                "Automatic backup cleanup "
                "removed the old LTM backup."
            )

        except OSError:
            print(
                "The old LTM backup could not "
                "be automatically removed."
            )
    else:
        print(
            f"Backup created: "
            f"{backup_path}"
        )

    print(
        "Please restart LTM."
    )

    return True


def check_ltm_update(
    files,
    config
):
    ltm_item = find_ltm_file(
        files
    )

    if not ltm_item:
        return

    local_path = Path(
        sys.argv[0]
    ).resolve()

    if not local_path.exists():
        return

    try:
        local_hash = calculate_file_hash(
            local_path
        )

    except OSError:
        return

    try:
        remote_data = download_url(
            ltm_item["url"]
        )

    except Exception:
        return

    remote_hash = calculate_hash(
        remote_data
    )

    if local_hash == remote_hash:
        if not config["silence_updates"]:
            print(
                "Linux Tools Manager "
                "is up to date."
            )
            print()

        return

    if config["auto_update"]:
        if not config["silence_updates"]:
            print()
            print(
                "LTM update found."
            )
            print(
                "Automatic update is enabled."
            )
            print()

        update_ltm(
            ltm_item,
            remote_data,
            config
        )

        print()
        return

    if config["silence_updates"]:
        return

    print()
    print(
        "========================================"
    )
    print(
        "       LTM UPDATE AVAILABLE"
    )
    print(
        "========================================"
    )
    print()

    print(
        "A newer Linux Tools Manager "
        "is available."
    )

    print()

    if confirm(
        "Update Linux Tools Manager"
    ):
        update_ltm(
            ltm_item,
            remote_data,
            config
        )
    else:
        print(
            "LTM update skipped."
        )

    print()


def print_setting_status(value):
    return "ON" if value else "OFF"


def settings_menu(config):
    while True:
        print()
        print(
            "========================================"
        )
        print(
            "                Settings"
        )
        print(
            "========================================"
        )
        print()

        print(
            "1. Automatic LTM updates: "
            f"{print_setting_status(config['auto_update'])}"
        )

        print(
            "2. Automatic backup cleanup: "
            f"{print_setting_status(config['auto_cleanup'])}"
        )

        print(
            "3. Silence update notifications: "
            f"{print_setting_status(config['silence_updates'])}"
        )

        print(
            "4. Back"
        )

        print()

        choice = input(
            "Select 1, 2, 3, or 4: "
        ).strip()

        if choice == "1":
            config["auto_update"] = not config[
                "auto_update"
            ]

            save_config(
                config
            )

            print()
            print(
                "Automatic LTM updates: "
                f"{print_setting_status(config['auto_update'])}"
            )

        elif choice == "2":
            config["auto_cleanup"] = not config[
                "auto_cleanup"
            ]

            save_config(
                config
            )

            print()
            print(
                "Automatic backup cleanup: "
                f"{print_setting_status(config['auto_cleanup'])}"
            )

        elif choice == "3":
            config["silence_updates"] = not config[
                "silence_updates"
            ]

            save_config(
                config
            )

            print()
            print(
                "Silence update notifications: "
                f"{print_setting_status(config['silence_updates'])}"
            )

        elif choice == "4":
            save_config(
                config
            )
            return

        else:
            print()
            print(
                "Invalid selection."
            )


def print_repo_files(files):
    print()
    print(
        "Available files:"
    )
    print()

    for index, item in enumerate(
        files,
        start=1
    ):
        print(
            f"{index:>3}. "
            f"{item['path']}"
        )

    print()


def parse_selections(
    value,
    maximum
):
    selections = set()

    parts = value.replace(
        ",",
        " "
    ).split()

    for part in parts:
        if "-" in part:
            pieces = part.split(
                "-",
                1
            )

            if len(pieces) != 2:
                continue

            try:
                start = int(
                    pieces[0]
                )

                end = int(
                    pieces[1]
                )

            except ValueError:
                continue

            if start > end:
                start, end = (
                    end,
                    start
                )

            for number in range(
                start,
                end + 1
            ):
                if (
                    1
                    <= number
                    <= maximum
                ):
                    selections.add(
                        number
                    )

        else:
            try:
                number = int(
                    part
                )

            except ValueError:
                continue

            if (
                1
                <= number
                <= maximum
            ):
                selections.add(
                    number
                )

    return sorted(
        selections
    )


def download_file(
    item,
    destination
):
    try:
        data = download_url(
            item["url"]
        )

    except urllib.error.HTTPError as error:
        print(
            f"  Download failed: "
            f"HTTP {error.code}"
        )
        return False

    except urllib.error.URLError as error:
        print(
            f"  Download failed: "
            f"{error.reason}"
        )
        return False

    except Exception as error:
        print(
            f"  Download failed: "
            f"{error}"
        )
        return False

    temporary_path = destination.with_name(
        destination.name
        + ".linux-tools.tmp"
    )

    try:
        temporary_path.write_bytes(
            data
        )

        temporary_path.replace(
            destination
        )

    except OSError as error:
        print(
            f"  Could not write file: "
            f"{error}"
        )

        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except OSError:
            pass

        return False

    return True


def download_new_tools(files):
    if not files:
        print(
            "\nNo files were found "
            "in the repository."
        )
        return

    print_repo_files(
        files
    )

    selection = input(
        "Select files to download "
        "(example: 1 3 5 or 1-4): "
    ).strip()

    selections = parse_selections(
        selection,
        len(files)
    )

    if not selections:
        print(
            "\nNo valid files were selected."
        )
        return

    selected_files = [
        files[index - 1]
        for index in selections
    ]

    print()
    print(
        "Selected files:"
    )

    for item in selected_files:
        print(
            f"  - {item['path']}"
        )

    print()

    if not confirm(
        "Download these files"
    ):
        print(
            "\nDownload cancelled."
        )
        return

    manifest = load_manifest()
    downloaded = 0

    for item in selected_files:
        destination = (
            Path.cwd()
            / item["name"]
        )

        print(
            f"\nDownloading "
            f"{item['path']}..."
        )

        if destination.exists():
            print(
                f"  {destination.name} "
                f"already exists."
            )

            if not confirm(
                "  Replace the existing file"
            ):
                print(
                    "  Skipped."
                )
                continue

        if download_file(
            item,
            destination
        ):
            try:
                file_hash = (
                    calculate_file_hash(
                        destination
                    )
                )

            except OSError as error:
                print(
                    "  File downloaded, "
                    "but hash failed: "
                    f"{error}"
                )
                continue

            manifest[
                item["name"]
            ] = {
                "repo_path": item["path"],
                "repo_sha": item["sha"],
                "sha256": file_hash
            }

            downloaded += 1

            print(
                f"  Saved to: "
                f"{destination}"
            )

    save_manifest(
        manifest
    )

    print()
    print(
        f"Downloaded: "
        f"{downloaded} file(s)."
    )


def find_matching_local_files(
    files
):
    repo_by_name = {}

    for item in files:
        name = item["name"]

        if name not in repo_by_name:
            repo_by_name[name] = []

        repo_by_name[name].append(
            item
        )

    local_matches = []

    for path in Path.cwd().iterdir():
        if not path.is_file():
            continue

        if path.name in {
            MANIFEST_FILE,
            CONFIG_FILE
        }:
            continue

        if path.name.endswith(
            ".backup"
        ):
            continue

        matches = repo_by_name.get(
            path.name
        )

        if not matches:
            continue

        local_matches.append({
            "local_path": path,
            "repo_matches": matches
        })

    return local_matches


def update_current_tools(
    files,
    config
):
    local_matches = (
        find_matching_local_files(
            files
        )
    )

    if not local_matches:
        print()
        print(
            "No files in the current "
            "directory match files"
        )
        print(
            "from the Linux-Tools repository."
        )
        return

    manifest = load_manifest()

    print()
    print(
        "Matching files in the "
        "current directory:"
    )
    print()

    update_items = []

    for item in local_matches:
        local_path = item[
            "local_path"
        ]

        matches = item[
            "repo_matches"
        ]

        if len(matches) == 1:
            repo_item = matches[0]

            update_items.append({
                "local_path": local_path,
                "repo_item": repo_item
            })

            print(
                f"{len(update_items):>3}. "
                f"{local_path.name}"
            )

            print(
                f"     Repository: "
                f"{repo_item['path']}"
            )

        else:
            print(
                f"    {local_path.name}"
            )

            print(
                "     Multiple repository "
                "files have this name:"
            )

            for match in matches:
                print(
                    f"       - "
                    f"{match['path']}"
                )

            print(
                "     Skipped because the "
                "repository path is ambiguous."
            )

    if not update_items:
        print()
        print(
            "No unambiguous repository "
            "files were found."
        )
        return

    print()

    selection = input(
        "Select files to update "
        "(example: 1 3 or 1-4): "
    ).strip()

    selections = parse_selections(
        selection,
        len(update_items)
    )

    if not selections:
        print(
            "\nNo valid files were selected."
        )
        return

    selected_items = [
        update_items[index - 1]
        for index in selections
    ]

    print()
    print(
        "Selected files:"
    )

    for item in selected_items:
        print(
            f"  - "
            f"{item['local_path'].name} "
            f"<- "
            f"{item['repo_item']['path']}"
        )

    print()

    if not confirm(
        "Check and update these files"
    ):
        print(
            "\nUpdate cancelled."
        )
        return

    updated = 0
    current = 0
    failed = 0

    for item in selected_items:
        local_path = item[
            "local_path"
        ]

        repo_item = item[
            "repo_item"
        ]

        print(
            f"\nChecking "
            f"{local_path.name}..."
        )

        try:
            remote_data = download_url(
                repo_item["url"]
            )

        except urllib.error.HTTPError as error:
            print(
                "  Could not retrieve "
                "latest version: "
                f"HTTP {error.code}"
            )

            failed += 1
            continue

        except urllib.error.URLError as error:
            print(
                "  Could not retrieve "
                "latest version: "
                f"{error.reason}"
            )

            failed += 1
            continue

        except Exception as error:
            print(
                "  Could not retrieve "
                "latest version: "
                f"{error}"
            )

            failed += 1
            continue

        remote_hash = calculate_hash(
            remote_data
        )

        try:
            local_hash = (
                calculate_file_hash(
                    local_path
                )
            )

        except OSError as error:
            print(
                f"  Could not read "
                f"local file: {error}"
            )

            failed += 1
            continue

        if local_hash == remote_hash:
            print(
                "  Already up to date."
            )

            manifest[
                local_path.name
            ] = {
                "repo_path": repo_item["path"],
                "repo_sha": repo_item["sha"],
                "sha256": local_hash
            }

            current += 1
            continue

        managed_entry = manifest.get(
            local_path.name
        )

        if managed_entry:
            if (
                managed_entry.get(
                    "repo_path"
                )
                != repo_item["path"]
            ):
                print(
                    "  Repository path "
                    "does not match manifest."
                )

                print(
                    "  Skipped for safety."
                )

                failed += 1
                continue

        print(
            "  A newer version "
            "is available."
        )

        if not confirm(
            "  Replace the local file"
        ):
            print(
                "  Skipped."
            )
            continue

        backup_path = (
            local_path.with_name(
                local_path.name
                + ".backup"
            )
        )

        if backup_path.exists():
            try:
                backup_path.unlink()
            except OSError:
                pass

        try:
            shutil.copy2(
                local_path,
                backup_path
            )

        except OSError as error:
            print(
                f"  Could not create "
                f"backup: {error}"
            )

            failed += 1
            continue

        temporary_path = (
            local_path.with_name(
                local_path.name
                + ".linux-tools.tmp"
            )
        )

        try:
            temporary_path.write_bytes(
                remote_data
            )

            temporary_path.replace(
                local_path
            )

        except OSError as error:
            print(
                f"  Could not replace "
                f"local file: {error}"
            )

            try:
                if temporary_path.exists():
                    temporary_path.unlink()
            except OSError:
                pass

            failed += 1
            continue

        manifest[
            local_path.name
        ] = {
            "repo_path": repo_item["path"],
            "repo_sha": repo_item["sha"],
            "sha256": remote_hash
        }

        updated += 1

        print(
            f"  Updated: "
            f"{local_path}"
        )

        if config["auto_cleanup"]:
            try:
                backup_path.unlink()

                print(
                    "  Automatic cleanup "
                    "removed the backup."
                )

            except OSError:
                print(
                    "  Could not automatically "
                    "remove the backup."
                )

        else:
            print(
                f"  Backup:  "
                f"{backup_path}"
            )

    save_manifest(
        manifest
    )

    print()
    print(
        "Update complete."
    )

    print(
        f"Updated:         {updated}"
    )

    print(
        f"Already current: {current}"
    )

    print(
        f"Failed:          {failed}"
    )


def main():
    config = load_config()

    print_header()

    try:
        print(
            "Connecting to GitHub..."
        )

        files, branch = (
            get_repo_files()
        )

    except urllib.error.HTTPError as error:
        print(
            f"\nGitHub returned "
            f"HTTP {error.code}."
        )

        print(
            "Could not retrieve "
            "the repository."
        )

        return 1

    except urllib.error.URLError as error:
        print(
            f"\nCould not connect "
            f"to GitHub: {error.reason}"
        )

        return 1

    except Exception as error:
        print(
            "\nCould not retrieve "
            f"repository files: {error}"
        )

        return 1

    print(
        f"Using branch: {branch}"
    )

    print(
        f"Found {len(files)} file(s)."
    )

    print()

    check_ltm_update(
        files,
        config
    )

    while True:
        print(
            "What would you like to do?"
        )

        print()

        print(
            "1. Download new tools"
        )

        print(
            "2. Update current tools"
        )

        print(
            "3. CleanUP"
        )

        print(
            "4. Settings"
        )

        print(
            "5. Exit"
        )

        print()

        choice = input(
            "Select 1, 2, 3, 4, or 5: "
        ).strip()

        if choice == "1":
            download_new_tools(
                files
            )

            print()

            input(
                "Press Enter to return "
                "to the menu..."
            )

            print()

        elif choice == "2":
            update_current_tools(
                files,
                config
            )

            print()

            input(
                "Press Enter to return "
                "to the menu..."
            )

            print()

        elif choice == "3":
            cleanup_backups(
                ask_confirmation=True
            )

            input(
                "Press Enter to return "
                "to the menu..."
            )

            print()

        elif choice == "4":
            settings_menu(
                config
            )

            print()

        elif choice == "5":
            print()
            print(
                "Goodbye."
            )

            return 0

        else:
            print()
            print(
                "Invalid selection. "
                "Please choose 1, 2, 3, 4, or 5."
            )

            print()


if __name__ == "__main__":
    try:
        sys.exit(
            main()
        )

    except KeyboardInterrupt:
        print(
            "\n\nOperation cancelled."
        )

        sys.exit(130)
        # not tested
