import os
import sys
from pathlib import Path

APP_NAME = "pyStudyFlash"


def app_root_dir() -> Path:
    """Directory with bundled resources for source and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> str:
    return str(app_root_dir().joinpath(*parts))


def settings_dir() -> Path:
    """
    Writable settings directory.
    - Source run: project sets/ folder (keeps backward compatibility).
    - Frozen app: %APPDATA%\\pyStudyFlash.
    - Installed source app: %APPDATA%\\pyStudyFlash when requested by launcher.
    """
    use_appdata = os.getenv("PYSTUDYFLASH_USE_APPDATA", "").strip().lower() in {"1", "true", "yes", "on"}
    if getattr(sys, "frozen", False) or use_appdata:
        base = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA") or str(Path.home())
        path = Path(base) / APP_NAME
    else:
        path = app_root_dir() / "sets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file_path() -> str:
    return str(settings_dir() / "settings.ini")


def address_book_file_path() -> str:
    return str(settings_dir() / "address_book")
