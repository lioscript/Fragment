import http.server
import os
import re
import json

VERSION = 598

PAGE_ROUTES = {
    "/": "index.html",
    "/numbers": "html/page_2.html",
    "/gifts": "html/page_3.html",
    "/stars": "html/page_4.html",
    "/premium": "html/page_5.html",
    "/ads": "html/page_6.html",
    "/html/numbers.html": "html/page_2.html",
    "/html/gifts.html": "html/page_3.html",
    "/html/stars.html": "html/page_4.html",
    "/html/premium.html": "html/page_5.html",
    "/html/ads.html": "html/page_6.html",
}

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".zip": "application/zip",
    ".json": "application/json",
}

_page_cache = {}

def parse_page(filepath):
    if filepath in _page_cache:
        return _page_cache[filepath]

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    title_match = re.search(r"<title[^>]*>\s*(.*?)\s*</title>", content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Fragment"

    rc_match = re.search(r'<html[^>]*class=["\']([^"\']*)["\']', content)
    rc = rc_match.group(1) if rc_match else ""

    start_marker = 'id="aj_content"'
    start_idx = content.find(start_marker)
    if start_idx == -1:
        start_marker = "id='aj_content'"
        start_idx = content.find(start_marker)

    aj_html = ""
    if start_idx != -1:
        div_open_end = content.find(">", start_idx) + 1
        depth = 1
        pos = div_open_end
        while depth > 0 and pos < len(content):
            next_open = content.find("<div", pos)
            next_close = content.find("</div>", pos)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    aj_html = content[div_open_end:next_close]
                    break
                pos = next_close + 6

    result = {"title": title, "rc": rc, "aj_html": aj_html}
    _page_cache[filepath] = result
    return result


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_full_page(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        is_ajax = bool(self.headers.get("X-Aj-Referer"))

        file_path = PAGE_ROUTES.get(path)

        if file_path:
            if is_ajax:
                try:
                    page = parse_page(file_path)
                    self.send_json({
                        "v": VERSION,
                        "h": page["aj_html"],
                        "t": page["title"],
                        "rc": page["rc"],
                    })
                except Exception:
                    self.send_full_page(file_path)
            else:
                self.send_full_page(file_path)
            return

        static_path = path.lstrip("/")
        if not static_path:
            static_path = "index.html"

        if not os.path.isfile(static_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        ext = os.path.splitext(static_path)[1].lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        with open(static_path, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"{}")


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 5000), Handler)
    print("Server running on port 5000")
    server.serve_forever()
