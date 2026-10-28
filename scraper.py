import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "CreatorSourcingTool/1.0 (contact: your@email.com)"
DEFAULT_DELAY = 2.0  # 秒，每次请求之间的间隔
TIMEOUT = 10


class ComplianceScraper:
    """合规公开网页爬虫：遵守 robots.txt、限速、不抓 PII。"""

    def __init__(self, user_agent: str = USER_AGENT, delay: float = DEFAULT_DELAY):
        self.user_agent = user_agent
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    # ---------- robots.txt 检查 ----------
    def _can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            # robots.txt 读不到时，保守跳过
            return False
        return rp.can_fetch(self.user_agent, url)

    # ---------- 单页抓取 ----------
    def fetch(self, url: str):
        if not self._can_fetch(url):
            return {"url": url, "error": "robots.txt 不允许抓取"}
        time.sleep(self.delay)  # 礼貌限速
        try:
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return {"url": url, "html": resp.text, "status": resp.status_code}
        except Exception as e:
            return {"url": url, "error": str(e)}

    # ---------- 提取公开元数据（不含 PII） ----------
    def extract_public_meta(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "html.parser")

        # 标题
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

        # Open Graph 信息（很多创作者页用 og 标签）
        og_title = ""
        og_desc = ""
        og_image = ""
        og_tag = soup.find("meta", attrs={"property": "og:title"})
        if og_tag:
            og_title = og_tag.get("content", "").strip()
        og_desc_tag = soup.find("meta", attrs={"property": "og:description"})
        if og_desc_tag:
            og_desc = og_desc_tag.get("content", "").strip()
        og_img_tag = soup.find("meta", attrs={"property": "og:image"})
        if og_img_tag:
            og_image = og_img_tag.get("content", "").strip()

        # 页面可见文字的前 500 字（用于关键词匹配，不存个资）
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body_text = " ".join(soup.get_text(separator=" ").split())[:500]

        # 同域链接（用于发现更多公开页面）
        internal_links = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(base_url, a["href"])
            if urlparse(full).netloc == urlparse(base_url).netloc:
                internal_links.add(full)

        return {
            "page_title": title,
            "meta_description": description,
            "og_title": og_title,
            "og_description": og_desc,
            "og_image": og_image,
            "body_excerpt": body_text,
            "internal_links": list(internal_links)[:30],  # 最多 30 条
        }

    # ---------- 一站式抓取 ----------
    def scrape_page(self, url: str):
        result = self.fetch(url)
        if "html" not in result:
            return result
        meta = self.extract_public_meta(result["html"], url)
        return {"url": url, **meta}
