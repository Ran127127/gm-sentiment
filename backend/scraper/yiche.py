"""
易车(yiche.com)抓取器
抓取策略：
  1. 易车新闻/文章搜索页面解析
  2. 通过搜索URL检索文章列表
  3. 详情页提取正文、互动数据、评论
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


class YicheScraper:
    """易车抓取器"""

    source_name = "yiche"
    BASE_URL = "https://www.yiche.com"
    NEWS_URL = "https://news.yiche.com"
    SEARCH_URL = "https://so.yiche.com"

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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _random_delay(self, min_s=1.5, max_s=4.0):
        time.sleep(random.uniform(min_s, max_s))

    def _get(self, url: str, params: dict = None, retries=3) -> httpx.Response | None:
        for attempt in range(retries):
            try:
                if self.ua:
                    self.client.headers["User-Agent"] = self.ua.random
                resp = self.client.get(url, params=params)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"[yiche] HTTP {resp.status_code}: {url}")
            except httpx.HTTPError as e:
                logger.warning(f"[yiche] 请求失败(第{attempt+1}次): {e}")
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
            logger.info(f"[yiche] 搜索品牌: {brand_name}")

            for page in range(1, max_pages + 1):
                if len(all_articles) >= max_articles:
                    break

                # 方式1: 搜索页
                articles = self._search_articles(brand_name, page)

                # 方式2: 如果搜索页无结果，尝试品牌新闻列表页
                if not articles and page == 1:
                    articles = self._scrape_brand_news(brand_name)

                all_articles.extend(articles)
                self._random_delay()

            if len(all_articles) >= max_articles:
                break

        logger.info(f"[yiche] 共抓取 {len(all_articles)} 篇文章")
        return all_articles[:max_articles]

    def _search_articles(self, keyword: str, page: int) -> list:
        """通过搜索页检索文章"""
        url = f"{self.SEARCH_URL}/article/"
        params = {
            "keyword": keyword,
            "page": page,
        }

        resp = self._get(url, params=params)
        if not resp:
            return []

        articles = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")

            # 易车搜索结果可能有SSR嵌入数据
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                for pattern in [
                    r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;',
                    r'window\.__DATA__\s*=\s*({.*?})\s*;',
                ]:
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            items = self._extract_items(data)
                            for item in items:
                                parsed = self._parse_item(item, keyword)
                                if parsed:
                                    articles.append(parsed)
                        except json.JSONDecodeError:
                            continue

            # 降级: 直接解析HTML
            if not articles:
                articles = self._parse_search_html(soup, keyword)

        except Exception as e:
            logger.error(f"[yiche] 搜索页解析失败: {e}")

        return articles

    def _scrape_brand_news(self, brand_name: str) -> list:
        """抓取品牌新闻列表页"""
        # 易车品牌新闻页URL模式
        brand_slug = {
            "别克": "buick",
            "凯迪拉克": "cadillac",
            "雪佛兰": "chevrolet",
        }.get(brand_name, "")

        if not brand_slug:
            return []

        url = f"{self.NEWS_URL}/{brand_slug}/"
        resp = self._get(url)
        if not resp:
            return []

        articles = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")

            # 新闻列表
            news_items = soup.select(
                "div.news-list li, div.article-list div.item, "
                "ul.list li, div[class*='news'] div[class*='item']"
            )

            for item in news_items:
                try:
                    title_tag = item.select_one("a h3, a h4, a[class*='title'], div.title a")
                    if not title_tag:
                        # 尝试直接找a标签
                        title_tag = item.select_one("a[href*='hao/wenzhang'], a[href*='news']")
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    link_tag = title_tag if title_tag.name == "a" else title_tag.find_parent("a")
                    if not link_tag:
                        link_tag = item.select_one("a[href]")
                    href = link_tag.get("href", "") if link_tag else ""
                    if href and not href.startswith("http"):
                        href = f"https:{href}" if href.startswith("//") else f"{self.NEWS_URL}{href}"

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

        except Exception as e:
            logger.error(f"[yiche] 品牌新闻页解析失败: {e}")

        return articles

    def _extract_items(self, data: dict) -> list:
        """从嵌入JSON中提取文章列表"""
        items = []

        def _walk(obj, depth=0):
            if depth > 10:
                return
            if isinstance(obj, dict):
                if "title" in obj and ("url" in obj or "id" in obj):
                    items.append(obj)
                    return
                for v in obj.values():
                    _walk(v, depth + 1)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v, depth + 1)

        _walk(data)
        return items

    def _parse_item(self, item: dict, keyword: str) -> dict | None:
        """解析文章数据项"""
        try:
            title = item.get("title", "")
            if not title:
                return None

            url = item.get("url", "") or item.get("link", "")
            if not url:
                aid = item.get("id", "")
                url = f"{self.NEWS_URL}/hao/wenzhang/{aid}/" if aid else ""

            brand_name = self._detect_brand(title) or keyword
            model_name = self._detect_model(title)
            content = item.get("content", "") or item.get("description", "") or item.get("summary", "")

            # 时间
            publish_time = None
            ts = item.get("publish_time") or item.get("create_time") or item.get("time", 0)
            if ts:
                try:
                    if isinstance(ts, (int, float)):
                        publish_time = datetime.fromtimestamp(int(ts))
                    else:
                        publish_time = self._parse_time(str(ts))
                except (ValueError, OSError, TypeError):
                    pass

            # 互动数据
            view_count = int(item.get("view_count", 0) or item.get("play_count", 0) or 0)
            like_count = int(item.get("like_count", 0) or item.get("praise_count", 0) or 0)
            comment_count = int(item.get("comment_count", 0) or 0)
            share_count = int(item.get("share_count", 0) or 0)

            # 抓取详情
            detail = self._scrape_detail(url) if url else None

            return {
                "source_name": self.source_name,
                "brand_name": brand_name,
                "model_name": model_name,
                "title": title,
                "content": detail.get("content", content) if detail else content,
                "summary": content[:100] + "..." if content else "",
                "url": url,
                "author": detail.get("author", "") if detail else (item.get("author", "") or ""),
                "publish_time": publish_time,
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "share_count": share_count,
                "comments": detail.get("comments", []) if detail else [],
            }
        except Exception as e:
            logger.debug(f"[yiche] 解析数据项失败: {e}")
            return None

    def _parse_search_html(self, soup: BeautifulSoup, keyword: str) -> list:
        """直接解析搜索结果HTML"""
        articles = []

        result_items = soup.select(
            "div.search-result div.item, "
            "div[class*='search'] div[class*='result-item'], "
            "div[class*='list'] div[class*='item'], "
            "a[href*='hao/wenzhang'], a[href*='/news/']"
        )

        for item in result_items:
            try:
                if item.name == "a":
                    title = item.get_text(strip=True)
                    href = item.get("href", "")
                    if not title or len(title) < 5:
                        continue
                else:
                    title_tag = item.select_one("a h3, a h4, a[class*='title'], div.title a, a")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get("href", "") if title_tag.name == "a" else ""
                    if not href:
                        parent_a = title_tag.find_parent("a")
                        href = parent_a.get("href", "") if parent_a else ""

                if href and not href.startswith("http"):
                    href = f"https:{href}" if href.startswith("//") else f"{self.NEWS_URL}{href}"

                articles.append({
                    "source_name": self.source_name,
                    "brand_name": self._detect_brand(title) or keyword,
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
                "div.content-detail, div.detail-content, "
                "div[class*='post-content']"
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
                "a[class*='name'], div.source-name"
            )
            result["author"] = author_tag.get_text(strip=True) if author_tag else ""

            # 发布时间
            time_tag = soup.select_one(
                "span[class*='time'], span[class*='date'], "
                "em[class*='time'], time"
            )
            if time_tag:
                result["publish_time"] = self._parse_time(
                    time_tag.get_text(strip=True)
                )

            # 浏览数
            view_tag = soup.select_one(
                "span[class*='view'], span[class*='read'], "
                "em[class*='view']"
            )
            result["view_count"] = self._parse_number(
                view_tag.get_text(strip=True) if view_tag else "0"
            )

            result["like_count"] = 0
            result["share_count"] = 0

            # 评论
            result["comments"] = self._scrape_comments(soup)

            return result

        except Exception as e:
            logger.debug(f"[yiche] 详情页解析失败: {e}")
            return None

    def _scrape_comments(self, soup: BeautifulSoup) -> list:
        """提取评论"""
        comments = []
        comment_items = soup.select(
            "div.comment-item, div[class*='comment'] div[class*='item'], "
            "ul.comment-list li, div[class*='reply-item']"
        )

        for item in comment_items[:10]:
            try:
                content_tag = item.select_one(
                    "p, span[class*='content'], div[class*='text']"
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

    def _parse_time(self, time_str: str) -> datetime | None:
        if not time_str:
            return None
        time_str = time_str.strip()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        if "分钟前" in time_str:
            minutes = int(re.search(r"(\d+)", time_str).group(1))
            from datetime import timedelta
            return datetime.now() - timedelta(minutes=minutes)
        if "小时前" in time_str:
            hours = int(re.search(r"(\d+)", time_str).group(1))
            from datetime import timedelta
            return datetime.now() - timedelta(hours=hours)
        if "天前" in time_str:
            days = int(re.search(r"(\d+)", time_str).group(1))
            from datetime import timedelta
            return datetime.now() - timedelta(days=days)

        return None

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
