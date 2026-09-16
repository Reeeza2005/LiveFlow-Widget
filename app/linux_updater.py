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
    cleanup_file = Path(sys.argv[3]).resolve()

    time.sleep(2)

    if not downloaded_app.exists():
        return 2

    temp_app = current_app.with_suffix(current_app.suffix + '.new')

    try:
        shutil.copy2(downloaded_app, temp_app)
        os.chmod(temp_app, 0o755)
        os.replace(temp_app, current_app)

        subprocess.Popen(
            [str(current_app)],
            start_new_session=True
        )

        try:
            downloaded_app.unlink(missing_ok=True)
        except Exception:
            pass

        try:
            shutil.rmtree(cleanup_file, ignore_errors=True)
        except Exception:
            pass

        try:
            shutil.rmtree(Path(sys.argv[0]).resolve().parent, ignore_errors=True)
        except Exception:
            pass
        return 0

    except Exception:
        try:
            temp_app.unlink(missing_ok=True)
        except Exception:
            pass
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
