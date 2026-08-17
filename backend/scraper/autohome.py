"""
汽车之家(autohome.com.cn)抓取器
抓取策略：
  1. 通过搜索接口按品牌/车型关键词检索文章
  2. 解析搜索结果页HTML提取文章列表
  3. 逐篇进入详情页获取正文、浏览数、评论数等
  4. 抓取文章评论区前N条评论
"""
import re
import time
import random
import logging
from datetime import datetime
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# GM China 品牌及车型关键词
BRAND_KEYWORDS = {
    "别克": ["别克", "君越", "君威", "GL8", "昂科威", "微蓝"],
    "凯迪拉克": ["凯迪拉克", "CT5", "CT4", "XT5", "XT4", "锐歌", "LYRIQ"],
    "雪佛兰": ["雪佛兰", "迈锐宝", "科鲁泽", "创界", "星迈罗", "开拓者"],
}

# 车型名 → 品牌名的反向映射
MODEL_TO_BRAND = {}
for brand, kws in BRAND_KEYWORDS.items():
    for kw in kws:
        MODEL_TO_BRAND[kw] = brand

# 车型名列表（用于匹配文章中的车型）
ALL_MODEL_NAMES = []
for brand, info in [
    ("别克", ["君越", "君威", "GL8", "昂科威Plus", "微蓝6"]),
    ("凯迪拉克", ["CT5", "CT4", "XT5", "XT4", "LYRIQ锐歌"]),
    ("雪佛兰", ["迈锐宝XL", "科鲁泽", "创界", "星迈罗", "开拓者"]),
]:
    for m in info:
        ALL_MODEL_NAMES.append((m, brand))


class AutohomeScraper:
    """汽车之家抓取器"""

    source_name = "autohome"
    BASE_URL = "https://so.autohome.com.cn"
    ARTICLE_BASE = "https://club.autohome.com.cn"

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
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _random_delay(self, min_s=1.5, max_s=4.0):
        """随机延迟，避免触发反爬"""
        time.sleep(random.uniform(min_s, max_s))

    def _get(self, url: str, retries=3) -> httpx.Response | None:
        """带重试的GET请求"""
        for attempt in range(retries):
            try:
                # 每次请求刷新UA
                self.client.headers["User-Agent"] = (
                    self.ua.random if self.ua else
                    self.client.headers["User-Agent"]
                )
                resp = self.client.get(url)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"[autohome] HTTP {resp.status_code}: {url}")
            except httpx.HTTPError as e:
                logger.warning(f"[autohome] 请求失败(第{attempt+1}次): {e}")
            self._random_delay(2, 5)
        return None

    def scrape(self, **kwargs) -> list:
        """
        执行抓取，返回文章数据列表。
        kwargs:
            max_pages: 每个关键词最大搜索页数 (默认2)
            max_articles: 最大文章总数 (默认30)
        """
        max_pages = kwargs.get("max_pages", 2)
        max_articles = kwargs.get("max_articles", 30)
        all_articles = []

        # 遍历品牌关键词搜索
        for brand_name, keywords in BRAND_KEYWORDS.items():
            # 用品牌主关键词搜索
            search_kw = brand_name
            logger.info(f"[autohome] 搜索关键词: {search_kw}")

            for page in range(1, max_pages + 1):
                if len(all_articles) >= max_articles:
                    break

                articles = self._search_page(search_kw, page, brand_name)
                all_articles.extend(articles)
                self._random_delay()

            if len(all_articles) >= max_articles:
                break

        logger.info(f"[autohome] 共抓取 {len(all_articles)} 篇文章")
        return all_articles[:max_articles]

    def _search_page(self, keyword: str, page: int, brand_name: str) -> list:
        """解析搜索结果页"""
        url = f"{self.BASE_URL}/article?q={quote(keyword)}&page={page}"
        resp = self._get(url)
        if not resp:
            return []

        articles = []
        try:
            soup = BeautifulSoup(resp.text, "lxml")

            # 汽车之家搜索结果在 div.search-result-list 或类似容器中
            # 实际选择器需要根据页面结构调整，这里覆盖多种可能的结构
            result_items = soup.select(
                "div.search-result-list div.result-item, "
                "div.search-list div.item, "
                "div.article-list div.article-item, "
                "div.search-result div.search-item"
            )

            if not result_items:
                # 备用：尝试查找所有包含文章链接的区块
                result_items = soup.select("div[class*='result'] a[href*='thread']")
                # 包装成伪item
                result_items = [a.parent for a in result_items if a.parent]

            for item in result_items:
                article_data = self._parse_search_item(item, brand_name)
                if article_data:
                    articles.append(article_data)

        except Exception as e:
            logger.error(f"[autohome] 解析搜索结果页失败: {e}")

        return articles

    def _parse_search_item(self, item, brand_name: str) -> dict | None:
        """从搜索结果项中提取文章数据"""
        try:
            # 提取标题和链接
            title_tag = item.select_one(
                "a.title, h3 a, a[class*='title'], "
                "div.title a, a[href*='thread']"
            )
            if not title_tag:
                return None

            title = title_tag.get_text(strip=True)
            if not title or len(title) < 5:
                return None

            href = title_tag.get("href", "")
            if href and not href.startswith("http"):
                href = urljoin(self.ARTICLE_BASE, href)

            # 过滤非GM品牌文章
            if not self._is_gm_related(title):
                return None

            # 识别车型
            model_name = self._detect_model(title)

            # 提取摘要
            summary_tag = item.select_one(
                "p.summary, p.desc, div.summary, "
                "p[class*='desc'], p[class*='summary']"
            )
            summary = summary_tag.get_text(strip=True) if summary_tag else ""

            # 提取发布时间
            time_tag = item.select_one(
                "span.time, span.date, time, "
                "span[class*='time'], span[class*='date']"
            )
            publish_time = self._parse_time(
                time_tag.get_text(strip=True) if time_tag else ""
            )

            # 尝试获取详情页的更多信息
            if href and "thread" in href:
                detail = self._scrape_article_detail(href)
                if detail:
                    return {
                        "source_name": self.source_name,
                        "brand_name": brand_name,
                        "model_name": model_name,
                        "title": title,
                        "content": detail.get("content", ""),
                        "summary": summary or detail.get("content", "")[:100] + "...",
                        "url": href,
                        "author": detail.get("author", ""),
                        "publish_time": publish_time or detail.get("publish_time"),
                        "view_count": detail.get("view_count", 0),
                        "like_count": detail.get("like_count", 0),
                        "comment_count": detail.get("comment_count", 0),
                        "share_count": detail.get("share_count", 0),
                        "comments": detail.get("comments", []),
                    }

            # 如果详情页抓取失败，仍返回基本信息
            return {
                "source_name": self.source_name,
                "brand_name": brand_name,
                "model_name": model_name,
                "title": title,
                "content": summary,
                "summary": summary[:100] + "..." if summary else "",
                "url": href,
                "author": "",
                "publish_time": publish_time,
                "view_count": 0,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "comments": [],
            }

        except Exception as e:
            logger.debug(f"[autohome] 解析搜索结果项失败: {e}")
            return None

    def _scrape_article_detail(self, url: str) -> dict | None:
        """抓取文章详情页，获取正文、浏览数、评论等"""
        self._random_delay(1, 3)
        resp = self._get(url)
        if not resp:
            return None

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            result = {}

            # 正文内容
            content_div = soup.select_one(
                "div#contents, div.article-content, "
                "div.post_content, div[class*='content']"
            )
            if content_div:
                # 提取纯文本，保留段落结构
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
                "a[class*='author'], span[class*='author'], "
                "div.author a, div.poster-name"
            )
            result["author"] = (
                author_tag.get_text(strip=True) if author_tag else ""
            )

            # 发布时间
            time_tag = soup.select_one(
                "span[class*='time'], em[class*='time'], "
                "div.publish-time, span.pub-time"
            )
            result["publish_time"] = self._parse_time(
                time_tag.get_text(strip=True) if time_tag else ""
            )

            # 浏览数
            view_tag = soup.select_one(
                "span[class*='view'], em[class*='view'], "
                "span.visit-count"
            )
            result["view_count"] = self._parse_number(
                view_tag.get_text(strip=True) if view_tag else "0"
            )

            # 评论数
            comment_tag = soup.select_one(
                "span[class*='comment'], em[class*='reply']"
            )
            result["comment_count"] = self._parse_number(
                comment_tag.get_text(strip=True) if comment_tag else "0"
            )

            result["like_count"] = 0
            result["share_count"] = 0

            # 抓取评论
            result["comments"] = self._scrape_comments(soup)

            return result

        except Exception as e:
            logger.error(f"[autohome] 解析文章详情失败: {e}")
            return None

    def _scrape_comments(self, soup: BeautifulSoup) -> list:
        """从详情页提取评论"""
        comments = []
        comment_items = soup.select(
            "div.comment-item, div.reply-item, "
            "div[class*='comment'] div.item, "
            "ul.comment-list li"
        )

        for item in comment_items[:10]:  # 最多取10条
            try:
                content_tag = item.select_one(
                    "p.comment-content, div.content, "
                    "span[class*='content'], p"
                )
                author_tag = item.select_one(
                    "a[class*='user'], span[class*='name'], "
                    "div.author a"
                )
                like_tag = item.select_one(
                    "span[class*='like'], span[class*='agree']"
                )

                content = (
                    content_tag.get_text(strip=True) if content_tag else ""
                )
                if not content:
                    continue

                comments.append({
                    "content": content,
                    "author": (
                        author_tag.get_text(strip=True) if author_tag else ""
                    ),
                    "like_count": self._parse_number(
                        like_tag.get_text(strip=True) if like_tag else "0"
                    ),
                })
            except Exception:
                continue

        return comments

    def _is_gm_related(self, text: str) -> bool:
        """判断文本是否与GM品牌相关"""
        gm_keywords = [
            "别克", "凯迪拉克", "雪佛兰",
            "君越", "君威", "GL8", "昂科威", "微蓝",
            "CT5", "CT4", "XT5", "XT4", "锐歌",
            "迈锐宝", "科鲁泽", "创界", "星迈罗", "开拓者",
        ]
        return any(kw in text for kw in gm_keywords)

    def _detect_model(self, text: str) -> str:
        """从文本中检测提到的车型"""
        # 按名称长度降序排列，优先匹配更具体的车型名
        sorted_models = sorted(ALL_MODEL_NAMES, key=lambda x: len(x[0]), reverse=True)
        for model_name, brand in sorted_models:
            if model_name in text:
                return model_name
        return ""

    def _parse_time(self, time_str: str) -> datetime | None:
        """解析各种格式的时间字符串"""
        if not time_str:
            return None
        time_str = time_str.strip()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%m月%d日 %H:%M",
            "%m月%d日",
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                # 补全年份
                if parsed.year == 1900:
                    parsed = parsed.replace(year=datetime.now().year)
                return parsed
            except ValueError:
                continue

        # 处理相对时间
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
        if "昨天" in time_str:
            from datetime import timedelta
            return datetime.now() - timedelta(days=1)
        if "今天" in time_str:
            return datetime.now()

        return None

    @staticmethod
    def _parse_number(text: str) -> int:
        """从文本中提取数字"""
        if not text:
            return 0
        text = text.strip().replace(",", "").replace(" ", "")
        # 处理 "1.2万" 这类写法
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return 0
        match = re.search(r"[\d]+", text)
        return int(match.group()) if match else 0

    def close(self):
        self.client.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
