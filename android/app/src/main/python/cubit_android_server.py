"""Bootstrap Cubit FastAPI app on Android via Chaquopy.

Starts uvicorn on 127.0.0.1:<port>. The Kotlin WebView loads the same dashboard.
No payments, wallet, or cloud requirements.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

_server_thread: threading.Thread | None = None
_started = False


def _ensure_cubit_on_path() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


def start_server(port: int = 8765, data_root: str | None = None) -> str:
    """Start uvicorn in a daemon thread. Idempotent.

    data_root: writable directory for JSON stores (Android filesDir/cubit_data).
    """
    global _server_thread, _started
    if _started:
        return f"already running on 127.0.0.1:{port}"

    _ensure_cubit_on_path()
    os.environ["CUBIT_ANDROID"] = "1"
    if data_root:
        Path(data_root).mkdir(parents=True, exist_ok=True)
        os.environ["CUBIT_DATA_ROOT"] = str(data_root)
    elif "CUBIT_DATA_ROOT" not in os.environ:
        fallback = Path.home() / "cubit_data"
        fallback.mkdir(parents=True, exist_ok=True)
        os.environ["CUBIT_DATA_ROOT"] = str(fallback)

    def run() -> None:
        import uvicorn
        from cubit.web.app import app

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=int(port),
            log_level="warning",
            access_log=False,
        )

    _server_thread = threading.Thread(target=run, name="cubit-uvicorn", daemon=True)
    _server_thread.start()
    _started = True
    return f"started on 127.0.0.1:{port} data={os.environ.get('CUBIT_DATA_ROOT')}"
