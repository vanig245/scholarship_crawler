import re, time, hashlib, requests, urllib3
from urllib.parse import urljoin, urlparse
from urllib import robotparser
from bs4 import BeautifulSoup
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
S = requests.Session()
S.headers.update({"User-Agent": config.USER_AGENT})
_robots, _last = {}, {}
BLOCK = ["p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6",
         "section", "article", "table", "ul", "ol"]

def _polite(domain):
    wait = config.CRAWL_DELAY_SECONDS - (time.time() - _last.get(domain, 0))
    if wait > 0:
        time.sleep(wait)
    _last[domain] = time.time()

def allowed(url):
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = robotparser.RobotFileParser()
        try:
            r = S.get(base + "/robots.txt", timeout=config.REQUEST_TIMEOUT)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(config.USER_AGENT, url)

def _get(url):
    try:
        return S.get(url, timeout=config.REQUEST_TIMEOUT)
    except requests.exceptions.SSLError:      # some gov sites have broken certificates; read-only public pages
        return S.get(url, timeout=config.REQUEST_TIMEOUT, verify=False)

def parse_page(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip()).split("#")[0]
        if href.startswith("http"):
            links.append((href, " ".join(a.get_text(" ").split())))
    title = " ".join(soup.title.get_text(" ").split()) if soup.title else ""
    h1_tag = soup.find("h1")
    h1 = " ".join(h1_tag.get_text(" ").split()) if h1_tag else ""
    meta = soup.find("meta", attrs={"property": "og:site_name"})
    site_name = meta["content"].strip() if meta and meta.get("content") else ""
    for t in soup(["script", "style", "noscript", "nav", "footer"]):
        t.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for t in soup.find_all(BLOCK):
        t.append("\n")
    lines = [" ".join(l.split()) for l in soup.get_text("").split("\n")]
    text = "\n".join(l for l in lines if l)
    return dict(text=text, title=title, h1=h1, site_name=site_name, links=links)

def fetch(url):
    out = dict(url=url, ok=False, status=None, error=None, text="", title="", h1="",
               site_name="", links=[], content_hash=None)
    if not allowed(url):
        out["error"] = "blocked by robots.txt"
        return out
    _polite(urlparse(url).netloc)
    try:
        r = _get(url)
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    out["status"] = r.status_code
    if r.status_code != 200:
        out["error"] = f"HTTP {r.status_code}"
        return out
    if "html" not in r.headers.get("content-type", "").lower():
        out["error"] = "non-html content"
        return out
    out.update(parse_page(r.text, r.url))
    if len(out["text"]) < 1500 and re.search(r"page (was )?not found|404|no longer available|does not exist", out["text"], re.I):
        out["status"], out["error"] = 404, "soft 404"
        return out
    out["ok"] = True
    out["content_hash"] = hashlib.sha256(out["text"].encode()).hexdigest()
    return out

def url_alive(url):
    if not allowed(url):
        return None
    _polite(urlparse(url).netloc)
    try:
        return _get(url).status_code < 400
    except Exception:
        return False