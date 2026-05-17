import os
import sys
import traceback
from pathlib import Path


def main():
    app_dir = Path(__file__).resolve().parent
    os.chdir(app_dir)
    os.environ["PYSTUDYFLASH_USE_APPDATA"] = "1"

    log_path = app_dir / "app.log"
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = log
        sys.stderr = log
        print("\n=== pyStudyFlash start ===")
        print(f"Python: {sys.executable}")
        print(f"App dir: {app_dir}")
        try:
            from pystudyflash import main as app_main
            app_main()
        except SystemExit:
            raise
        except Exception:
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
