import os
import sys
import time
import shutil
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) != 4:
        return 1

    current_app = Path(sys.argv[1]).resolve()
    downloaded_app = Path(sys.argv[2]).resolve()
    cleanup_dir = Path(sys.argv[3]).resolve()

    # Give the main application time to exit.
    time.sleep(2)

    if not downloaded_app.exists():
        return 2

    temp_app = current_app.with_suffix(".new.exe")

    try:
        # Wait until the old executable is no longer locked.
        for _ in range(20):
            try:
                if current_app.exists():
                    test_file = current_app.with_suffix(".lock-test")
                    with open(current_app, "rb") as source:
                        with open(test_file, "wb") as target:
                            target.write(source.read(1024))
                    test_file.unlink(missing_ok=True)
                break
            except Exception:
                time.sleep(0.5)

        shutil.copy2(downloaded_app, temp_app)

        # Replace the old executable.
        os.replace(temp_app, current_app)

        # Start the new version.
        subprocess.Popen(
            [str(current_app)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )


        subprocess.Popen(["cmd", "/c", 'timeout /t 3 /nobreak >nul & rmdir /s /q "' + str(cleanup_dir) + '"'], creationflags=subprocess.CREATE_NO_WINDOW)
        return 0

    except Exception:
        try:
            temp_app.unlink(missing_ok=True)
        except Exception:
            pass

        return 3


if __name__ == "__main__":
    raise SystemExit(main())
