from pathlib import Path
import re
import shutil
import subprocess
import random
import json


SUPPORTED_OS = {
    "Alpine", "Amazon Linux", "Anarchy", "Antergos", "AntiX", "AOSC",
    "Apricity", "Arch", "ArchBox", "ArchLabs", "ArchMerge", "Arch XFerience",
    "Artix", "AryaLinux", "Blag", "Blankon", "BunsenLabs", "Calculate",
    "CentOS", "Chakra", "ChaletOS", "Chapeau", "ChromeOS", "CloverOS",
    "Container Linux by CoreOS", "Crux", "Debian", "Deepin", "DesaOS",
    "Devuan", "DracOS", "Elementary OS", "EndeavourOS", "Endless OS",
    "Exherbo", "Fedora", "Frugalware", "Funtoo", "GalliumOS", "Gentoo",
    "Gnewsense", "GoboLinux", "GrombyangOS", "GuixSD", "Hyperbola",
    "KDE Neon", "Kali", "KaOS", "Kogaion", "Korora", "Kubuntu", "KS Linux",
    "LEDE", "LMDE", "Linux Mint", "Lubuntu", "Lunar Linux", "Mageia",
    "MagpieOS", "Manjaro", "Maui", "MX Linux", "Netrunner", "Nitrux",
    "NixOS", "Nurunner", "NuTyX", "OBRevenge", "openSUSE", "OpenIndiana",
    "OpenMandriva", "OpenWrt", "Oracle", "Parabola", "Parrot Security",
    "Pardus", "Parsix", "PCLinuxOS", "Peppermint", "Pop!_OS", "Porteus",
    "PostMarketOS", "Puppy", "Qubes OS", "Raspbian", "Red Hat",
    "Redstar OS", "Rosa", "Sabotage", "Sabayon", "SailfishOS", "SalentOS",
    "Scientific", "Siduction", "Slackware", "SliTaz", "Solus", "Source Mage",
    "Sparky", "SteamOS", "SwagArch", "Tails", "Travis", "Trisquel", "Ubuntu",
    "Ubuntu-GNOME", "Xubuntu", "Studio", "Budgie", "Void", "Zorin",
    "Bitrig", "DragonFly BSD", "FreeBSD", "NetBSD", "OpenBSD",
    "Solaris", "IRIX", "MINIX", "Haiku", "GNU Hurd", "FreeMiNT",
    "Android", "iPadOS", "CYGWIN", "MINGW", "MSYS2",
    "Windows 10 Linux Subsystem", "MacOS", "OS X", "AIX", "DosFetch",
    "MySysInf"
}


FASTFETCH_LOGO_NAMES = {
    "Alpine": "alpine",
    "Amazon Linux": "amazon",
    "Anarchy": "anarchy",
    "Antergos": "antergos",
    "AntiX": "antix",
    "AOSC": "aosc",
    "Apricity": "apricity",
    "Arch": "arch",
    "ArchBox": "archbox",
    "ArchLabs": "archlabs",
    "ArchMerge": "archmerge",
    "Arch XFerience": "arch_xferience",
    "Artix": "artix",
    "AryaLinux": "aryalinux",
    "Blag": "blag",
    "Blankon": "blankon",
    "BunsenLabs": "bunsenlabs",
    "Calculate": "calculate",
    "CentOS": "centos",
    "Chakra": "chakra",
    "ChaletOS": "chaletos",
    "Chapeau": "chapeau",
    "ChromeOS": "chrome",
    "CloverOS": "clover",
    "Container Linux by CoreOS": "coreos",
    "Crux": "crux",
    "Debian": "debian",
    "Deepin": "deepin",
    "DesaOS": "desaos",
    "Devuan": "devuan",
    "DracOS": "dracos",
    "Elementary OS": "elementary",
    "EndeavourOS": "endeavouros",
    "Endless OS": "endless",
    "Exherbo": "exherbo",
    "Fedora": "fedora",
    "Frugalware": "frugalware",
    "Funtoo": "funtoo",
    "GalliumOS": "galliumos",
    "Gentoo": "gentoo",
    "Gnewsense": "gnewsense",
    "GoboLinux": "gobolinux",
    "GrombyangOS": "grombyang",
    "GuixSD": "guix",
    "Hyperbola": "hyperbola",
    "KDE Neon": "kde",
    "Kali": "kali",
    "KaOS": "kaos",
    "Kogaion": "kogaion",
    "Korora": "korora",
    "Kubuntu": "kubuntu",
    "KS Linux": "kslinux",
    "LEDE": "lede",
    "LMDE": "lmde",
    "Linux Mint": "mint",
    "Lubuntu": "lubuntu",
    "Lunar Linux": "lunar",
    "Mageia": "mageia",
    "MagpieOS": "magpie",
    "Manjaro": "manjaro",
    "Maui": "maui",
    "MX Linux": "mx",
    "Netrunner": "netrunner",
    "Nitrux": "nitrux",
    "NixOS": "nixos",
    "Nurunner": "nurunner",
    "NuTyX": "nutyx",
    "OBRevenge": "obrevenge",
    "openSUSE": "opensuse",
    "OpenIndiana": "openindiana",
    "OpenMandriva": "openmandriva",
    "OpenWrt": "openwrt",
    "Oracle": "oracle",
    "Parabola": "parabola",
    "Parrot Security": "parrot",
    "Pardus": "pardus",
    "Parsix": "parsix",
    "PCLinuxOS": "pclinuxos",
    "Peppermint": "peppermint",
    "Pop!_OS": "popos",
    "Porteus": "porteus",
    "PostMarketOS": "postmarketos",
    "Puppy": "puppy",
    "Qubes OS": "qubes",
    "Raspbian": "raspbian",
    "Red Hat": "redhat",
    "Redstar OS": "redstar",
    "Rosa": "rosa",
    "Sabotage": "sabotage",
    "Sabayon": "sabayon",
    "SailfishOS": "sailfish",
    "SalentOS": "salentos",
    "Scientific": "scientific",
    "Siduction": "siduction",
    "Slackware": "slackware",
    "SliTaz": "slitaz",
    "Solus": "solus",
    "Source Mage": "sourcemage",
    "Sparky": "sparky",
    "SteamOS": "steamos",
    "SwagArch": "swagarch",
    "Tails": "tails",
    "Travis": "travis",
    "Trisquel": "trisquel",
    "Ubuntu": "ubuntu",
    "Ubuntu-GNOME": "ubuntu_gnome",
    "Xubuntu": "xubuntu",
    "Studio": "ubuntu_studio",
    "Budgie": "budgie",
    "Void": "void",
    "Zorin": "zorin",
    "Bitrig": "bitrig",
    "DragonFly BSD": "dragonfly",
    "FreeBSD": "freebsd",
    "NetBSD": "netbsd",
    "OpenBSD": "openbsd",
    "Solaris": "solaris",
    "IRIX": "irix",
    "MINIX": "minix",
    "Haiku": "haiku",
    "GNU Hurd": "gnu_hurd",
    "FreeMiNT": "freemint",
    "Android": "android",
    "iPadOS": "ipados",
    "CYGWIN": "cygwin",
    "MINGW": "mingw",
    "MSYS2": "msys2",
    "Windows 10 Linux Subsystem": "wsl",
    "MacOS": "macos",
    "OS X": "macos",
    "AIX": "aix",
    "DosFetch": "dosfetch",
    "MySysInf": "mysysinfo"
}


def find_neofetch_config():
    return Path.home() / ".config" / "neofetch" / "config.conf"


def find_fastfetch_config():
    return Path.home() / ".config" / "fastfetch" / "config.jsonc"


def check_program(program):
    return shutil.which(program) is not None


def choose_fetch_program():
    while True:
        print("Which fetch program are you using?")
        print()
        print("1. Neofetch")
        print("2. Fastfetch")
        print()

        choice = input("Select 1 or 2: ").strip()

        if choice == "1":
            if not check_program("neofetch"):
                print("\nError: neofetch was not found.")
                print("Make sure neofetch is installed and available in your PATH.\n")
                continue

            return "neofetch"

        if choice == "2":
            if not check_program("fastfetch"):
                print("\nError: fastfetch was not found.")
                print("Make sure fastfetch is installed and available in your PATH.\n")
                continue

            return "fastfetch"

        print("\nPlease select 1 or 2.\n")


def preview_neofetch(os_name):
    try:
        subprocess.run(
            ["neofetch", "--ascii_distro", os_name],
            check=False
        )
        return True
    except FileNotFoundError:
        print("\nError: neofetch was not found.")
        print("Make sure neofetch is installed and available in your PATH.")
        return False


def preview_fastfetch(os_name):
    logo_name = FASTFETCH_LOGO_NAMES.get(os_name)

    if not logo_name:
        print(f'\nError: No Fastfetch logo mapping exists for "{os_name}".')
        return False

    try:
        subprocess.run(
            [
                "fastfetch",
                "--logo-type",
                "builtin",
                "--logo",
                logo_name
            ],
            check=False
        )
        return True
    except FileNotFoundError:
        print("\nError: fastfetch was not found.")
        print("Make sure fastfetch is installed and available in your PATH.")
        return False


def save_neofetch_logo(os_name):
    config_file = find_neofetch_config()

    if not config_file.exists():
        print("\nError: Neofetch config was not found:")
        print(f"  {config_file}")
        return False

    backup_file = config_file.with_suffix(".conf.backup")

    try:
        shutil.copy2(config_file, backup_file)
    except Exception as e:
        print(f"\nError creating backup: {e}")
        return False

    try:
        contents = config_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"\nError reading config: {e}")
        return False

    pattern = r'^(#?\s*ascii_distro\s*=\s*)["\'].*?["\'](\s*)$'
    replacement = rf'\1"{os_name}"\2'

    new_contents, changes = re.subn(
        pattern,
        replacement,
        contents,
        count=1,
        flags=re.MULTILINE
    )

    if changes == 0:
        print("\nError: Could not find the ascii_distro setting.")
        print("Make sure your config contains:")
        print('ascii_distro="auto"')
        return False

    try:
        config_file.write_text(new_contents, encoding="utf-8")
    except Exception as e:
        print(f"\nError writing config: {e}")

        try:
            shutil.copy2(backup_file, config_file)
        except Exception:
            pass

        return False

    print(f'\nNeofetch logo changed to "{os_name}".')
    print("Backup created at:")
    print(f"  {backup_file}")

    return True


def save_fastfetch_logo(os_name):
    config_file = find_fastfetch_config()

    if not config_file.exists():
        print("\nError: Fastfetch config was not found:")
        print(f"  {config_file}")
        print()
        print("Create one with:")
        print("  fastfetch --gen-config")
        return False

    logo_name = FASTFETCH_LOGO_NAMES.get(os_name)

    if not logo_name:
        print(f'\nError: No Fastfetch logo mapping exists for "{os_name}".')
        return False

    backup_file = config_file.with_suffix(".jsonc.backup")

    try:
        shutil.copy2(config_file, backup_file)
    except Exception as e:
        print(f"\nError creating backup: {e}")
        return False

    try:
        contents = config_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"\nError reading config: {e}")
        return False

    logo_pattern = r'"logo"\s*:\s*\{'

    logo_match = re.search(logo_pattern, contents)

    if logo_match:
        start = logo_match.start()
        brace_start = contents.find("{", logo_match.start())

        depth = 0
        in_string = False
        escaped = False
        end = None

        for index in range(brace_start, len(contents)):
            character = contents[index]

            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False

                continue

            if character == '"':
                in_string = True
                continue

            if character == "{":
                depth += 1

            elif character == "}":
                depth -= 1

                if depth == 0:
                    end = index + 1
                    break

        if end is None:
            print("\nError: Could not parse the Fastfetch logo configuration.")
            return False

        old_logo = contents[start:end]

        new_logo = (
            '"logo": {\n'
            f'        "type": "builtin",\n'
            f'        "source": "{logo_name}"\n'
            '    }'
        )

        new_contents = contents[:start] + new_logo + contents[end:]

    else:
        stripped = contents.lstrip()

        if not stripped.startswith("{"):
            print("\nError: Fastfetch config is not a valid JSONC object.")
            return False

        opening_index = contents.find("{")

        new_logo = (
            '"logo": {\n'
            f'        "type": "builtin",\n'
            f'        "source": "{logo_name}"\n'
            '    },\n'
        )

        new_contents = (
            contents[:opening_index + 1]
            + "\n    "
            + new_logo
            + contents[opening_index + 1:]
        )

    try:
        config_file.write_text(new_contents, encoding="utf-8")
    except Exception as e:
        print(f"\nError writing config: {e}")

        try:
            shutil.copy2(backup_file, config_file)
        except Exception:
            pass

        return False

    print(f'\nFastfetch logo changed to "{os_name}".')
    print(f'Fastfetch builtin logo: "{logo_name}"')
    print("Backup created at:")
    print(f"  {backup_file}")

    return True


def preview_logo(fetch_program, os_name):
    if fetch_program == "neofetch":
        return preview_neofetch(os_name)

    return preview_fastfetch(os_name)


def save_logo(fetch_program, os_name):
    if fetch_program == "neofetch":
        return save_neofetch_logo(os_name)

    return save_fastfetch_logo(os_name)


def show_os_list(fetch_program):
    os_list = list(SUPPORTED_OS)

    if fetch_program == "fastfetch":
        os_list = [
            os_name
            for os_name in os_list
            if os_name in FASTFETCH_LOGO_NAMES
        ]

    random.shuffle(os_list)

    print("\nSupported operating systems:\n")

    columns = 3
    rows = (len(os_list) + columns - 1) // columns

    for row in range(rows):
        line = ""

        for column in range(columns):
            index = row + column * rows

            if index < len(os_list):
                line += f"{os_list[index]:<32}"

        print(line.rstrip())

    print()


def main():
    print("Made with ❤️ by Cozy")
    print()
    print("OS Logo Switcher")
    print("----------------")

    fetch_program = choose_fetch_program()

    print()

    if fetch_program == "neofetch":
        print("Using Neofetch.")
    else:
        print("Using Fastfetch.")

    print()

    show_os_list(fetch_program)

    print("Enter the name of the operating system you want to use.")
    print()

    while True:
        prompt = (
            "Switch neofetch logo to? "
            if fetch_program == "neofetch"
            else "Switch fastfetch logo to? "
        )

        os_name = input(prompt).strip()

        if not os_name:
            print("Please enter an operating system.\n")
            continue

        matched_os = next(
            (
                name for name in SUPPORTED_OS
                if name.lower() == os_name.lower()
            ),
            None
        )

        if matched_os is None:
            print(f'\n"{os_name}" is not in the supported OS list.')
            print("Please choose one of the operating systems listed above.\n")
            continue

        if fetch_program == "fastfetch" and matched_os not in FASTFETCH_LOGO_NAMES:
            print(f'\nFastfetch does not have a mapped logo for "{matched_os}".')
            print("Please choose one of the Fastfetch-supported operating systems listed above.\n")
            continue

        print(f'\nPreviewing "{matched_os}"...\n')

        if not preview_logo(fetch_program, matched_os):
            return

        print()

        confirmation = input(
            f'Are you sure you want to switch the logo to "{matched_os}"? [yes/no] '
        ).strip().lower()

        if confirmation == "yes":
            if save_logo(fetch_program, matched_os):
                break

        elif confirmation == "no":
            print("\nOkay, choose another logo.\n")
            continue

        else:
            print('\nPlease type "yes" or "no".\n')


if __name__ == "__main__":
    main()
    # not really tested
