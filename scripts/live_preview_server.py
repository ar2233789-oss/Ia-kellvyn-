#!/usr/bin/env python3
"""Serve the existing Kellvyn Studio with two authenticated live Android screen feeds."""
from __future__ import annotations

import argparse
import io
import json
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ScreenFeed:
    def __init__(self, serial: str, label: str, interval: float = 1.0) -> None:
        self.serial = serial
        self.label = label
        self.interval = interval
        self.frame = b""
        self.version = 0
        self.updated_at = 0.0
        self.last_error = "Aguardando primeira captura ADB"
        self.lock = threading.Condition()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._capture_loop, name=f"capture-{label}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        with self.lock:
            self.lock.notify_all()

    def _capture_loop(self) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                result = subprocess.run(
                    ["adb", "-s", self.serial, "exec-out", "screencap", "-p"],
                    capture_output=True,
                    timeout=25,
                    check=False,
                )
                if result.returncode != 0 or not result.stdout.startswith(PNG_SIGNATURE):
                    message = result.stderr.decode("utf-8", "replace")[-500:] or "ADB não retornou PNG válido"
                    raise RuntimeError(message.strip())
                with Image.open(io.BytesIO(result.stdout)) as source:
                    image = source.convert("RGB")
                    image.thumbnail((680, 1510), Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=66, optimize=True)
                    frame = buffer.getvalue()
                with self.lock:
                    self.frame = frame
                    self.version += 1
                    self.updated_at = time.time()
                    self.last_error = ""
                    self.lock.notify_all()
            except Exception as error:
                with self.lock:
                    self.last_error = str(error)[:500]
                    self.lock.notify_all()
            elapsed = time.monotonic() - started
            self.stop_event.wait(max(0.15, self.interval - elapsed))

    def status(self) -> dict:
        with self.lock:
            age = time.time() - self.updated_at if self.updated_at else None
            return {
                "label": self.label,
                "device": self.serial,
                "connected": age is not None and age < 6.0,
                "frameAgeSeconds": round(age, 2) if age is not None else None,
                "frameNumber": self.version,
                "lastError": self.last_error,
            }

    def next_frame(self, previous_version: int, timeout: float = 2.0) -> tuple[bytes, int]:
        deadline = time.monotonic() + timeout
        with self.lock:
            while self.version <= previous_version and not self.stop_event.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self.lock.wait(remaining)
            return self.frame, self.version


def build_studio_page(studio_path: Path, token: str) -> bytes:
    html = studio_path.read_text(encoding="utf-8")
    prefix = "/" + token

    nav_marker = '<button class="nav" data-page="report"><span class="ico">▥</span> Relatórios</button>'
    nav_live = nav_marker + '\n  <button class="nav active" data-page="live"><span class="ico">◉</span> Ao vivo</button>'
    if nav_marker not in html:
        raise RuntimeError("Não encontrei a navegação original de Relatórios no Studio.")
    html = html.replace(nav_marker, nav_live, 1)

    css = """
.live-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.live-card{min-width:0;border:1px solid var(--line);border-radius:14px;background:#081116;overflow:hidden}
.live-card-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.live-card-head strong{font-size:13px}
.live-frame{display:block;width:100%;height:auto;max-height:calc(100vh - 245px);min-height:260px;object-fit:contain;background:#020507}
.live-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.live-state{display:inline-flex;align-items:center;gap:6px}
.live-state i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#ff6978}
.live-state i.ok{background:#5ee2a0;box-shadow:0 0 9px #5ee2a080}
@media(max-width:760px){.live-grid{grid-template-columns:repeat(2,minmax(280px,1fr));overflow-x:auto;padding-bottom:8px}.live-frame{max-height:calc(100vh - 250px);min-height:220px}}
"""
    html = html.replace("</style>", css + "\n</style>", 1)

    live_section = """
  <section class="page" id="page-live">
    <p class="intro">Transmissão das duas execuções reais no laboratório Android 15. À esquerda está a referência original dentro da WebView de teste; à direita está o APK Android nativo. Os dois aparelhos virtuais ficam ligados ao mesmo tempo e enviam quadros atuais ao Studio.</p>
    <div class="row" style="margin:0 0 12px">
      <span class="pill"><span class="dot"></span> Emulação Android 15 · 1220 × 2712 · 440 dpi</span>
      <span class="pill" id="liveOverall">Conectando às telas…</span>
      <button id="liveRefresh">Reconectar imagens</button>
    </div>
    <div class="live-grid">
      <div class="live-card">
        <div class="live-card-head"><strong>Referência WebView</strong><span class="badge live-state"><i id="webDot"></i><span id="webStatus">Aguardando</span></span></div>
        <img class="live-frame" id="webFrame" alt="Tela ao vivo da versão original na WebView" src="__PREFIX__/stream/webview">
        <div class="live-card-head"><span class="sub">PocoF6Virtual-Web · APK auxiliar de laboratório</span><button id="webFullscreen">Ampliar</button></div>
      </div>
      <div class="live-card">
        <div class="live-card-head"><strong>Android nativo</strong><span class="badge live-state"><i id="nativeDot"></i><span id="nativeStatus">Aguardando</span></span></div>
        <img class="live-frame" id="nativeFrame" alt="Tela ao vivo do APK Android nativo" src="__PREFIX__/stream/native">
        <div class="live-card-head"><span class="sub">PocoF6Virtual · com.kellvyn.assistant</span><button id="nativeFullscreen">Ampliar</button></div>
      </div>
    </div>
    <p class="sub" style="margin-top:12px">A WebView existe somente nesta bancada de comparação e não entra no APK de distribuição. São duas instâncias virtuais com o mesmo perfil de resolução, densidade, RAM e CPU; isso permite ver os dois aplicativos ao mesmo tempo, mas não substitui o teste no Poco F6 físico com HyperOS.</p>
  </section>
"""
    live_section = live_section.replace("__PREFIX__", prefix)
    footer_marker = '<footer class="foot">'
    if footer_marker not in html:
        raise RuntimeError("Não encontrei o rodapé original do Studio.")
    html = html.replace(footer_marker, live_section + "\n  " + footer_marker, 1)

    pages_marker = 'report:"Relatórios do laboratório"}'
    if pages_marker not in html:
        raise RuntimeError("Não encontrei o mapa de páginas original do Studio.")
    html = html.replace(pages_marker, 'report:"Relatórios do laboratório",live:"Acompanhamento ao vivo"}', 1)

    boot_script = """
<script>
(function(){
  var prefix = "__PREFIX__";
  var web = document.getElementById("webFrame");
  var native = document.getElementById("nativeFrame");
  function connectImage(img, route){
    img.onerror = function(){ img.dataset.failed = "1"; };
    img.onload = function(){ img.dataset.failed = "0"; };
  }
  connectImage(web, "webview");
  connectImage(native, "native");
  function badge(name, state){
    var dot = document.getElementById(name + "Dot");
    var text = document.getElementById(name + "Status");
    dot.classList.toggle("ok", !!state.connected);
    text.textContent = state.connected ? "AO VIVO · quadro " + state.frameNumber : "Sem sinal";
    if(state.frameAgeSeconds !== null && !state.connected) text.textContent += " · " + state.frameAgeSeconds + "s";
  }
  function poll(){
    fetch(prefix + "/health?t=" + Date.now(), {cache:"no-store"})
      .then(function(response){ if(!response.ok) throw new Error("HTTP " + response.status); return response.json(); })
      .then(function(data){
        badge("web", data.webview);
        badge("native", data.native);
        var both = data.webview.connected && data.native.connected;
        document.getElementById("liveOverall").textContent = both ? "Duas telas transmitindo" : "Reconectando uma das telas…";
      })
      .catch(function(){
        document.getElementById("liveOverall").textContent = "Conexão interrompida";
      });
  }
  document.getElementById("liveRefresh").addEventListener("click", function(){
    var stamp = Date.now();
    web.src = prefix + "/stream/webview?refresh=" + stamp;
    native.src = prefix + "/stream/native?refresh=" + stamp;
    poll();
  });
  document.getElementById("webFullscreen").addEventListener("click", function(){
    if(web.requestFullscreen) web.requestFullscreen();
  });
  document.getElementById("nativeFullscreen").addEventListener("click", function(){
    if(native.requestFullscreen) native.requestFullscreen();
  });
  window.setInterval(poll, 1400);
  poll();
  var liveNav = document.querySelector('button.nav[data-page="live"]');
  if(liveNav) liveNav.click();
})();
</script>
"""
    html = html.replace("__PREFIX__", prefix)
    html = html.replace("</body>", boot_script + "\n</body>", 1)
    return html.encode("utf-8")


class LiveServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, token: str, page: bytes, web_feed: ScreenFeed, native_feed: ScreenFeed):
        super().__init__(address, handler)
        self.token = token
        self.page = page
        self.feeds = {"webview": web_feed, "native": native_feed}
        self.stop_event = threading.Event()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *args) -> None:
        # Keep the bearer URL out of Actions logs.
        return

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        server: LiveServer = self.server  # type: ignore[assignment]
        path = urlsplit(self.path).path
        prefix = "/" + server.token
        if path == "/":
            self.send_response(302)
            self.send_header("Location", prefix + "/")
            self.end_headers()
            return
        if path in {prefix, prefix + "/"}:
            self._send(200, server.page, "text/html; charset=utf-8")
            return
        if path == prefix + "/health":
            payload = json.dumps(
                {
                    "status": "streaming",
                    "webview": server.feeds["webview"].status(),
                    "native": server.feeds["native"].status(),
                    "updatedAt": time.time(),
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        for name in ("webview", "native"):
            if path == prefix + "/stream/" + name:
                self._stream(server.feeds[name])
                return
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def _stream(self, feed: ScreenFeed) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Connection", "close")
        self.end_headers()
        version = -1
        try:
            while not self.server.stop_event.is_set():  # type: ignore[attr-defined]
                frame, current = feed.next_frame(version, timeout=2.5)
                if not frame:
                    continue
                if current == version:
                    continue
                packet = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                    + frame
                    + b"\r\n"
                )
                self.wfile.write(packet)
                self.wfile.flush()
                version = current
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        except OSError:
            return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studio", type=Path, required=True)
    parser.add_argument("--webview-device", required=True)
    parser.add_argument("--native-device", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    if len(args.token) < 24:
        parser.error("O token de acesso precisa ter pelo menos 24 caracteres.")
    if not args.studio.is_file():
        parser.error(f"Studio não encontrado: {args.studio}")

    web_feed = ScreenFeed(args.webview_device, "WebView", args.interval)
    native_feed = ScreenFeed(args.native_device, "Nativo", args.interval)
    web_feed.start()
    native_feed.start()
    page = build_studio_page(args.studio, args.token)
    server = LiveServer(("127.0.0.1", args.port), Handler, args.token, page, web_feed, native_feed)

    def stop_server(_signum, _frame) -> None:
        server.stop_event.set()
        web_feed.stop()
        native_feed.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    print(
        json.dumps(
            {
                "status": "ready",
                "localUrl": f"http://127.0.0.1:{args.port}/",
                "webviewDevice": args.webview_device,
                "nativeDevice": args.native_device,
                "refreshIntervalSeconds": args.interval,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        web_feed.stop()
        native_feed.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
