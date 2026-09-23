import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

CHECK_INTERVAL = 60
HTTP_TIMEOUT = 15
SPEED_TIMEOUT = 30

DOWNLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_BYTES = 5 * 1024 * 1024

IP_API = "https://ipwho.is/"
GOOGLE_CONNECTIVITY_URL = "https://www.google.com/generate_204"

CLOUDFLARE_DOWNLOAD_URL = (
    "https://speed.cloudflare.com/__down?bytes="
    + str(DOWNLOAD_BYTES)
)

CLOUDFLARE_UPLOAD_URL = "https://speed.cloudflare.com/__up"

USE_COLOR = sys.stdout.isatty()

RESET = "\033[0m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""

RED = "\033[91m" if USE_COLOR else ""
GREEN = "\033[92m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
BLUE = "\033[94m" if USE_COLOR else ""
CYAN = "\033[96m" if USE_COLOR else ""
MAGENTA = "\033[95m" if USE_COLOR else ""
WHITE = "\033[97m" if USE_COLOR else ""


def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        print("\033[2J\033[H", end="")


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def utc_string():
    return datetime.now(timezone.utc).isoformat()


def format_duration(seconds):
    if seconds is None:
        return "N/A"

    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"

    return f"{seconds:.2f} s"


def format_speed(mbps):
    if mbps is None:
        return "N/A"

    return f"{mbps:.2f} Mbps"


def make_request(
    url,
    method="GET",
    data=None,
    headers=None,
    timeout=HTTP_TIMEOUT
):
    if headers is None:
        headers = {}

    headers.setdefault(
        "User-Agent",
        "Cozy-Internet-Safety-Monitor/1.0"
    )

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:
        body = response.read()
        return response.status, body, response.headers


def get_ip_information():
    try:
        status, body, _ = make_request(
            IP_API,
            timeout=HTTP_TIMEOUT
        )

        if status != 200:
            return {
                "success": False,
                "error": f"IP service returned HTTP {status}"
            }

        data = json.loads(
            body.decode("utf-8")
        )

        if not data.get("success", False):
            return {
                "success": False,
                "error": data.get(
                    "message",
                    "IP lookup failed"
                )
            }

        security = data.get("security") or {}
        connection = data.get("connection") or {}

        return {
            "success": True,
            "ip": data.get("ip"),
            "type": data.get("type"),
            "continent": data.get("continent"),
            "country": data.get("country"),
            "country_code": data.get("country_code"),
            "region": data.get("region"),
            "city": data.get("city"),
            "isp": connection.get("isp"),
            "org": connection.get("org"),
            "asn": connection.get("asn"),
            "domain": connection.get("domain"),
            "vpn": bool(security.get("vpn", False)),
            "proxy": bool(security.get("proxy", False)),
            "tor": bool(security.get("tor", False)),
            "hosting": bool(security.get("hosting", False)),
        }

    except urllib.error.HTTPError as exc:
        return {
            "success": False,
            "error": f"IP service HTTP error: {exc.code}"
        }

    except urllib.error.URLError as exc:
        return {
            "success": False,
            "error": f"IP service connection error: {exc.reason}"
        }

    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "IP service returned invalid JSON"
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc)
        }


def determine_vpn_status(ip_info):
    if not ip_info.get("success"):
        return "UNKNOWN"

    if ip_info.get("vpn"):
        return "VPN VERIFIED"

    if ip_info.get("proxy"):
        return "PROXY DETECTED"

    if ip_info.get("tor"):
        return "TOR DETECTED"

    if ip_info.get("hosting"):
        return "HOSTING/DATACENTER IP"

    return "VPN NOT DETECTED"


def google_connectivity_test():
    start = time.perf_counter()

    try:
        status, _, _ = make_request(
            GOOGLE_CONNECTIVITY_URL,
            timeout=HTTP_TIMEOUT
        )

        elapsed = time.perf_counter() - start

        return {
            "success": status in (200, 204),
            "status": status,
            "latency": elapsed,
        }

    except Exception as exc:
        elapsed = time.perf_counter() - start

        return {
            "success": False,
            "status": None,
            "latency": elapsed,
            "error": str(exc),
        }


def cloudflare_download_test():
    start = time.perf_counter()
    total_bytes = 0

    try:
        request = urllib.request.Request(
            CLOUDFLARE_DOWNLOAD_URL,
            headers={
                "User-Agent": "Cozy-Internet-Safety-Monitor/1.0",
                "Cache-Control": "no-cache",
            },
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=SPEED_TIMEOUT
        ) as response:

            while True:
                chunk = response.read(64 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

        elapsed = time.perf_counter() - start

        if elapsed <= 0 or total_bytes <= 0:
            return {
                "success": False,
                "error": "No download data received"
            }

        megabits = (total_bytes * 8) / 1_000_000
        mbps = megabits / elapsed

        return {
            "success": True,
            "bytes": total_bytes,
            "seconds": elapsed,
            "mbps": mbps,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc)
        }


def cloudflare_upload_test():
    try:
        upload_data = b"C" * UPLOAD_BYTES

        start = time.perf_counter()

        request = urllib.request.Request(
            CLOUDFLARE_UPLOAD_URL,
            data=upload_data,
            headers={
                "User-Agent": "Cozy-Internet-Safety-Monitor/1.0",
                "Content-Type": "application/octet-stream",
                "Cache-Control": "no-cache",
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=SPEED_TIMEOUT
        ) as response:
            response.read(1024)

        elapsed = time.perf_counter() - start

        if elapsed <= 0:
            return {
                "success": False,
                "error": "Invalid upload timing"
            }

        megabits = (UPLOAD_BYTES * 8) / 1_000_000
        mbps = megabits / elapsed

        return {
            "success": True,
            "bytes": UPLOAD_BYTES,
            "seconds": elapsed,
            "mbps": mbps,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc)
        }


class InternetMonitor:

    def __init__(self):
        self.previous_ip = None
        self.ip_history = []
        self.download_history = []
        self.upload_history = []
        self.google_latency_history = []

        self.last_ip_info = None
        self.last_download = None
        self.last_upload = None
        self.last_google = None

        self.start_time = time.time()

    def check_ip_change(self, current_ip):
        if not current_ip:
            return None

        if self.previous_ip is None:
            self.previous_ip = current_ip
            return None

        if current_ip != self.previous_ip:
            old_ip = self.previous_ip
            self.previous_ip = current_ip

            self.ip_history.append({
                "old": old_ip,
                "new": current_ip,
                "time": utc_string(),
            })

            return {
                "old": old_ip,
                "new": current_ip,
            }

        return None

    def run_check(self):
        print(f"{CYAN}Checking public IP...{RESET}")

        ip_info = get_ip_information()
        self.last_ip_info = ip_info

        if ip_info.get("success"):
            ip_change = self.check_ip_change(
                ip_info.get("ip")
            )
        else:
            ip_change = None

        print(
            f"{CYAN}"
            "Checking Google connectivity..."
            f"{RESET}"
        )

        google = google_connectivity_test()
        self.last_google = google

        print(
            f"{CYAN}"
            "Running Cloudflare download test..."
            f"{RESET}"
        )

        download = cloudflare_download_test()
        self.last_download = download

        print(
            f"{CYAN}"
            "Running Cloudflare upload test..."
            f"{RESET}"
        )

        upload = cloudflare_upload_test()
        self.last_upload = upload

        if download.get("success"):
            self.download_history.append(
                download["mbps"]
            )

        if upload.get("success"):
            self.upload_history.append(
                upload["mbps"]
            )

        if google.get("success"):
            self.google_latency_history.append(
                google["latency"] * 1000
            )

        return ip_change

    def display(self, ip_change=None):
        clear_screen()

        print()

        print(
            f"{MAGENTA}{BOLD}"
            "╔══════════════════════════════════════════════════════╗"
            f"{RESET}"
        )

        print(
            f"{MAGENTA}{BOLD}"
            "║          Made with ❤️ by Cozy                      ║"
            f"{RESET}"
        )

        print(
            f"{MAGENTA}{BOLD}"
            "║          INTERNET SAFETY MONITOR                   ║"
            f"{RESET}"
        )

        print(
            f"{MAGENTA}{BOLD}"
            "╚══════════════════════════════════════════════════════╝"
            f"{RESET}"
        )

        print()
        print(
            f"{WHITE}Last check:{RESET} "
            f"{now_string()}"
        )

        print(
            f"{WHITE}Monitoring interval:{RESET} "
            f"{CHECK_INTERVAL} seconds"
        )

        uptime = time.time() - self.start_time

        print(
            f"{WHITE}Monitor uptime:{RESET} "
            f"{format_duration(uptime)}"
        )

        print()
        print(
            f"{BOLD}{BLUE}"
            "━━ PUBLIC IP & VPN STATUS ━━"
            f"{RESET}"
        )

        ip_info = self.last_ip_info or {}

        if ip_info.get("success"):
            ip = ip_info.get("ip", "Unknown")
            vpn_status = determine_vpn_status(
                ip_info
            )

            if vpn_status == "VPN VERIFIED":
                status_color = GREEN
            elif vpn_status in (
                "PROXY DETECTED",
                "TOR DETECTED",
                "HOSTING/DATACENTER IP",
            ):
                status_color = YELLOW
            else:
                status_color = RED

            print(f"Public IP:       {ip}")

            print(
                f"VPN status:      "
                f"{status_color}{BOLD}"
                f"{vpn_status}"
                f"{RESET}"
            )

            print(
                f"ISP:             "
                f"{ip_info.get('isp') or 'Unknown'}"
            )

            print(
                f"Organization:    "
                f"{ip_info.get('org') or 'Unknown'}"
            )

            asn = ip_info.get("asn")

            if asn:
                print(f"ASN:             {asn}")

            country = ip_info.get("country")
            city = ip_info.get("city")

            if city and country:
                print(
                    f"Location:        "
                    f"{city}, {country}"
                )
            elif country:
                print(
                    f"Location:        "
                    f"{country}"
                )

            print()

            print(
                f"VPN flag:        "
                f"{'YES' if ip_info.get('vpn') else 'NO'}"
            )

            print(
                f"Proxy flag:      "
                f"{'YES' if ip_info.get('proxy') else 'NO'}"
            )

            print(
                f"Tor flag:        "
                f"{'YES' if ip_info.get('tor') else 'NO'}"
            )

            print(
                f"Hosting flag:    "
                f"{'YES' if ip_info.get('hosting') else 'NO'}"
            )

        else:
            print(
                f"{RED}"
                "Could not determine public IP."
                f"{RESET}"
            )

            if ip_info.get("error"):
                print(
                    f"Reason: "
                    f"{ip_info['error']}"
                )

        if ip_change:
            print()

            print(
                f"{RED}{BOLD}"
                "🚨 ALERT: YOUR PUBLIC IP CHANGED"
                f"{RESET}"
            )

            print(
                f"Previous IP: "
                f"{ip_change['old']}"
            )

            print(
                f"Current IP:  "
                f"{ip_change['new']}"
            )

            print("\a", end="")

        print()
        print(
            f"{BOLD}{BLUE}"
            "━━ CONNECTIVITY ━━"
            f"{RESET}"
        )

        google = self.last_google or {}

        if google.get("success"):
            latency_ms = google["latency"] * 1000

            if latency_ms < 50:
                latency_color = GREEN
            elif latency_ms < 120:
                latency_color = YELLOW
            else:
                latency_color = RED

            print(
                f"Google:          "
                f"{GREEN}ONLINE{RESET}"
            )

            print(
                f"Google latency:  "
                f"{latency_color}"
                f"{latency_ms:.0f} ms"
                f"{RESET}"
            )

        else:
            print(
                f"Google:          "
                f"{RED}UNREACHABLE{RESET}"
            )

            if google.get("error"):
                print(
                    f"Reason:          "
                    f"{google['error']}"
                )

        print()
        print(
            f"{BOLD}{BLUE}"
            "━━ INTERNET SPEED ━━"
            f"{RESET}"
        )

        download = self.last_download or {}

        if download.get("success"):
            print(
                f"Download:        "
                f"{GREEN}"
                f"{format_speed(download['mbps'])}"
                f"{RESET}"
            )

        else:
            print(
                f"Download:        "
                f"{RED}FAILED{RESET}"
            )

            if download.get("error"):
                print(
                    f"Reason:          "
                    f"{download['error']}"
                )

        upload = self.last_upload or {}

        if upload.get("success"):
            print(
                f"Upload:          "
                f"{GREEN}"
                f"{format_speed(upload['mbps'])}"
                f"{RESET}"
            )

        else:
            print(
                f"Upload:          "
                f"{RED}FAILED{RESET}"
            )

            if upload.get("error"):
                print(
                    f"Reason:          "
                    f"{upload['error']}"
                )

        print()
        print(
            f"{BOLD}{BLUE}"
            "━━ SESSION STATISTICS ━━"
            f"{RESET}"
        )

        if self.download_history:
            avg_download = statistics.mean(
                self.download_history
            )

            print(
                f"Average download: "
                f"{avg_download:.2f} Mbps"
            )

        if self.upload_history:
            avg_upload = statistics.mean(
                self.upload_history
            )

            print(
                f"Average upload:   "
                f"{avg_upload:.2f} Mbps"
            )

        if self.google_latency_history:
            avg_latency = statistics.mean(
                self.google_latency_history
            )

            print(
                f"Average latency:  "
                f"{avg_latency:.0f} ms"
            )

        print(
            f"IP changes:       "
            f"{len(self.ip_history)}"
        )

        if self.ip_history:
            print()
            print(
                f"{BOLD}{BLUE}"
                "━━ RECENT IP CHANGES ━━"
                f"{RESET}"
            )

            for event in self.ip_history[-5:]:
                print(
                    f"{event['time']}  "
                    f"{event['old']} → "
                    f"{event['new']}"
                )

        print()
        print(
            f"{CYAN}"
            f"Next check in {CHECK_INTERVAL} seconds..."
            f"{RESET}"
        )

        print(
            f"{WHITE}"
            "Press Ctrl+C to exit."
            f"{RESET}"
        )

    def run(self):
        while True:
            try:
                ip_change = self.run_check()
                self.display(ip_change)
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                print()
                print()

                print(
                    f"{MAGENTA}{BOLD}"
                    "Cozy Internet Safety Monitor stopped."
                    f"{RESET}"
                )

                print(
                    f"IP changes detected: "
                    f"{len(self.ip_history)}"
                )

                return

            except Exception as exc:
                print()

                print(
                    f"{RED}"
                    f"Monitor error: {exc}"
                    f"{RESET}"
                )

                print(
                    f"Retrying in "
                    f"{CHECK_INTERVAL} seconds..."
                )

                time.sleep(CHECK_INTERVAL)


def main():
    print()

    print(
        f"{MAGENTA}{BOLD}"
        "Made with ❤️ by Cozy"
        f"{RESET}"
    )

    print(
        f"{CYAN}"
        "Starting Internet Safety Monitor..."
        f"{RESET}"
    )

    print()

    print(
        "This monitor uses public Internet services to "
        "determine your public IP and perform "
        "connectivity/speed tests."
    )

    print(
        "VPN detection is based on IP intelligence and "
        "cannot guarantee that a VPN application is running."
    )

    print()

    try:
        time.sleep(2)
    except KeyboardInterrupt:
        return

    monitor = InternetMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
# not tested
