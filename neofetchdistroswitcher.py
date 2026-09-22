from pathlib import Path
import re
import shutil
import subprocess
import random

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


def find_config():
    return Path.home() / ".config" / "neofetch" / "config.conf"


def preview_logo(os_name):
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


def save_logo(os_name):
    config_file = find_config()

    if not config_file.exists():
        print("\nError: Neofetch config was not found:")
        print(f"  {config_file}")
        return

    backup_file = config_file.with_suffix(".conf.backup")
    shutil.copy2(config_file, backup_file)

    try:
        contents = config_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"\nError reading config: {e}")
        return

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
        return

    try:
        config_file.write_text(new_contents, encoding="utf-8")
    except Exception as e:
        print(f"\nError writing config: {e}")
        shutil.copy2(backup_file, config_file)
        return

    print(f'\nNeofetch logo changed to "{os_name}".')
    print("Backup created at:")
    print(f"  {backup_file}")


def show_os_list():
    os_list = list(SUPPORTED_OS)
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
    print("Neofetch Logo Switcher")
    print("----------------------")

    show_os_list()

    print("Enter the name of the operating system you want to use.")
    print()

    while True:
        os_name = input("Switch neofetch logo to? ").strip()

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

        print(f'\nPreviewing "{matched_os}"...\n')

        if not preview_logo(matched_os):
            return

        print()

        confirmation = input(
            f'Are you sure you want to switch the logo to "{matched_os}"? [yes/no] '
        ).strip().lower()

        if confirmation == "yes":
            save_logo(matched_os)
            break

        elif confirmation == "no":
            print("\nOkay, choose another logo.\n")
            continue

        else:
            print('\nPlease type "yes" or "no".\n')


if __name__ == "__main__":
    main()
#little editor note. some of the icons just are tux idk why i just grabbed a list off of google and i tested most of the them and it works ALSO this only works correctly if you use neofetch not fastfetch this also works best with neofetch auto running with fish but its not needed
