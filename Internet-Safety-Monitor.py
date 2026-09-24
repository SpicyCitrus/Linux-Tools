import curses
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


APP_NAME = "Internet Safety Monitor"
FOOTER = "Made with ❤️ by Cozy"

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_DIR = BASE_DIR / "ISM LOGS"
LOG_FILE = LOG_DIR / "history.log"

DEFAULT_CONFIG = {
    "refresh_seconds": 2,
    "history_enabled": True,
    "max_history_entries": 1000
}


def ensure_files():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)


def load_config():
    ensure_files()

    try:
        config = json.loads(
            CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(config, dict):
            return DEFAULT_CONFIG.copy()

        result = DEFAULT_CONFIG.copy()
        result.update(config)

        return result

    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()


def save_config(config):
    CONFIG_FILE.write_text(
        json.dumps(
            config,
            indent=4
        ),
        encoding="utf-8"
    )


def run_command(command):
    executable = shutil.which(command[0])

    if not executable:
        return None

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    except (OSError, subprocess.SubprocessError):
        return None


def get_interfaces():
    net_dir = Path("/sys/class/net")

    if not net_dir.exists():
        return []

    return sorted(
        path.name
        for path in net_dir.iterdir()
        if path.is_dir()
    )


def get_interface_addresses():
    output = run_command([
        "ip",
        "-brief",
        "address"
    ])

    if not output:
        return []

    interfaces = []

    for line in output.splitlines():
        parts = line.split()

        if len(parts) < 2:
            continue

        interface = parts[0]
        state = parts[1]
        addresses = parts[2:]

        interfaces.append({
            "name": interface,
            "state": state,
            "addresses": addresses
        })

    return interfaces


def get_default_route():
    output = run_command([
        "ip",
        "route",
        "show",
        "default"
    ])

    if not output:
        return None

    match = re.search(
        r"default via ([^\s]+) dev ([^\s]+)",
        output
    )

    if match:
        return {
            "gateway": match.group(1),
            "interface": match.group(2)
        }

    match = re.search(
        r"default dev ([^\s]+)",
        output
    )

    if match:
        return {
            "gateway": None,
            "interface": match.group(1)
        }

    return None


def get_networkmanager_connections():
    output = run_command([
        "nmcli",
        "-t",
        "-f",
        "NAME,TYPE,DEVICE,STATE",
        "connection",
        "show",
        "--active"
    ])

    if not output:
        return []

    connections = []

    for line in output.splitlines():
        parts = line.split(":")

        if len(parts) < 4:
            continue

        name, connection_type, device, state = parts[:4]

        connections.append({
            "name": name,
            "type": connection_type,
            "device": device,
            "state": state
        })

    return connections


def detect_vpn_processes():
    processes = []
    proc_dir = Path("/proc")

    if not proc_dir.exists():
        return processes

    known_processes = {
        "openvpn": ("OpenVPN", "OpenVPN"),
        "wireguard": ("WireGuard", "WireGuard"),
        "wg-quick": ("WireGuard", "WireGuard"),
        "tailscaled": ("Tailscale", "VPN"),
        "tailscale": ("Tailscale", "VPN"),
        "protonvpn": ("Proton VPN", "VPN"),
        "protonvpn-cli": ("Proton VPN", "VPN"),
        "mullvad": ("Mullvad VPN", "VPN"),
        "mullvad-daemon": ("Mullvad VPN", "VPN"),
        "nordvpn": ("NordVPN", "VPN"),
        "nordvpnd": ("NordVPN", "VPN"),
        "expressvpn": ("ExpressVPN", "VPN"),
        "expressvpnd": ("ExpressVPN", "VPN"),
        "surfshark": ("Surfshark", "VPN"),
        "surfsharkd": ("Surfshark", "VPN"),
        "pia-daemon": (
            "Private Internet Access",
            "VPN"
        ),
        "piactl": (
            "Private Internet Access",
            "VPN"
        )
    }

    try:
        process_dirs = proc_dir.iterdir()
    except OSError:
        return processes

    for process_dir in process_dirs:
        if not process_dir.name.isdigit():
            continue

        try:
            process_name = (
                process_dir / "comm"
            ).read_text(
                encoding="utf-8"
            ).strip().lower()

        except (OSError, UnicodeDecodeError):
            continue

        if process_name in known_processes:
            provider, vpn_type = known_processes[
                process_name
            ]

            processes.append({
                "process": process_name,
                "provider": provider,
                "type": vpn_type
            })

    return processes


def detect_vpn():
    interfaces = get_interfaces()
    connections = get_networkmanager_connections()
    processes = detect_vpn_processes()

    detected = False
    vpn_type = None
    provider = None
    interface = None
    evidence = []

    for name in interfaces:
        if name.startswith("wg"):
            detected = True
            vpn_type = "WireGuard"
            interface = name

            evidence.append(
                f"WireGuard interface: {name}"
            )

        elif name.startswith(("tun", "tap")):
            detected = True

            if vpn_type is None:
                vpn_type = "TUN/TAP"

            if interface is None:
                interface = name

            evidence.append(
                f"TUN/TAP interface: {name}"
            )

    provider_names = {
        "proton": "Proton VPN",
        "protonvpn": "Proton VPN",
        "mullvad": "Mullvad VPN",
        "nordvpn": "NordVPN",
        "nord vpn": "NordVPN",
        "expressvpn": "ExpressVPN",
        "express vpn": "ExpressVPN",
        "surfshark": "Surfshark",
        "private internet access": (
            "Private Internet Access"
        ),
        "tailscale": "Tailscale"
    }

    for connection in connections:
        connection_type = connection["type"].lower()
        name = connection["name"]
        lower_name = name.lower()

        if "wireguard" in connection_type:
            detected = True
            vpn_type = "WireGuard"

            if connection["device"]:
                interface = connection["device"]

            evidence.append(
                f"NetworkManager connection: {name}"
            )

        elif connection_type == "vpn":
            detected = True

            if vpn_type is None:
                vpn_type = "VPN"

            if connection["device"]:
                interface = connection["device"]

            evidence.append(
                f"NetworkManager VPN connection: {name}"
            )

        for keyword, detected_provider in (
            provider_names.items()
        ):
            if keyword in lower_name:
                provider = detected_provider
                detected = True
                break

    for process in processes:
        detected = True

        if provider is None:
            provider = process["provider"]

        if vpn_type is None:
            vpn_type = process["type"]

        evidence.append(
            f"VPN process: {process['process']}"
        )

    return {
        "detected": detected,
        "type": vpn_type,
        "provider": provider,
        "interface": interface,
        "evidence": list(
            dict.fromkeys(evidence)
        )
    }


def parse_connections():
    output = run_command([
        "ss",
        "-tunap"
    ])

    if not output:
        return []

    connections = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 5:
            continue

        if parts[0] not in {
            "tcp",
            "udp",
            "tcp6",
            "udp6"
        }:
            continue

        protocol = parts[0]
        state = parts[1]
        local = parts[4]
        remote = (
            parts[5]
            if len(parts) > 5
            else "*"
        )

        process = ""

        if "users:" in line:
            match = re.search(
                r'"([^"]+)"',
                line
            )

            if match:
                process = match.group(1)

        connections.append({
            "protocol": protocol,
            "state": state,
            "local": local,
            "remote": remote,
            "process": process
        })

    return connections


def extract_remote_host(remote):
    if remote in {
        "*",
        "*:*",
        "0.0.0.0:*",
        "[::]:*"
    }:
        return None

    if remote.startswith("["):
        closing = remote.find("]")

        if closing != -1:
            return remote[1:closing]

    if ":" in remote:
        return remote.rsplit(
            ":",
            1
        )[0]

    return remote


def get_remote_port(remote):
    if remote in {
        "*",
        "*:*"
    }:
        return None

    if remote.startswith("["):
        closing = remote.find("]")

        if closing != -1:
            return remote[
                closing + 2:
            ]

    if ":" in remote:
        return remote.rsplit(
            ":",
            1
        )[1]

    return None


def resolve_host(host):
    if not host:
        return None

    try:
        return socket.gethostbyaddr(
            host
        )[0]

    except (
        socket.herror,
        socket.gaierror,
        OSError
    ):
        return None


def connection_summary(connections):
    summary = {
        "total": 0,
        "tcp": 0,
        "udp": 0,
        "established": 0
    }

    for connection in connections:
        summary["total"] += 1

        protocol = connection[
            "protocol"
        ].lower()

        if protocol.startswith("tcp"):
            summary["tcp"] += 1

        elif protocol.startswith("udp"):
            summary["udp"] += 1

        if connection[
            "state"
        ].upper() in {
            "ESTAB",
            "ESTABLISHED"
        }:
            summary["established"] += 1

    return summary


def save_history(vpn, connections, route, config):
    if not config.get(
        "history_enabled",
        True
    ):
        return

    try:
        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = (
            datetime.now()
            .astimezone()
            .isoformat()
        )

        provider = (
            vpn["provider"]
            if vpn["detected"]
            else "None"
        )

        vpn_type = (
            vpn["type"]
            if vpn["detected"]
            else "None"
        )

        interface = (
            route["interface"]
            if route
            else "None"
        )

        line = (
            f"{timestamp} | "
            f"vpn={provider} | "
            f"type={vpn_type} | "
            f"route={interface} | "
            f"connections={len(connections)}\n"
        )

        with LOG_FILE.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(line)

        max_entries = int(
            config.get(
                "max_history_entries",
                1000
            )
        )

        if max_entries < 1:
            max_entries = 1

        try:
            lines = LOG_FILE.read_text(
                encoding="utf-8"
            ).splitlines()

            if len(lines) > max_entries:
                LOG_FILE.write_text(
                    "\n".join(
                        lines[-max_entries:]
                    ) + "\n",
                    encoding="utf-8"
                )

        except OSError:
            pass

    except OSError:
        pass


def clear_history():
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()

        return True

    except OSError:
        return False


def read_history():
    if not LOG_FILE.exists():
        return []

    try:
        contents = LOG_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if not contents:
            return []

        return contents.splitlines()

    except OSError:
        return []


def draw_live_screen(stdscr, config):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(250)

    while True:
        key = stdscr.getch()

        if key in (
            ord("q"),
            ord("Q"),
            27
        ):
            return

        vpn = detect_vpn()
        interfaces = get_interface_addresses()
        route = get_default_route()
        connections = parse_connections()
        summary = connection_summary(
            connections
        )

        stdscr.erase()

        height, width = stdscr.getmaxyx()

        title = f"{APP_NAME} - LIVE"

        stdscr.addstr(
            0,
            0,
            title[:max(1, width - 1)],
            curses.A_BOLD
        )

        stdscr.addstr(
            1,
            0,
            "=" * max(
                1,
                min(
                    len(title),
                    width - 1
                )
            )
        )

        row = 3

        if row < height - 1:
            stdscr.addstr(
                row,
                0,
                "Network",
                curses.A_BOLD
            )

        row += 1

        for interface in interfaces:
            if row >= height - 1:
                break

            addresses = ", ".join(
                interface["addresses"]
            )

            line = (
                f"  {interface['name']:<10} "
                f"{interface['state']:<10} "
                f"{addresses}"
            )

            stdscr.addstr(
                row,
                0,
                line[:max(1, width - 1)]
            )

            row += 1

        row += 1

        if row < height - 1:
            stdscr.addstr(
                row,
                0,
                "Default Route",
                curses.A_BOLD
            )

        row += 1

        if route:
            route_lines = [
                f"  Interface: {route['interface']}"
            ]

            if route["gateway"]:
                route_lines.append(
                    f"  Gateway:   {route['gateway']}"
                )
        else:
            route_lines = [
                "  None detected."
            ]

        for line in route_lines:
            if row >= height - 1:
                break

            stdscr.addstr(
                row,
                0,
                line[:max(1, width - 1)]
            )

            row += 1

        row += 1

        if row < height - 1:
            stdscr.addstr(
                row,
                0,
                "VPN",
                curses.A_BOLD
            )

        row += 1

        if vpn["detected"]:
            vpn_lines = [
                "  Status:    Detected",
                (
                    f"  Type:      "
                    f"{vpn['type'] or 'Unknown'}"
                ),
                (
                    f"  Provider:  "
                    f"{vpn['provider'] or 'Unknown'}"
                )
            ]

            if vpn["interface"]:
                vpn_lines.append(
                    f"  Interface: {vpn['interface']}"
                )
        else:
            vpn_lines = [
                "  Status:    Not detected",
                "  Provider:  None identified"
            ]

        for line in vpn_lines:
            if row >= height - 1:
                break

            stdscr.addstr(
                row,
                0,
                line[:max(1, width - 1)]
            )

            row += 1

        row += 1

        if row < height - 1:
            stdscr.addstr(
                row,
                0,
                "Connections",
                curses.A_BOLD
            )

        row += 1

        summary_text = (
            f"  Total: {summary['total']}  "
            f"TCP: {summary['tcp']}  "
            f"UDP: {summary['udp']}  "
            f"Established: {summary['established']}"
        )

        if row < height - 1:
            stdscr.addstr(
                row,
                0,
                summary_text[:max(1, width - 1)]
            )

            row += 2

        for connection in connections:
            if row >= height - 3:
                break

            remote = extract_remote_host(
                connection["remote"]
            )

            if not remote:
                continue

            port = get_remote_port(
                connection["remote"]
            )

            hostname = resolve_host(
                remote
            )

            host = hostname or remote
            process = (
                connection["process"]
                or "Unknown"
            )

            line = (
                f"{connection['protocol'].upper():<5} "
                f"{connection['state']:<12} "
                f"{host:<32} "
                f"{port or '-':<6} "
                f"{process}"
            )

            stdscr.addstr(
                row,
                0,
                line[:max(1, width - 1)]
            )

            row += 1

        footer = (
            "Refreshing every "
            f"{config.get('refresh_seconds', 2)} "
            "seconds | Q: Back"
        )

        if height > 1:
            stdscr.addstr(
                height - 1,
                0,
                footer[:max(1, width - 1)]
            )

        stdscr.refresh()

        save_history(
            vpn,
            connections,
            route,
            config
        )

        time.sleep(
            float(
                config.get(
                    "refresh_seconds",
                    2
                )
            )
        )


def show_history_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(False)

    while True:
        stdscr.erase()

        height, width = stdscr.getmaxyx()

        title = f"{APP_NAME} - HISTORY"

        stdscr.addstr(
            0,
            0,
            title[:max(1, width - 1)],
            curses.A_BOLD
        )

        stdscr.addstr(
            1,
            0,
            "=" * max(
                1,
                min(
                    len(title),
                    width - 1
                )
            )
        )

        history = read_history()

        if not history:
            stdscr.addstr(
                3,
                0,
                "No history available."
            )

        else:
            start = max(
                0,
                len(history) - (
                    height - 6
                )
            )

            row = 3

            for line in history[start:]:
                if row >= height - 3:
                    break

                stdscr.addstr(
                    row,
                    0,
                    line[:max(1, width - 1)]
                )

                row += 1

        if height > 1:
            stdscr.addstr(
                height - 1,
                0,
                "Q: Back"[:max(1, width - 1)]
            )

        stdscr.refresh()

        key = stdscr.getch()

        if key in (
            ord("q"),
            ord("Q"),
            27
        ):
            return


def run_live(config):
    curses.wrapper(
        draw_live_screen,
        config
    )


def run_history():
    curses.wrapper(
        show_history_screen
    )


def show_menu(config):
    while True:
        print(
            "\033[2J\033[H",
            end=""
        )

        print(APP_NAME)
        print("=" * len(APP_NAME))
        print()
        print("1. Live Monitor")
        print("2. View History")
        print("3. Clear History")
        print("4. Exit")
        print()
        print(
            f"Refresh rate: "
            f"{config.get('refresh_seconds', 2)} seconds"
        )
        print(
            f"History: "
            f"{'Enabled' if config.get('history_enabled', True) else 'Disabled'}"
        )
        print()
        print(FOOTER)
        print()

        try:
            choice = input(
                "Select an option: "
            ).strip()

        except KeyboardInterrupt:
            print()
            return

        if choice == "1":
            run_live(config)

        elif choice == "2":
            run_history()

        elif choice == "3":
            print()

            if clear_history():
                print(
                    "History cleared successfully."
                )
            else:
                print(
                    "Could not clear history."
                )

            input(
                "\nPress Enter to return..."
            )

        elif choice == "4":
            print()
            print("Goodbye!")
            return

        else:
            print()
            print(
                "Invalid option."
            )

            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(
        prog="internet-safety-monitor",
        description=(
            "Internet Safety Monitor - "
            "a Linux CLI network safety monitor."
        ),
        epilog=FOOTER
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Internet Safety Monitor 1.0"
    )

    args = parser.parse_args()

    try:
        ensure_files()
        config = load_config()
        show_menu(config)

    except KeyboardInterrupt:
        print(
            "\nCancelled."
        )
        sys.exit(130)

    except Exception as error:
        print(
            f"Error: {error}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
# not tested
