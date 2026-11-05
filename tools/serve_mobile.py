import http.server, os, sys

PORT = 8000
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "web")

EXTRA_MIME = {
    ".wasm": "application/wasm",
    ".js":   "application/javascript",
    ".gz":   "application/gzip",
    ".apk":  "application/zip",
    ".ogg":  "audio/ogg",
    ".wav":  "audio/wav",
    ".png":  "image/png",
    ".ico":  "image/x-icon",
}

class MobileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BUILD_DIR, **kwargs)
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy",   "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in EXTRA_MIME:
            return EXTRA_MIME[ext]
        return super().guess_type(path)
    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}", flush=True)

os.chdir(BUILD_DIR)
with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), MobileHandler) as httpd:
    print("Servidor mobile: http://192.168.0.6:8000", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Parado.")
