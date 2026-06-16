import shutil
import subprocess

from dashboard.constants import GOOD, MUTED


def wifi_indicator():
    """(text, color) for the header WiFi icon."""
    if not shutil.which("nmcli"):
        return ("Wi-Fi —", MUTED)
    try:
        out = subprocess.check_output(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "dev"],
                                      text=True, timeout=4, stderr=subprocess.DEVNULL)
    except Exception:
        return ("Wi-Fi ?", MUTED)
    rows = [l.split(":") for l in out.splitlines() if l]
    wifi = next((r for r in rows if r and r[0] == "wifi"), None)
    if wifi and len(wifi) >= 2 and wifi[1] == "connected":
        ssid = (wifi[2] if len(wifi) > 2 and wifi[2] else "Wi-Fi")[:9]
        return (f"Wi-Fi {ssid}", GOOD)
    eth = next((r for r in rows if r and r[0] == "ethernet"), None)
    if eth and len(eth) >= 2 and eth[1] == "connected":
        return ("Wired", GOOD)
    return ("No Wi-Fi", "#f59e0b")
