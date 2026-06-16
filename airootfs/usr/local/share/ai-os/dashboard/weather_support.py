import importlib.util

from dashboard.paths import WORKSPACE

WEATHER_APP_DIR = WORKSPACE / "desktop weather app"
WEATHER_LAUNCH = WEATHER_APP_DIR / "launch.sh"


def load_weather_app():
    """Import the real weather app as a module."""
    spec = importlib.util.spec_from_file_location(
        "weather_app", WEATHER_APP_DIR / "weather_app.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load weather app from {WEATHER_APP_DIR / 'weather_app.py'}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    WAPP = load_weather_app()
except Exception:
    WAPP = None
