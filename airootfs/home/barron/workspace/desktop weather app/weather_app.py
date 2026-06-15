#!/usr/bin/env python3
"""Lightweight Ubuntu desktop weather widget.

No API key required. Uses Open-Meteo geocoding + forecast APIs.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import threading
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import Canvas, Tk, messagebox

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "weather_app.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

WEATHER_CODES = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Thunderstorm hail",
    99: "Severe thunderstorm",
}

WEATHER_ICONS = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️",
    53: "🌦️",
    55: "🌧️",
    61: "🌦️",
    63: "🌧️",
    65: "🌧️",
    71: "🌨️",
    73: "❄️",
    75: "❄️",
    80: "🌦️",
    81: "🌧️",
    82: "⛈️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️",
}

# Clean modern dark-card palette chosen in the 20-question appearance pass.
CARD = "#111827"
CARD_2 = "#172033"
SHADOW = "#020617"
BLUE = "#38bdf8"
BLUE_DARK = "#1e3a8a"
TEXT = "#f8fafc"
MUTED = "#cbd5e1"
DIM = "#94a3b8"
TEMP = "#fde68a"


def weather_icon(code: int | str | None) -> str:
    try:
        return WEATHER_ICONS.get(int(code), "🌡️")
    except Exception:
        return "🌡️"


def load_config() -> dict:
    default = {
        "location": "New York, NY",
        "forecast_days": 7,
        "refresh_minutes": 30,
        "always_on_top": True,
        "always_on_bottom": False,
        "opacity": 0.96,
        "width": 900,
        "height": 340,
        "position_mode": "manual",
        "top_margin": 35,
        "position": {"x": 80, "y": 766},
    }
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            default.update(data)
        except Exception as exc:
            logging.exception("Failed to read config.json: %s", exc)
    return default


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def http_json(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "desktop-weather-widget/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(location: str) -> dict:
    queries = [location]
    if "," in location:
        queries.append(location.split(",", 1)[0].strip())
    if " VA" in location.upper() or " VIRGINIA" in location.upper():
        queries.append(location.upper().replace(" VIRGINIA", "").replace(" VA", "").title())

    results = []
    for query in dict.fromkeys(q for q in queries if q):
        url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
            {"name": query, "count": 3, "language": "en", "format": "json"}
        )
        data = http_json(url)
        results = data.get("results") or []
        if results:
            break
    if not results:
        raise RuntimeError(f"No location found for {location!r}")
    r = results[0]
    return {
        "name": r.get("name", location),
        "admin1": r.get("admin1", ""),
        "country": r.get("country", ""),
        "lat": r["latitude"],
        "lon": r["longitude"],
    }


def fetch_weather(config: dict) -> dict:
    loc = geocode(config.get("location", "New York, NY"))
    days = int(config.get("forecast_days", 7))
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": max(1, min(days, 16)),
        "timezone": "auto",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    data = http_json(url)
    current = data.get("current", {})
    daily = data.get("daily", {})
    forecast = []
    for date, hi, lo, code in zip(
        daily.get("time", []),
        daily.get("temperature_2m_max", []),
        daily.get("temperature_2m_min", []),
        daily.get("weather_code", []),
    ):
        forecast.append(
            {
                "date": date,
                "hi": round(float(hi)),
                "lo": round(float(lo)),
                "code": int(code),
                "icon": weather_icon(code),
                "condition": WEATHER_CODES.get(int(code), f"Code {code}"),
            }
        )
    current_code = int(current.get("weather_code", 0))
    humidity = current.get("relative_humidity_2m")
    feels_like = current.get("apparent_temperature")
    wind = current.get("wind_speed_10m")
    precipitation = current.get("precipitation")
    return {
        "location": ", ".join(x for x in [loc["name"], loc["admin1"]] if x),
        "temp": round(float(current.get("temperature_2m", 0))),
        "feels_like": round(float(feels_like)) if feels_like is not None else None,
        "humidity": round(float(humidity)) if humidity is not None else None,
        "wind": round(float(wind)) if wind is not None else None,
        "precipitation": round(float(precipitation), 1) if precipitation is not None else None,
        "code": current_code,
        "icon": weather_icon(current_code),
        "condition": WEATHER_CODES.get(current_code, "Unknown"),
        "forecast": forecast,
        "updated": datetime.now().strftime("%I:%M %p").lstrip("0"),
    }


def rounded_rect(canvas: Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> None:
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def _bbox_union(canvas: Canvas, items: list[int]) -> tuple[int, int, int, int]:
    boxes = [canvas.bbox(item) for item in items]
    boxes = [box for box in boxes if box]
    if not boxes:
        return (0, 0, 0, 0)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def draw_weather_symbol(canvas: Canvas, cx: float, top: float, code: int | str | None, size: int) -> tuple[int, int, int, int]:
    """Draw a colored weather symbol and return its Canvas bbox.

    Native emoji can appear monochrome or vary wildly between Tk/font setups.
    These vector symbols keep the sun yellow, rain blue, and clouds gray.
    """
    try:
        c = int(code)
    except Exception:
        c = -1
    x = float(cx)
    y = float(top)
    s = float(size)
    items: list[int] = []

    def sun(center_x: float, center_y: float, radius: float) -> None:
        for dx, dy in [(0, -1), (0.7, -0.7), (1, 0), (0.7, 0.7), (0, 1), (-0.7, 0.7), (-1, 0), (-0.7, -0.7)]:
            items.append(
                canvas.create_line(
                    center_x + dx * radius * 1.45,
                    center_y + dy * radius * 1.45,
                    center_x + dx * radius * 2.0,
                    center_y + dy * radius * 2.0,
                    fill="#facc15",
                    width=max(2, int(s / 14)),
                    capstyle="round",
                )
            )
        items.append(canvas.create_oval(center_x - radius, center_y - radius, center_x + radius, center_y + radius, fill="#fbbf24", outline="#fde047", width=2))

    def cloud(left: float, cloud_top: float, scale: float = 1.0) -> None:
        w = s * scale
        h = s * 0.45 * scale
        fill = "#cbd5e1"
        outline = "#e2e8f0"
        items.append(canvas.create_oval(left + w * 0.08, cloud_top + h * 0.25, left + w * 0.42, cloud_top + h * 0.95, fill=fill, outline=outline, width=1))
        items.append(canvas.create_oval(left + w * 0.28, cloud_top, left + w * 0.68, cloud_top + h * 0.85, fill=fill, outline=outline, width=1))
        items.append(canvas.create_oval(left + w * 0.55, cloud_top + h * 0.20, left + w * 0.92, cloud_top + h * 0.95, fill=fill, outline=outline, width=1))
        items.append(canvas.create_rectangle(left + w * 0.20, cloud_top + h * 0.48, left + w * 0.82, cloud_top + h * 0.95, fill=fill, outline=fill))

    def rain(left: float, rain_top: float, scale: float = 1.0) -> None:
        for i in range(3):
            drop_x = left + s * scale * (0.28 + i * 0.22)
            items.append(canvas.create_line(drop_x, rain_top, drop_x - s * scale * 0.08, rain_top + s * scale * 0.18, fill="#38bdf8", width=max(2, int(s / 13)), capstyle="round"))

    if c == 0:
        sun(x, y + s * 0.48, s * 0.22)
    elif c in {1, 2}:
        sun(x - s * 0.18, y + s * 0.36, s * 0.16)
        cloud(x - s * 0.38, y + s * 0.34, 0.78)
    elif c in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        cloud(x - s * 0.45, y + s * 0.08, 0.90)
        rain(x - s * 0.45, y + s * 0.58, 0.90)
    elif c in {95, 96, 99}:
        cloud(x - s * 0.45, y + s * 0.05, 0.90)
        items.append(canvas.create_polygon(x - s * 0.05, y + s * 0.50, x + s * 0.08, y + s * 0.50, x - s * 0.04, y + s * 0.88, x + s * 0.22, y + s * 0.40, x + s * 0.08, y + s * 0.40, fill="#facc15", outline="#fde047"))
        rain(x - s * 0.45, y + s * 0.62, 0.80)
    elif c in {71, 73, 75}:
        cloud(x - s * 0.45, y + s * 0.08, 0.90)
        for i in range(3):
            items.append(canvas.create_text(x - s * 0.24 + i * s * 0.24, y + s * 0.72, text="✦", anchor="center", fill="#bfdbfe", font=("Ubuntu", max(9, int(s * 0.28)), "bold")))
    else:
        cloud(x - s * 0.45, y + s * 0.20, 0.90)

    return _bbox_union(canvas, items)


def primary_monitor_geometry() -> tuple[int, int, int, int] | None:
    """Return x, y, width, height for the primary xrandr monitor when available."""
    try:
        out = subprocess.check_output(["xrandr", "--query"], text=True, stderr=subprocess.DEVNULL, timeout=3)
    except Exception:
        return None
    for line in out.splitlines():
        if " connected primary " not in line:
            continue
        match = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
        if match:
            w, h, x, y = map(int, match.groups())
            return x, y, w, h
    return None


class WeatherWidget:
    def __init__(self) -> None:
        self.config = load_config()
        self.width = int(self.config.get("width", 900))
        self.height = int(self.config.get("height", 285))
        self.root = Tk()
        self.root.title("Desktop Weather Widget")
        self.always_on_bottom = bool(self.config.get("always_on_bottom", False))
        # GNOME/Wayland handles normal window-manager managed windows more
        # reliably than override-redirect windows for below/desktop stacking.
        # Use a desktop-type window when the widget should sit behind apps.
        self.root.overrideredirect(not self.always_on_bottom)
        if self.always_on_bottom:
            try:
                self.root.attributes("-type", "desktop")
            except Exception as exc:
                logging.info("Desktop window type not supported: %s", exc)
        self.root.configure(bg=SHADOW)
        self.root.attributes("-alpha", float(self.config.get("opacity", 0.96)))
        if self.config.get("always_on_top", False):
            self.root.attributes("-topmost", True)
        elif self.always_on_bottom:
            self.root.after(500, self.keep_on_bottom)
        self._set_initial_geometry()
        self._drag_start = (0, 0)
        self.hover_controls = False

        self.canvas = Canvas(self.root, width=self.width, height=self.height, bg=SHADOW, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.save_position)
        self.canvas.bind("<Enter>", self.show_controls)
        self.canvas.bind("<Leave>", self.hide_controls)
        self.canvas.tag_bind("refresh", "<Button-1>", lambda _e: self.refresh_async())
        self.canvas.tag_bind("close", "<Button-1>", lambda _e: self.root.destroy())
        self.root.bind("<Escape>", lambda _e: self.root.destroy())

        self.draw_loading()
        self.root.after(250, self.refresh_async)
        self.schedule_refresh()

    def _set_initial_geometry(self) -> None:
        pos = self.config.get("position", {}) or {}
        if self.config.get("position_mode") == "top_center":
            # Top-center should mean the primary/vertical monitor, not the
            # center of the whole combined virtual desktop. On this setup the
            # combined center can land above/between monitors and look hidden.
            geom = primary_monitor_geometry()
            if geom:
                mx, my, mw, mh = geom
            else:
                mx, my, mw, mh = 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            x = mx + max(0, int((mw - self.width) / 2))
            y = my + int(self.config.get("top_margin", 35))
            x = max(mx, min(x, mx + max(0, mw - self.width)))
            y = max(my, min(y, my + max(0, mh - self.height)))
        else:
            x = int(pos.get("x", 40))
            y = int(pos.get("y", 80))
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        # Enforce geometry after GNOME/Tk maps the window; avoids invisible or
        # clipped first-map placement after monitor layout changes.
        self.root.after(250, lambda: self.root.geometry(f"{self.width}x{self.height}+{x}+{y}"))

    def keep_on_bottom(self) -> None:
        """Keep the widget below normal windows when the window manager allows it."""
        try:
            self.root.attributes("-topmost", False)
            self.root.lower()
            self.root.update_idletasks()
            candidate_ids = {str(self.root.winfo_id())}
            try:
                out = subprocess.check_output(
                    ["xdotool", "search", "--name", "Desktop Weather Widget"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                candidate_ids.update(line.strip() for line in out.splitlines() if line.strip())
            except Exception:
                pass
            for xid in candidate_ids:
                subprocess.run(
                    [
                        "xprop",
                        "-id",
                        xid,
                        "-f",
                        "_NET_WM_WINDOW_TYPE",
                        "32a",
                        "-set",
                        "_NET_WM_WINDOW_TYPE",
                        "_NET_WM_WINDOW_TYPE_DESKTOP",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                    check=False,
                )
                subprocess.run(
                    [
                        "xprop",
                        "-id",
                        xid,
                        "-f",
                        "_NET_WM_STATE",
                        "32a",
                        "-set",
                        "_NET_WM_STATE",
                        "_NET_WM_STATE_BELOW",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                    check=False,
                )
            self.root.lower()
        except Exception as exc:
            logging.warning("Could not set below-window state: %s", exc)
        if not self.config.get("always_on_top", False) and self.config.get("always_on_bottom", False):
            self.root.after(5000, self.keep_on_bottom)

    def draw_base(self) -> None:
        self.canvas.delete("all")
        # Soft shadow then mostly solid dark rounded card with subtle blue border.
        rounded_rect(self.canvas, 14, 16, self.width - 8, self.height - 8, 24, fill=SHADOW, outline="")
        rounded_rect(self.canvas, 8, 8, self.width - 16, self.height - 16, 24, fill=CARD, outline=BLUE, width=2)
        rounded_rect(self.canvas, 18, 18, self.width - 26, self.height - 26, 18, fill=CARD_2, outline=BLUE_DARK, width=1)

    def draw_loading(self) -> None:
        self.draw_base()
        self.canvas.create_text(44, 44, text="🌡️  Loading weather...", anchor="nw", fill=TEXT, font=("Ubuntu", 28, "bold"))
        self.draw_controls()

    def draw_controls(self) -> None:
        if not self.hover_controls:
            return
        self.canvas.create_text(self.width - 92, 24, text="↻", tags=("refresh",), anchor="center", fill=BLUE, font=("Ubuntu", 20, "bold"))
        self.canvas.create_text(self.width - 48, 24, text="×", tags=("close",), anchor="center", fill=BLUE, font=("Ubuntu", 20, "bold"))

    def show_controls(self, _event=None) -> None:
        self.hover_controls = True
        if hasattr(self, "latest_data"):
            self.render(self.latest_data)
        else:
            self.draw_loading()

    def hide_controls(self, _event=None) -> None:
        self.hover_controls = False
        if hasattr(self, "latest_data"):
            self.render(self.latest_data)
        else:
            self.draw_loading()

    def start_drag(self, event) -> None:
        self._drag_start = (event.x, event.y)

    def drag(self, event) -> None:
        x = self.root.winfo_x() + event.x - self._drag_start[0]
        y = self.root.winfo_y() + event.y - self._drag_start[1]
        self.root.geometry(f"+{x}+{y}")

    def save_position(self, _event=None) -> None:
        self.config["position"] = {"x": self.root.winfo_x(), "y": self.root.winfo_y()}
        # If user drags it, respect that manual position next time.
        self.config["position_mode"] = "manual"
        save_config(self.config)

    def schedule_refresh(self) -> None:
        minutes = max(5, int(self.config.get("refresh_minutes", 30)))
        self.root.after(minutes * 60 * 1000, self.refresh_then_reschedule)

    def refresh_then_reschedule(self) -> None:
        self.refresh_async()
        self.schedule_refresh()

    def refresh_async(self) -> None:
        self.canvas.delete("status")
        self.canvas.create_text(34, self.height - 36, text="Refreshing...", tags=("status",), anchor="w", fill=DIM, font=("Ubuntu", 10))
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self) -> None:
        try:
            data = fetch_weather(self.config)
            self.root.after(0, lambda: self.render(data))
        except Exception as exc:
            logging.exception("Weather refresh failed: %s", exc)
            self.root.after(0, lambda: self.show_error(str(exc)))

    def render(self, data: dict) -> None:
        self.latest_data = data
        self.draw_base()

        # Current weather: colored vector icon with a clear gutter before temp.
        current_icon_box = draw_weather_symbol(self.canvas, 102, 48, data.get("code"), 70)
        temp_x = max(212, current_icon_box[2] + 34)
        self.canvas.create_text(temp_x, 42, text=f"{data['temp']}°F", anchor="nw", fill=TEXT, font=("Ubuntu", 52, "bold"))
        self.canvas.create_text(temp_x + 4, 106, text=data["condition"], anchor="nw", fill=BLUE, font=("Ubuntu", 21, "bold"))
        details = []
        if data.get("feels_like") is not None:
            details.append(f"Feels {data['feels_like']}°")
        if data.get("humidity") is not None:
            details.append(f"Humidity {data['humidity']}%")
        if data.get("wind") is not None:
            details.append(f"Wind {data['wind']} mph")
        if data.get("precipitation") is not None and data["precipitation"] > 0:
            details.append(f"Rain {data['precipitation']:.1f} in")
        if details:
            detail_x = min(temp_x + 260, self.width - 360)
            self.canvas.create_text(detail_x, 58, text="  ·  ".join(details[:2]), anchor="nw", fill=MUTED, font=("Ubuntu", 12, "bold"))
            if len(details) > 2:
                self.canvas.create_text(detail_x, 84, text="  ·  ".join(details[2:4]), anchor="nw", fill=MUTED, font=("Ubuntu", 12, "bold"))

        # Seven airy forecast cards. Vector icons keep sun/rain/clouds colorful,
        # and bottom text is pinned above the card edge so it never touches.
        days = data.get("forecast", [])[: int(self.config.get("forecast_days", 7))]
        start_x = 28
        y = 146
        gap = 10
        card_w = int((self.width - 2 * start_x - gap * 6) / 7)
        card_h = 142
        for idx, day in enumerate(days):
            x = start_x + idx * (card_w + gap)
            rounded_rect(self.canvas, x, y, x + card_w, y + card_h, 16, fill="#0f172a", outline="#1e40af", width=1)
            dt = datetime.strptime(day["date"], "%Y-%m-%d")
            self.canvas.create_text(x + card_w / 2, y + 10, text=dt.strftime("%a"), anchor="n", fill=MUTED, font=("Ubuntu", 15, "bold"))
            icon_box = draw_weather_symbol(self.canvas, x + card_w / 2, y + 38, day.get("code"), 38)
            temp_y = max(y + 82, icon_box[3] + 8)
            condition_y = min(temp_y + 30, y + card_h - 25)
            self.canvas.create_text(x + card_w / 2, temp_y, text=f"{day['hi']}°/{day['lo']}°", anchor="n", fill=TEMP, font=("Ubuntu", 15, "bold"))
            self.canvas.create_text(x + card_w / 2, condition_y, text=day["condition"][:13], anchor="n", fill=MUTED, font=("Ubuntu", 9, "bold"))

        # Bottom context line, intentionally small.
        bottom = f"{data['location']} · Updated {data['updated']}"
        self.canvas.create_text(34, self.height - 32, text=bottom, anchor="w", fill=DIM, font=("Ubuntu", 10))
        self.draw_controls()

    def show_error(self, msg: str) -> None:
        self.draw_base()
        self.canvas.create_text(48, 54, text="⚠️ Weather unavailable", anchor="nw", fill=TEXT, font=("Ubuntu", 30, "bold"))
        self.canvas.create_text(52, 114, text="Check internet/DNS, then hover and click refresh.", anchor="nw", fill=MUTED, font=("Ubuntu", 14))
        self.canvas.create_text(52, 158, text=msg[:140], anchor="nw", fill=DIM, font=("Ubuntu", 10))
        self.draw_controls()

    def run(self) -> None:
        logging.info("Weather widget started")
        self.root.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="fetch weather once and print JSON")
    args = parser.parse_args()
    if args.self_test:
        data = fetch_weather(load_config())
        print(json.dumps(data, indent=2))
        return 0
    try:
        WeatherWidget().run()
        return 0
    except Exception as exc:
        logging.exception("Widget failed to start: %s", exc)
        try:
            messagebox.showerror("Weather Widget", str(exc))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
