"""
Compliance-first public web scraper.

Rules:
- Only public HTTP/HTTPS pages.
- Respect robots.txt (cached per host, 4xx vs 5xx distinction).
- Rate limit between requests.
- Reject private / loopback / link-local / reserved addresses (SSRF protection).
- Re-check the final URL after redirects.
- Cap response size and require HTML content type.
- Extract only public metadata; do not store PII.
"""

import ipaddress
import socket
import time
import urllib.robotparser
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "CreatorSourcingTool/1.0 (contact: your@email.com)"
DEFAULT_DELAY = 2.0            # seconds between requests
TIMEOUT = 10                   # seconds per request
MAX_HTML_BYTES = 2_000_000     # 2 MB cap
MAX_EXCERPT_CHARS = 500
MAX_INTERNAL_LINKS = 30
ALLOWED_SCHEMES = {"http", "https"}


class ComplianceScraper:
    """Compliant public web scraper: respects robots.txt, rate limits, no PII."""

    def __init__(self, user_agent: str = USER_AGENT, delay: float = DEFAULT_DELAY):
        self.user_agent = user_agent
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        # Cache robots.txt per host to avoid repeated fetches within a batch.
        self._robots_cache: dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

    # ---------- URL / SSRF protection ----------
    @staticmethod
    def _is_public_url(url: str) -> bool:
        """Return True only for public HTTP(S) URLs that resolve to public IPs."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        if parsed.scheme not in ALLOWED_SCHEMES:
            return False
        if not parsed.hostname:
            return False

        host = parsed.hostname

        # Reject obvious local names
        if host == "localhost" or host.endswith(".local"):
            return False

        # Resolve all A/AAAA records and reject any non-public IP
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False

        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except ValueError:
                return False
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False
        return True

    # ---------- robots.txt (cached per host) ----------
    def _robots_for(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"

        if host_key in self._robots_cache:
            return self._robots_cache[host_key]

        robots_url = f"{host_key}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)

        try:
            resp = self.session.get(robots_url, timeout=TIMEOUT)

            if resp.status_code >= 500:
                # 5xx: be conservative, treat as disallow-all
                self._robots_cache[host_key] = None
                return None

            if resp.status_code >= 400:
                # 4xx (except 429): no robots.txt -> allow all
                rp.parse([])
            else:
                rp.parse(resp.text.splitlines())

            self._robots_cache[host_key] = rp
            return rp

        except requests.RequestException:
            # Network error: conservative
            self._robots_cache[host_key] = None
            return None

    def _can_fetch(self, url: str) -> bool:
        rp = self._robots_for(url)
        if rp is None:
            return False
        return rp.can_fetch(self.user_agent, url)

    # ---------- fetch ----------
    def fetch(self, url: str) -> dict:
        if not self._is_public_url(url):
            return {"url": url, "error": "URL rejected (scheme or host not allowed)"}

        if not self._can_fetch(url):
            return {"url": url, "error": "Blocked by robots.txt"}

        time.sleep(self.delay)  # polite rate limit

        try:
            resp = self.session.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True,
            )
        except requests.RequestException as e:
            return {"url": url, "error": f"Request failed: {e}"}

        # Final URL after redirects must also pass SSRF and robots checks
        final_url = resp.url
        if not self._is_public_url(final_url):
            resp.close()
            return {"url": url, "error": "Redirected to a disallowed host"}

        if final_url != url and not self._can_fetch(final_url):
            resp.close()
            return {"url": url, "error": "Redirected to a page blocked by robots.txt"}

        if resp.status_code >= 400:
            resp.close()
            return {"url": url, "error": f"HTTP {resp.status_code}"}

        content_type = resp.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            resp.close()
            return {"url": url, "error": f"Not an HTML page ({content_type or 'unknown'})"}

        # Cap response size
        chunks = []
        total = 0
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                total += len(chunk)
                if total > MAX_HTML_BYTES:
                    break
                chunks.append(chunk)
        finally:
            resp.close()

        encoding = resp.encoding or "utf-8"
        html = b"".join(chunks).decode(encoding, errors="replace")

        return {
            "url": url,
            "final_url": final_url,
            "html": html,
            "status": resp.status_code,
        }

    # ---------- extract public metadata (no PII) ----------
    def extract_public_meta(self, html: str, base_url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        # Title (handle nested tags inside <title>)
        title = soup.title.get_text(strip=True) if soup.title else ""

        def meta_content(attr: str, value: str) -> str:
            tag = soup.find("meta", attrs={attr: value})
            if tag and tag.get("content"):
                return tag["content"].strip()
            return ""

        description = meta_content("name", "description")
        og_title = meta_content("property", "og:title")
        og_description = meta_content("property", "og:description")
        og_image = meta_content("property", "og:image")

        # Collect internal links BEFORE stripping tags
        base_netloc = urlparse(base_url).netloc
        internal_links: list[str] = []
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            full = urljoin(base_url, a["href"])
            parsed = urlparse(full)

            if parsed.scheme not in ALLOWED_SCHEMES:
                continue
            if parsed.netloc != base_netloc:
                continue

            normalized = parsed._replace(fragment="").geturl()
            if normalized in seen:
                continue

            seen.add(normalized)
            internal_links.append(normalized)

            if len(internal_links) >= MAX_INTERNAL_LINKS:
                break

        # Visible text excerpt (strip noisy tags first)
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        body_text = " ".join(soup.get_text(separator=" ").split())[:MAX_EXCERPT_CHARS]

        return {
            "page_title": title,
            "meta_description": description,
            "og_title": og_title,
            "og_description": og_description,
            "og_image": og_image,
            "body_excerpt": body_text,
            "internal_links": internal_links,
        }

    # ---------- one-shot ----------
    def scrape_page(self, url: str) -> dict:
        result = self.fetch(url)
        if "html" not in result:
            return result
        meta = self.extract_public_meta(result["html"], result.get("final_url", url))
        return {"url": url, **meta}
