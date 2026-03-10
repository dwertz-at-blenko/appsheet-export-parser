"""Fetch live AppSheet documentation via Chrome CDP.

Uses headless Chrome with a persistent user-data-dir for auth cookies.
Extracts document.body.innerText which produces clean, tab-delimited text
identical in structure to PDF text but without page-break artifacts.
"""

from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

# websockets is used for CDP communication — imported lazily to keep
# the module importable even when websockets isn't installed (PDF-only mode).


def fetch_appdoc_text(
    url: str,
    chrome_profile: str = "/tmp/chrome-shopify-app",
    timeout: int = 30,
) -> str:
    """Fetch the innerText of an AppSheet documentation page via CDP.

    1. If Chrome is already running on port 9222, reuse it.
    2. Otherwise, launch headless Chrome with the given profile dir.
    3. Navigate to the URL, wait for content, extract innerText.

    Args:
        url: Full AppSheet doc URL.
        chrome_profile: Path to Chrome user-data-dir with auth cookies.
        timeout: Max seconds to wait for page load.

    Returns:
        The full innerText of the page body.

    Raises:
        RuntimeError: If Chrome can't be reached or page fails to load.
    """
    import asyncio
    return asyncio.run(_fetch_async(url, chrome_profile, timeout))


async def _fetch_async(url: str, chrome_profile: str, timeout: int) -> str:
    """Async implementation of the CDP fetch."""
    try:
        import websockets
    except ImportError:
        raise RuntimeError(
            "websockets package required for URL mode. "
            "Install with: pip install websockets"
        )

    chrome_launched = False
    ws_url = _get_debugger_url()

    if not ws_url:
        # Launch headless Chrome
        _launch_chrome(chrome_profile)
        chrome_launched = True
        # Wait for Chrome to start
        for _ in range(20):
            time.sleep(0.5)
            ws_url = _get_debugger_url()
            if ws_url:
                break
        if not ws_url:
            raise RuntimeError("Failed to connect to Chrome on port 9222")

    try:
        async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
            msg_id = 1

            async def send_cmd(method: str, params: dict | None = None) -> dict:
                nonlocal msg_id
                cmd = {"id": msg_id, "method": method}
                if params:
                    cmd["params"] = params
                msg_id += 1
                await ws.send(json.dumps(cmd))

                # Wait for matching response
                deadline = time.time() + timeout
                while time.time() < deadline:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == cmd["id"]:
                        if "error" in resp:
                            raise RuntimeError(
                                f"CDP error: {resp['error'].get('message', resp['error'])}"
                            )
                        return resp.get("result", {})
                raise RuntimeError(f"Timeout waiting for CDP response to {method}")

            # Navigate to the URL
            await send_cmd("Page.enable")
            await send_cmd("Page.navigate", {"url": url})

            # Wait for page load
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = await ws.recv()
                msg = json.loads(raw)
                if msg.get("method") == "Page.loadEventFired":
                    break
            else:
                raise RuntimeError("Timeout waiting for page load")

            # Give the page a moment to render dynamic content
            time.sleep(2)

            # Extract innerText
            result = await send_cmd(
                "Runtime.evaluate",
                {"expression": "document.body.innerText", "returnByValue": True},
            )

            inner_text = result.get("result", {}).get("value", "")
            if not inner_text or len(inner_text) < 1000:
                raise RuntimeError(
                    f"Page content too short ({len(inner_text)} chars) — "
                    "auth cookies may have expired"
                )

            return inner_text

    finally:
        if chrome_launched:
            _kill_chrome()


def _get_debugger_url() -> str | None:
    """Get the WebSocket debugger URL from Chrome DevTools on port 9222."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("webSocketDebuggerUrl")
    except Exception:
        return None


def _is_port_open(port: int = 9222) -> bool:
    """Check if a port is open on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _launch_chrome(profile_dir: str) -> subprocess.Popen:
    """Launch headless Chrome with remote debugging."""
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    chrome_bin = None
    for p in chrome_paths:
        if Path(p).exists():
            chrome_bin = p
            break

    if not chrome_bin:
        raise RuntimeError("Chrome/Chromium not found on system")

    args = [
        chrome_bin,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--window-size=1920,1080",
        "about:blank",
    ]
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _kill_chrome() -> None:
    """Kill any Chrome processes we launched."""
    subprocess.run(
        ["pkill", "-f", "remote-debugging-port=9222"],
        capture_output=True,
    )
