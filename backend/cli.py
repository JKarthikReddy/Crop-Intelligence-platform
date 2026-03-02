"""crop-intel CLI — Launch the Crop Intelligence Platform with one command."""

import os
import socket
import sys
import threading
import time
import webbrowser

# Ensure the working directory is the backend package root so that
# ``import app`` (and all engine sub-packages) are discoverable.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _find_free_port(default: int = 8000) -> int:
    """Return *default* if it is available, otherwise pick a random free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", default))
            return default
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _open_browser(port: int, delay: float = 1.5) -> None:
    """Open the dashboard in the default browser after a short delay."""
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    """Entry-point wired as ``crop-intel`` console script."""
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn is not installed. Run:  pip install uvicorn")
        sys.exit(1)

    port = _find_free_port()

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║        🌾  Crop Intelligence Platform        ║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  Dashboard : http://localhost:{port:<14}║")
    print(f"  ║  API Docs  : http://localhost:{port}/docs{' '*(8-len(str(port)))}║")
    print("  ║  Press Ctrl+C to stop                       ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    # Open browser in background thread
    threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
