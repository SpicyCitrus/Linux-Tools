import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path


IP_API_URL = "https://ipinfo.io/json"
SPEED_TEST_URL = "https://speed.cloudflare.com/__down?bytes=10000000"
UPLOAD_TEST_URL = "https://speed.cloudflare.com/__up"

MONITOR_INTERVAL = 5
SPEED_TEST_BYTES = 10_000_000
UPLOAD_TEST_BYTES = 2_000_000

APP_NAME = "Internet Safety Monitor"


def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def get_terminal_width():
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def print_header():
    width = get_terminal_width()

    print("=" * width)
    print(APP_NAME.center(width))
    print("=" * width)
    print("Made with ❤️ by Cozy".center(width))
    print("=" * width)
    print()


def get_json(url, timeout=10):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Internet-Safety-Monitor"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:
        return response.read().decode("utf-8")


def get_public_ip_info():
    try:
        data = get_json(
            IP_API_URL,
            timeout=10
        )

        import json

        data = json.loads(data)

        return {
            "ip": data.get("ip", "Unknown"),
            "hostname": data.get(
                "hostname",
                "Unknown"
            ),
            "city": data.get(
                "city",
                "Unknown"
            ),
            "region": data.get(
                "region",
                "Unknown"
            ),
            "country": data.get(
                "country",
                "Unknown"
            ),
            "org": data.get(
                "org",
                "Unknown"
            ),
            "postal": data.get(
                "postal",
                "Unknown"
            ),
            "timezone": data.get(
                "timezone",
                "Unknown"
            )
        }

    except Exception as error:
        return {
            "ip": "Unavailable",
            "hostname": "Unknown",
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
            "org": "Unknown",
            "postal": "Unknown",
            "timezone": "Unknown",
            "error": str(error)
        }


def detect_vpn(info):
    if not info:
        return {
            "detected": False,
            "confidence": "Unknown",
            "reason": "No IP information available"
        }

    organization = str(
        info.get("org", "")
    ).lower()

    hostname = str(
        info.get("hostname", "")
    ).lower()

    combined = (
        organization
        + " "
        + hostname
    )

    vpn_keywords = [
        "vpn",
        "proxy",
        "hosting",
        "datacenter",
        "data center",
        "digitalocean",
        "amazon",
        "aws",
        "google cloud",
        "microsoft azure",
        "azure",
        "ovh",
        "linode",
        "vultr",
        "hetzner",
        "choopa",
        "m247",
        "nordvpn",
        "expressvpn",
        "surfshark",
        "private internet access",
        "pia"
    ]

    matches = [
        keyword
        for keyword in vpn_keywords
        if keyword in combined
    ]

    if matches:
        return {
            "detected": True,
            "confidence": "Possible",
            "reason": (
                "IP network information contains: "
                + ", ".join(matches)
            )
        }

    return {
        "detected": False,
        "confidence": "Not detected",
        "reason": (
            "No obvious VPN, proxy, or hosting "
            "indicators were found."
        )
    }


def test_latency():
    targets = [
        "1.1.1.1",
        "8.8.8.8"
    ]

    results = []

    for target in targets:
        try:
            start = time.perf_counter()

            connection = socket.create_connection(
                (target, 443),
                timeout=3
            )

            connection.close()

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            results.append(elapsed)

        except Exception:
            pass

    if not results:
        return None

    return min(results)


def test_download_speed():
    request = urllib.request.Request(
        SPEED_TEST_URL,
        headers={
            "User-Agent": "Internet-Safety-Monitor"
        }
    )

    start = time.perf_counter()
    total_bytes = 0

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            while total_bytes < SPEED_TEST_BYTES:
                chunk = response.read(
                    min(
                        1024 * 1024,
                        SPEED_TEST_BYTES - total_bytes
                    )
                )

                if not chunk:
                    break

                total_bytes += len(chunk)

    except Exception:
        return None

    elapsed = time.perf_counter() - start

    if elapsed <= 0 or total_bytes <= 0:
        return None

    bits = total_bytes * 8
    megabits = bits / 1_000_000

    return megabits / elapsed


def test_upload_speed():
    data = os.urandom(
        UPLOAD_TEST_BYTES
    )

    request = urllib.request.Request(
        UPLOAD_TEST_URL,
        data=data,
        method="POST",
        headers={
            "User-Agent": "Internet-Safety-Monitor",
            "Content-Type": "application/octet-stream"
        }
    )

    start = time.perf_counter()

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:
            response.read(1024)

    except Exception:
        return None

    elapsed = time.perf_counter() - start

    if elapsed <= 0:
        return None

    bits = len(data) * 8
    megabits = bits / 1_000_000

    return megabits / elapsed


def run_speed_test():
    print("Running speed test...")
    print()

    print("Testing latency...")

    latency = test_latency()

    if latency is None:
        print("Latency: unavailable")
    else:
        print(
            f"Latency: {latency:.1f} ms"
        )

    print()

    print("Testing download speed...")

    download = test_download_speed()

    if download is None:
        print("Download: unavailable")
    else:
        print(
            f"Download: {download:.2f} Mbps"
        )

    print()

    print("Testing upload speed...")

    upload = test_upload_speed()

    if upload is None:
        print("Upload: unavailable")
    else:
        print(
            f"Upload: {upload:.2f} Mbps"
        )

    print()

    return {
        "latency": latency,
        "download": download,
        "upload": upload
    }


def run_command(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return ""

        return result.stdout

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        OSError
    ):
        return ""


def get_process_name(pid):
    proc_name = Path(
        f"/proc/{pid}/comm"
    )

    try:
        return proc_name.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        pass

    output = run_command([
        "ps",
        "-p",
        str(pid),
        "-o",
        "comm="
    ])

    return output.strip()


def get_process_connections():
    connections = []

    output = run_command([
        "ss",
        "-tunp"
    ])

    if not output:
        return connections

    lines = output.splitlines()

    for line in lines:
        if line.startswith("Netid"):
            continue

        parts = line.split()

        if len(parts) < 6:
            continue

        state = parts[1]
        local_address = parts[4]
        remote_address = parts[5]

        if remote_address in {
            "*:*",
            "0.0.0.0:*",
            "[::]:*"
        }:
            continue

        process_match = re.search(
            r"pid=(\d+)",
            line
        )

        pid = None

        if process_match:
            pid = process_match.group(1)

        process_name = "Unknown"

        if pid:
            process_name = (
                get_process_name(pid)
                or "Unknown"
            )

        connections.append({
            "state": state,
            "local": local_address,
            "remote": remote_address,
            "pid": pid,
            "process": process_name
        })

    return connections


def extract_remote_host(remote):
    remote = remote.strip()

    if remote.startswith("["):
        end = remote.find("]")

        if end != -1:
            return remote[
                1:end
            ]

    if ":" in remote:
        host, port = remote.rsplit(
            ":",
            1
        )

        if host:
            return host

    return remote


def resolve_host(host):
    if not host:
        return None

    if host in {
        "*",
        "0.0.0.0",
        "::"
    }:
        return None

    try:
        socket.inet_pton(
            socket.AF_INET,
            host
        )

        return host

    except OSError:
        pass

    try:
        socket.inet_pton(
            socket.AF_INET6,
            host
        )

        return host

    except OSError:
        pass

    try:
        result = socket.gethostbyaddr(
            host
        )

        return result[0]

    except Exception:
        return None


def get_network_usage():
    usage = defaultdict(
        lambda: {
            "connections": 0,
            "remote_hosts": set()
        }
    )

    connections = get_process_connections()

    for connection in connections:
        process = connection[
            "process"
        ]

        remote = extract_remote_host(
            connection["remote"]
        )

        usage[process]["connections"] += 1

        if remote:
            resolved = resolve_host(
                remote
            )

            usage[process][
                "remote_hosts"
            ].add(
                resolved or remote
            )

    return usage


def get_interface_bytes():
    rx_total = 0
    tx_total = 0

    net_path = Path(
        "/proc/net/dev"
    )

    if not net_path.exists():
        return 0, 0

    try:
        lines = net_path.read_text(
            encoding="utf-8"
        ).splitlines()

    except OSError:
        return 0, 0

    for line in lines:
        if ":" not in line:
            continue

        interface, values = line.split(
            ":",
            1
        )

        interface = interface.strip()

        if interface == "lo":
            continue

        parts = values.split()

        if len(parts) < 9:
            continue

        try:
            rx_total += int(parts[0])
            tx_total += int(parts[8])

        except ValueError:
            continue

    return rx_total, tx_total


def format_bytes(value):
    if value < 1024:
        return f"{value} B"

    if value < 1024 ** 2:
        return f"{value / 1024:.1f} KB"

    if value < 1024 ** 3:
        return f"{value / (1024 ** 2):.1f} MB"

    if value < 1024 ** 4:
        return f"{value / (1024 ** 3):.2f} GB"

    return f"{value / (1024 ** 4):.2f} TB"


def print_alert(message):
    print()
    print("!" * 60)
    print(f"ALERT: {message}")
    print("!" * 60)
    print()


def print_ip_information(info):
    print("PUBLIC IP")
    print("-" * 60)

    print(
        f"IP Address : "
        f"{info.get('ip', 'Unknown')}"
    )

    print(
        f"Hostname   : "
        f"{info.get('hostname', 'Unknown')}"
    )

    print(
        f"Location   : "
        f"{info.get('city', 'Unknown')}, "
        f"{info.get('region', 'Unknown')}, "
        f"{info.get('country', 'Unknown')}"
    )

    print(
        f"ISP / Org  : "
        f"{info.get('org', 'Unknown')}"
    )

    print()


def print_vpn_information(info):
    vpn = detect_vpn(info)

    print("VPN STATUS")
    print("-" * 60)

    if vpn["detected"]:
        print(
            "Status     : POSSIBLE VPN / PROXY"
        )
    else:
        print(
            "Status     : NOT DETECTED"
        )

    print(
        f"Confidence : "
        f"{vpn['confidence']}"
    )

    print(
        f"Details    : "
        f"{vpn['reason']}"
    )

    print()


def print_connections():
    connections = get_process_connections()

    print(
        "ACTIVE INTERNET CONNECTIONS"
    )
    print("-" * 60)

    if not connections:
        print(
            "No active connections found."
        )

        print(
            "Try running the monitor with sudo "
            "for more process information."
        )

        print()
        return

    grouped = defaultdict(list)

    for connection in connections:
        grouped[
            connection["process"]
        ].append(
            connection
        )

    for process, process_connections in sorted(
        grouped.items(),
        key=lambda item: (
            -len(item[1]),
            item[0].lower()
        )
    ):
        print(
            f"{process}: "
            f"{len(process_connections)} "
            f"connection(s)"
        )

        displayed = set()

        for connection in process_connections:
            remote = extract_remote_host(
                connection["remote"]
            )

            resolved = resolve_host(
                remote
            )

            display_host = (
                resolved
                if resolved
                else remote
            )

            key = (
                display_host,
                connection["state"]
            )

            if key in displayed:
                continue

            displayed.add(key)

            print(
                f"  "
                f"{connection['state']:<12} "
                f"{display_host}"
            )

        print()


def print_usage():
    usage = get_network_usage()

    print("NETWORK ACTIVITY")
    print("-" * 60)

    if not usage:
        print(
            "No process-level network activity "
            "could be determined."
        )

        print()
        return

    sorted_usage = sorted(
        usage.items(),
        key=lambda item: (
            -item[1]["connections"],
            item[0].lower()
        )
    )

    for process, data in sorted_usage[:10]:
        print(
            f"{process:<25} "
            f"{data['connections']} connection(s)"
        )

        hosts = sorted(
            data["remote_hosts"]
        )

        if hosts:
            for host in hosts[:5]:
                print(
                    f"  -> {host}"
                )

        if len(hosts) > 5:
            print(
                f"  -> +{len(hosts) - 5} more"
            )

        print()


def print_traffic(
    rx,
    tx,
    previous_rx,
    previous_tx
):
    print("TRAFFIC")
    print("-" * 60)

    print(
        f"Total download : "
        f"{format_bytes(rx)}"
    )

    print(
        f"Total upload   : "
        f"{format_bytes(tx)}"
    )

    if previous_rx is not None:
        download_delta = max(
            0,
            rx - previous_rx
        )

        upload_delta = max(
            0,
            tx - previous_tx
        )

        print(
            f"Since refresh  : "
            f"{format_bytes(download_delta)} down / "
            f"{format_bytes(upload_delta)} up"
        )

    print()


def monitor():
    info = get_public_ip_info()

    current_ip = info.get(
        "ip",
        "Unavailable"
    )

    previous_ip = current_ip

    previous_rx, previous_tx = (
        get_interface_bytes()
    )

    last_speed_test = None
    speed_results = None

    while True:
        try:
            clear_screen()
            print_header()

            current_info = (
                get_public_ip_info()
            )

            current_ip = current_info.get(
                "ip",
                "Unavailable"
            )

            if (
                previous_ip != "Unavailable"
                and current_ip != "Unavailable"
                and current_ip != previous_ip
            ):
                print_alert(
                    f"Public IP changed!\n"
                    f"Old IP: {previous_ip}\n"
                    f"New IP: {current_ip}"
                )

            previous_ip = current_ip

            print_ip_information(
                current_info
            )

            print_vpn_information(
                current_info
            )

            rx, tx = get_interface_bytes()

            print_traffic(
                rx,
                tx,
                previous_rx,
                previous_tx
            )

            previous_rx = rx
            previous_tx = tx

            if (
                last_speed_test is None
                or time.time() - last_speed_test >= 300
            ):
                print("SPEED TEST")
                print("-" * 60)

                speed_results = (
                    run_speed_test()
                )

                last_speed_test = time.time()

            else:
                print("SPEED TEST")
                print("-" * 60)

                if speed_results:
                    latency = (
                        speed_results["latency"]
                    )

                    download = (
                        speed_results["download"]
                    )

                    upload = (
                        speed_results["upload"]
                    )

                    print(
                        "Latency: "
                        + (
                            f"{latency:.1f} ms"
                            if latency is not None
                            else "unavailable"
                        )
                    )

                    print(
                        "Download: "
                        + (
                            f"{download:.2f} Mbps"
                            if download is not None
                            else "unavailable"
                        )
                    )

                    print(
                        "Upload: "
                        + (
                            f"{upload:.2f} Mbps"
                            if upload is not None
                            else "unavailable"
                        )
                    )

                    print(
                        "Next speed test in "
                        "approximately 5 minutes."
                    )

                print()

            print_connections()
            print_usage()

            print(
                "Press Ctrl+C to stop monitoring."
            )

            time.sleep(
                MONITOR_INTERVAL
            )

        except KeyboardInterrupt:
            print()
            print(
                "Internet Safety Monitor stopped."
            )
            return

        except Exception as error:
            print()
            print(
                f"Monitor error: {error}"
            )

            time.sleep(
                MONITOR_INTERVAL
            )


def show_once():
    clear_screen()
    print_header()

    print(
        "Collecting network information..."
    )

    print()

    info = get_public_ip_info()

    print_ip_information(
        info
    )

    print_vpn_information(
        info
    )

    run_speed_test()

    print_connections()

    print_usage()

    print(
        "Made with ❤️ by Cozy"
    )


def main():
    while True:
        clear_screen()
        print_header()

        print(
            "1. Run safety check"
        )

        print(
            "2. Start live monitor"
        )

        print(
            "3. Exit"
        )

        print()

        choice = input(
            "Select 1, 2, or 3: "
        ).strip()

        if choice == "1":
            show_once()

            print()

            input(
                "Press Enter to return "
                "to the menu..."
            )

        elif choice == "2":
            monitor()

            print()

            input(
                "Press Enter to return "
                "to the menu..."
            )

        elif choice == "3":
            print()
            print(
                "Goodbye."
            )
            return 0

        else:
            print()
            print(
                "Invalid selection."
            )

            time.sleep(1)


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
