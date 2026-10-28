"""Start a detached, localhost-only preview without installing a persistent service."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        with socket.create_connection(("127.0.0.1", 7860), timeout=1):
            print("Port 7860 already has a listener. Open http://127.0.0.1:7860; no second server started.")
            return 0
    except OSError:
        pass
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    with (logs / "workshop.log").open("ab") as output:
        process = subprocess.Popen(
            [sys.executable, "-u", "-m", "repair_shop.app"],
            cwd=root, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "GRADIO_ANALYTICS_ENABLED": "False"},
        )
    (logs / "workshop.pid").write_text(str(process.pid) + "\n")
    for _ in range(60):
        if process.poll() is not None:
            print("Workshop exited during startup. Inspect logs/workshop.log locally.")
            return 1
        try:
            with urlopen("http://127.0.0.1:7860/", timeout=1) as response:
                if response.status == 200:
                    print(f"Workshop ready at http://127.0.0.1:7860 (PID {process.pid}).")
                    print("Detached local process; log: logs/workshop.log. No login or reboot service installed.")
                    return 0
        except OSError:
            pass
        time.sleep(0.25)
    print("Startup is still pending. Check logs/workshop.log; do not start another copy blindly.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
