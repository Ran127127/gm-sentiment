"""
懂车帝(dongchedi.com)抓取器
抓取策略：
  1. 懂车帝搜索页为SSR渲染，通过解析HTML获取初始数据
  2. 同时尝试其内部API接口（返回JSON）
  3. 文章详情页通过URL直接抓取正文和评论
"""
import re
import json
import time
import random
import logging
from datetime import datetime
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

BRAND_KEYWORDS = {
    "别克": ["别克", "君越", "君威", "GL8", "昂科威", "微蓝"],
    "凯迪拉克": ["凯迪拉克", "CT5", "CT4", "XT5", "XT4", "锐歌", "LYRIQ"],
    "雪佛兰": ["雪佛兰", "迈锐宝", "科鲁泽", "创界", "星迈罗", "开拓者"],
}

ALL_MODEL_NAMES = []
for brand, info in [
    ("别克", ["君越", "君威", "GL8", "昂科威Plus", "微蓝6"]),
    ("凯迪拉克", ["CT5", "CT4", "XT5", "XT4", "LYRIQ锐歌"]),
    ("雪佛兰", ["迈锐宝XL", "科鲁泽", "创界", "星迈罗", "开拓者"]),
]:
    for m in info:
        ALL_MODEL_NAMES.append((m, brand))


class DongchediScraper:
    """懂车帝抓取器"""

    source_name = "dongchedi"
    BASE_URL = "https://www.dongchedi.com"
    SEARCH_URL = "https://www.dongchedi.com/search"
    # 懂车帝内部搜索API（PC端）
    API_SEARCH_URL = "https://www.dongchedi.com/motor/search/api/pc/search"

    def __init__(self):
        try:
            self.ua = UserAgent()
        except Exception:
            self.ua = None
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=self._default_headers(),
        )

    def _default_headers(self):
        ua_string = self.ua.random if self.ua else (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        return {
            "User-Agent": ua_string,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.dongchedi.com/",
            "Connection": "keep-alive",
        }

    def _random_delay(self, min_s=2.0, max_s=5.0):
        time.sleep(random.uniform(min_s, max_s))

    def _get(self, url: str, params: dict = None, retries=3) -> httpx.Response | None:
        for attempt in range(retries):
            try:
                if self.ua:
                    self.client.headers["User-Agent"] = self.ua.random
                resp = self.client.get(url, params=params)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"[dongchedi] HTTP {resp.status_code}: {url}")
            except httpx.HTTPError as e:
                logger.warning(f"[dongchedi] 请求失败(第{attempt+1}次): {e}")
            self._random_delay(2, 5)
        return None

    def scrape(self, **kwargs) -> list:
        """
        执行抓取。
        kwargs:
            max_pages: 每个关键词最大搜索页数 (默认2)
            max_articles: 最大文章总数 (默认30)
        """
        max_pages = kwargs.get("max_pages", 2)
        max_articles = kwargs.get("max_articles", 30)
        all_articles = []

        for brand_name in BRAND_KEYWORDS:
            logger.info(f"[dongchedi] 搜索品牌: {brand_name}")

            for page in range(1, max_pages + 1):
                if len(all_articles) >= max_articles:
                    break

                # 优先尝试API方式
                articles = self._search_via_api(brand_name, page)
                if not articles:
                    # 降级到HTML解析
                    articles = self._search_via_html(brand_name, page, brand_name)

                all_articles.extend(articles)
                self._random_delay()

            if len(all_articles) >= max_articles:
                break

        logger.info(f"[dongchedi] 共抓取 {len(all_articles)} 篇文章")
        return all_articles[:max_articles]

    def _search_via_api(self, keyword: str, page: int) -> list:
        """通过懂车帝内部API搜索（返回JSON）"""
        params = {
            "keyword": keyword,
            "search_source": "pc_search",
            "search_id": "",
            "type": "article",
            "count": 20,
            "offset": (page - 1) * 20,
        }

        resp = self._get(self.API_SEARCH_URL, params=params)
        if not resp:
            return []

        articles = []
        try:
            data = resp.json()
            items = (
                data.get("data", {}).get("list", [])
                or data.get("data", {}).get("articles", [])
                or data.get("data", {}).get("result", {}).get("list", [])
            )

            for item in items:
                article_data = self._parse_api_item(item)
                if article_data:
                    articles.append(article_data)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"[dongchedi] API解析失败: {e}")

        return articles

    def _parse_api_item(self, item: dict) -> dict | None:
        """解析API返回的文章数据项"""
        try:
            title = item.get("title", "")
            if not title:
                return None

            # 文章URL
            article_id = item.get("id") or item.get("article_id") or item.get("group_id", "")
            url = f"{self.BASE_URL}/article/{article_id}" if article_id else ""
            if not url:
                return None

            # 品牌识别
            brand_name = self._detect_brand(title)
            model_name = self._detect_model(title)

            # 正文/摘要
            content = item.get("content", "") or item.get("abstract", "") or item.get("summary", "")
            summary = item.get("abstract", "") or content[:100]

            # 作者
            author_info = item.get("author", {}) or item.get("user", {}) or {}
            author = author_info.get("name", "") or author_info.get("screen_name", "")

            # 时间
            pub_ts = item.get("publish_time") or item.get("create_time") or 0
            publish_time = None
            if pub_ts:
                try:
                    publish_time = datetime.fromtimestamp(int(pub_ts))
                except (ValueError, OSError, TypeError):
                    pass

            # 互动数据
            stats = item.get("stats", {}) or item.get("statistics", {}) or {}
            view_count = int(stats.get("read_count", 0) or stats.get("view_count", 0) or item.get("read_count", 0))
            like_count = int(stats.get("like_count", 0) or stats.get("digg_count", 0) or item.get("like_count", 0))
            comment_count = int(stats.get("comment_count", 0) or item.get("comment_count", 0))
            share_count = int(stats.get("share_count", 0) or item.get("share_count", 0))

            # 抓取详情和评论
            detail = self._scrape_detail(url)

            return {
                "source_name": self.source_name,
                "brand_name": brand_name,
                "model_name": model_name,
                "title": title,
                "content": detail.get("content", content) if detail else content,
                "summary": summary[:100] + "..." if summary else "",
                "url": url,
                "author": detail.get("author", author) if detail else author,
                "publish_time": publish_time,
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "share_count": share_count,
                "comments": detail.get("comments", []) if detail else [],
            }

        except Exception as e:
            logger.debug(f"[dongchedi] 解析API数据项失败: {e}")
            return None

    def _search_via_html(self, keyword: str, page: int, brand_name: str) -> list:
        """通过HTML解析搜索结果页（降级方案）"""
        url = f"{self.SEARCH_URL}?keyword={quote(keyword)}&type=article&pd=information&source=pc_search&page={page}"
        resp = self._get(url)
        if not resp:
            return []

        articles = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")

            # 懂车帝SSR页面通常在 <script> 中嵌入JSON数据
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                # 查找 window.__INITIAL_DATA__ 或类似变量
                for pattern in [
                    r'window\.__INITIAL_DATA__\s*=\s*({.*?})\s*;',
                    r'window\.__SSR_DATA__\s*=\s*({.*?})\s*;',
                    r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*;',
                ]:
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            items = self._extract_items_from_ssr(data)
                            for item in items:
                                parsed = self._parse_api_item(item)
                                if parsed:
                                    articles.append(parsed)
                        except json.JSONDecodeError:
                            continue

            # 如果SSR数据提取失败，尝试直接解析HTML
            if not articles:
                articles = self._parse_search_html(soup, brand_name)

        except Exception as e:
            logger.error(f"[dongchedi] HTML解析失败: {e}")

        return articles

    def _extract_items_from_ssr(self, data: dict) -> list:
        """从SSR嵌入的JSON数据中提取文章列表"""
        # 递归搜索包含文章数据的节点
        items = []

        def _walk(obj, depth=0):
            if depth > 10:
                return
            if isinstance(obj, dict):
                # 检查是否是文章对象
                if "title" in obj and ("id" in obj or "article_id" in obj or "group_id" in obj):
                    items.append(obj)
                    return
                for v in obj.values():
                    _walk(v, depth + 1)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v, depth + 1)

        _walk(data)
        return items

    def _parse_search_html(self, soup: BeautifulSoup, brand_name: str) -> list:
        """直接解析搜索结果HTML"""
        articles = []
        result_items = soup.select(
            "div.search-result-item, div[class*='search'] div[class*='item'], "
            "div[class*='result'] div[class*='card'], "
            "a[href*='/article/']"
        )

        for item in result_items:
            try:
                # 提取标题
                title_tag = item.select_one(
                    "h3, div.title, span.title, "
                    "div[class*='title']"
                )
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title or len(title) < 5:
                    # 如果item本身是a标签
                    if item.name == "a" and "/article/" in item.get("href", ""):
                        title = item.get_text(strip=True)
                    if not title:
                        continue

                # 提取链接
                link_tag = item.select_one("a[href*='/article/']") or (
                    item if item.name == "a" and "/article/" in item.get("href", "") else None
                )
                href = link_tag.get("href", "") if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"{self.BASE_URL}{href}"

                articles.append({
                    "source_name": self.source_name,
                    "brand_name": brand_name,
                    "model_name": self._detect_model(title),
                    "title": title,
                    "content": "",
                    "summary": "",
                    "url": href,
                    "author": "",
                    "publish_time": None,
                    "view_count": 0,
                    "like_count": 0,
                    "comment_count": 0,
                    "share_count": 0,
                    "comments": [],
                })
            except Exception:
                continue

        return articles

    def _scrape_detail(self, url: str) -> dict | None:
        """抓取文章详情页"""
        self._random_delay(1.5, 3.5)
        resp = self._get(url)
        if not resp:
            return None

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            result = {}

            # 正文
            content_div = soup.select_one(
                "div.article-content, div[class*='article'] div[class*='content'], "
                "div.detail-content, div.main-content"
            )
            if content_div:
                paragraphs = content_div.find_all("p")
                if paragraphs:
                    result["content"] = "\n".join(
                        p.get_text(strip=True) for p in paragraphs
                        if p.get_text(strip=True)
                    )
                else:
                    result["content"] = content_div.get_text(separator="\n", strip=True)

            # 作者
            author_tag = soup.select_one(
                "span[class*='author'], div[class*='author'] a, "
                "a[class*='name']"
            )
            result["author"] = author_tag.get_text(strip=True) if author_tag else ""

            # 评论
            result["comments"] = self._scrape_comments(soup)

            return result

        except Exception as e:
            logger.debug(f"[dongchedi] 详情页解析失败: {e}")
            return None

    def _scrape_comments(self, soup: BeautifulSoup) -> list:
        """提取评论"""
        comments = []
        comment_items = soup.select(
            "div.comment-item, div[class*='comment'] div[class*='item'], "
            "div[class*='reply'] div[class*='content']"
        )

        for item in comment_items[:10]:
            try:
                content_tag = item.select_one(
                    "p, span[class*='content'], "
                    "div[class*='text']"
                )
                content = content_tag.get_text(strip=True) if content_tag else ""
                if not content:
                    continue

                author_tag = item.select_one(
                    "span[class*='name'], a[class*='user']"
                )
                like_tag = item.select_one(
                    "span[class*='like'], span[class*='count']"
                )

                comments.append({
                    "content": content,
                    "author": author_tag.get_text(strip=True) if author_tag else "",
                    "like_count": self._parse_number(
                        like_tag.get_text(strip=True) if like_tag else "0"
                    ),
                })
            except Exception:
                continue

        return comments

    def _detect_brand(self, text: str) -> str:
        for brand, keywords in BRAND_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return brand
        return ""

    def _detect_model(self, text: str) -> str:
        sorted_models = sorted(ALL_MODEL_NAMES, key=lambda x: len(x[0]), reverse=True)
        for model_name, brand in sorted_models:
            if model_name in text:
                return model_name
        return ""

    @staticmethod
    def _parse_number(text: str) -> int:
        if not text:
            return 0
        text = text.strip().replace(",", "").replace(" ", "")
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return 0
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0

    def close(self):
        self.client.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
