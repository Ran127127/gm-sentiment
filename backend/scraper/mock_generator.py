"""
Mock数据生成器 —— 生成逼真的中文汽车舆情数据用于开发和演示
"""
import random
from datetime import date, timedelta, datetime

# GM China 品牌与车型
BRAND_MODELS = {
    "别克": {
        "id": 1,
        "models": [
            {"name_cn": "君越", "name_en": "LaCrosse", "category": "sedan"},
            {"name_cn": "君威", "name_en": "Regal", "category": "sedan"},
            {"name_cn": "GL8", "name_en": "GL8", "category": "mpv"},
            {"name_cn": "昂科威Plus", "name_en": "Envision Plus", "category": "suv"},
            {"name_cn": "微蓝6", "name_en": "Velite 6", "category": "sedan"},
        ],
    },
    "凯迪拉克": {
        "id": 2,
        "models": [
            {"name_cn": "CT5", "name_en": "CT5", "category": "sedan"},
            {"name_cn": "CT4", "name_en": "CT4", "category": "sedan"},
            {"name_cn": "XT5", "name_en": "XT5", "category": "suv"},
            {"name_cn": "XT4", "name_en": "XT4", "category": "suv"},
            {"name_cn": "LYRIQ锐歌", "name_en": "LYRIQ", "category": "suv"},
        ],
    },
    "雪佛兰": {
        "id": 3,
        "models": [
            {"name_cn": "迈锐宝XL", "name_en": "Malibu XL", "category": "sedan"},
            {"name_cn": "科鲁泽", "name_en": "Monza", "category": "sedan"},
            {"name_cn": "创界", "name_en": "Trailblazer", "category": "suv"},
            {"name_cn": "星迈罗", "name_en": "Equinox", "category": "suv"},
            {"name_cn": "开拓者", "name_en": "Blazer", "category": "suv"},
        ],
    },
}

# 数据源
DATA_SOURCES = [
    {"name": "weibo", "display_name": "微博", "source_type": "social_media", "base_url": "https://weibo.com"},
    {"name": "autohome", "display_name": "汽车之家", "source_type": "auto_media", "base_url": "https://www.autohome.com.cn"},
    {"name": "dongchedi", "display_name": "懂车帝", "source_type": "auto_media", "base_url": "https://www.dongchedi.com"},
    {"name": "yiche", "display_name": "易车", "source_type": "auto_media", "base_url": "https://www.yiche.com"},
    {"name": "xiaohongshu", "display_name": "小红书", "source_type": "social_media", "base_url": "https://www.xiaohongshu.com"},
    {"name": "douyin", "display_name": "抖音", "source_type": "social_media", "base_url": "https://www.douyin.com"},
]

# 文章标题模板
TITLE_TEMPLATES = {
    "positive": [
        "试驾{model}：{aspect}表现令人惊喜",
        "{model}提车一个月真实感受，{aspect}真的香",
        "对比了三款车，最终选了{model}，说说原因",
        "{model}跑了一万公里，聊聊最满意的几个点",
        "为什么{model}是这个级别最值得买的车？",
        "{brand}{model}深度体验：{aspect}超出预期",
        "入手{model}半年，这些优点不得不说",
        "{model}车主真实口碑：{aspect}给满分",
        "全新{model}静态体验，{aspect}是最大亮点",
        "{brand}这次真的用心了，{model}{aspect}太赞",
    ],
    "negative": [
        "{model}开了三个月，说说最不满意的地方",
        "买{model}后悔了吗？车主说出真实感受",
        "{model}的{aspect}真的让人无语",
        "对比竞品后，{model}的{aspect}差距明显",
        "{model}车主吐槽：{aspect}是硬伤",
        "不建议买{model}，{aspect}体验太差",
        "{brand}{model}降价也卖不动，问题出在哪？",
        "提车{model}一周，{aspect}就出了问题",
        "{model}的{aspect}让我想退车",
        "真实车主反馈：{model}这些缺点忍不了",
    ],
    "neutral": [
        "{model}全面解析，优缺点一次说清",
        "客观评价{model}：有惊喜也有遗憾",
        "{brand}{model}值不值得买？看完这篇再决定",
        "{model} vs 竞品，到底谁更值得买？",
        "2026款{model}有哪些变化？一文读懂",
        "{model}用车成本分析，养车贵不贵？",
        "{brand}{model}选哪个配置最划算？",
        "{model}车主问答：大家最关心的10个问题",
        "从选车到提车，{model}购买全过程分享",
        "{model}三个月使用报告，给准车主参考",
    ],
}

# 评论内容模板
COMMENT_TEMPLATES = {
    "positive": [
        "这个车{aspect}确实不错，我试驾过",
        "同意，{model}的{aspect}是同级别最好的",
        "我也是{model}车主，{aspect}真的很满意",
        "性价比真的高，{aspect}没得说",
        "开了半年了，{aspect}表现一直很好",
        "准备入手了，被{aspect}种草",
        "{model}的{aspect}确实给力，推荐",
    ],
    "negative": [
        "我的{model}也遇到了，{aspect}确实有问题",
        "别提了，{aspect}是我的痛点",
        "同价位选竞品不香吗？{aspect}差太多",
        "后悔买了，{aspect}太失望",
        "这个价位{aspect}还这样，说不过去",
        "建议等等看下一代，{aspect}应该会改进",
    ],
    "neutral": [
        "各有优缺点吧，看个人需求",
        "这个价位都差不多，别期望太高",
        "还是去4S店试驾一下再说",
        "等降价再说，现在不急",
        "选车还是要看自己最看重什么",
    ],
}

# 维度关键词
ASPECTS = {
    "外观": {
        "positive": ["设计大气", "颜值高", "前脸好看", "尾灯漂亮", "轮毂帅气", "车身线条流畅"],
        "negative": ["设计一般", "前脸太夸张", "尾部不好看", "车灯不够亮", "轮毂样式老气"],
    },
    "内饰": {
        "positive": ["做工精致", "用料扎实", "科技感强", "屏幕清晰", "氛围灯漂亮", "座椅舒适"],
        "negative": ["塑料感重", "做工粗糙", "异响严重", "屏幕反应慢", "储物空间少"],
    },
    "动力": {
        "positive": ["动力充沛", "加速平顺", "油耗低", "换挡平顺", "起步轻快", "超车轻松"],
        "negative": ["起步肉", "变速箱顿挫", "油耗偏高", "动力不足", "涡轮迟滞明显"],
    },
    "空间": {
        "positive": ["空间大", "后排宽敞", "后备箱够用", "头部空间充裕", "腿部空间大"],
        "negative": ["空间偏小", "后排拥挤", "后备箱小", "头部空间压抑", "储物格太少"],
    },
    "性价比": {
        "positive": ["性价比高", "优惠大", "配置丰富", "物超所值", "终端价格良心"],
        "negative": ["性价比一般", "优惠太少", "配置偏低", "价格虚高", "保值率差"],
    },
    "操控": {
        "positive": ["操控精准", "底盘扎实", "转向轻盈", "刹车灵敏", "悬挂舒适"],
        "negative": ["操控一般", "底盘松散", "方向盘偏重", "刹车偏软", "悬挂偏硬"],
    },
    "舒适性": {
        "positive": ["隔音好", "减震舒适", "空调给力", "座椅舒服", "静谧性好"],
        "negative": ["噪音大", "减震硬", "空调慢", "座椅偏硬", "风噪明显"],
    },
}

# 作者名
AUTHORS = [
    "汽车评测试驾", "老司机说车", "车圈小助手", "买车那些事", "驾趣体验官",
    "车友俱乐部", "选车顾问小王", "车评人老张", "新车速递", "用车指南",
    "汽车之家网友", "懂车帝用户", "微博汽车博主", "小红书车友", "抖音车评人",
    "开车的老李", "90后女司机", "二胎奶爸选车", "通勤打工人", "自驾游客",
]

# 平台对应的URL模板
URL_TEMPLATES = {
    "weibo": "https://weibo.com/u/{uid}/post/{pid}",
    "autohome": "https://club.autohome.com.cn/bbs/thread/{tid}.html",
    "dongchedi": "https://www.dongchedi.com/article/{aid}",
    "yiche": "https://news.yiche.com/hao/wenzhang/{wid}/",
    "xiaohongshu": "https://www.xiaohongshu.com/explore/{xid}",
    "douyin": "https://www.douyin.com/video/{did}",
}


def generate_article(brand_name, model_info, source, sentiment_bias=None):
    """生成一篇模拟文章"""
    if sentiment_bias is None:
        sentiment_bias = random.choices(
            ["positive", "negative", "neutral"],
            weights=[0.5, 0.2, 0.3],
        )[0]

    model_name = model_info["name_cn"]
    templates = TITLE_TEMPLATES[sentiment_bias]
    title_template = random.choice(templates)

    # 随机选一个维度
    aspect_name = random.choice(list(ASPECTS.keys()))
    aspect_key = sentiment_bias if sentiment_bias in ASPECTS[aspect_name] else "positive"
    aspect_desc = random.choice(ASPECTS[aspect_name][aspect_key])

    title = title_template.format(
        brand=brand_name, model=model_name,
        aspect=aspect_desc,
    )

    # 生成正文（200-500字）
    content = _generate_content(brand_name, model_name, aspect_name,
                                aspect_desc, sentiment_bias)

    # 生成评论
    comments = _generate_comments(model_name, sentiment_bias, aspect_name)

    source_name = source["name"]
    url = URL_TEMPLATES[source_name].format(
        uid=random.randint(100000, 999999),
        pid=random.randint(1000000000, 9999999999),
        tid=random.randint(10000000, 99999999),
        aid=random.randint(1000000, 9999999),
        wid=random.randint(100000, 999999),
        xid=f"{random.randint(10000000, 99999999):016x}",
        did=random.randint(7000000000, 7999999999),
    )

    return {
        "source_name": source_name,
        "brand_name": brand_name,
        "model_name": model_name,
        "title": title,
        "content": content,
        "summary": content[:100] + "...",
        "url": url,
        "author": random.choice(AUTHORS),
        "publish_time": None,  # 由调用者设置
        "view_count": random.randint(500, 50000),
        "like_count": random.randint(10, 5000),
        "comment_count": len(comments),
        "share_count": random.randint(5, 1000),
        "comments": comments,
    }


def _generate_content(brand, model, aspect, aspect_desc, sentiment):
    """生成文章正文"""
    if sentiment == "positive":
        return (
            f"最近有机会深度体验了{brand}{model}这款车，整体感受非常不错。"
            f"首先要说的是{aspect}方面，{aspect_desc}，这在同级别车型中算是比较突出的表现。"
            f"从外观设计来看，{model}的整体造型很有辨识度，开出去回头率不低。"
            f"内饰方面用料和做工都比较用心，摸得到的地方基本都是软性材质。"
            f"驾驶感受上，动力输出平顺，底盘调校也偏向舒适，日常代步非常合适。"
            f"空间表现也不错，后排腿部空间充裕，后备箱容积完全够家用。"
            f"综合来看，{model}在这个价位段确实是一个很有竞争力的选择。"
            f"如果你正在考虑这个级别的车型，建议去4S店试驾感受一下。"
        )
    elif sentiment == "negative":
        return (
            f"提了{brand}{model}三个月，说实话有些后悔。"
            f"最大的问题出在{aspect}上，{aspect_desc}，严重影响日常使用体验。"
            f"当初选车的时候只关注了外观和价格，没有深入了解这些细节。"
            f"开了三个月下来，发现这个问题不仅没有改善，反而越来越明显。"
            f"去4S店检查，售后说是正常现象，这个回应让人很失望。"
            f"对比同价位的竞品，{model}在这个方面确实差了不少。"
            f"如果让我重新选择，可能不会选这款车了。"
            f"希望{brand}能重视这个问题，在后续改款中做出改进。"
        )
    else:
        return (
            f"今天来详细聊聊{brand}{model}这款车，给正在纠结的朋友一些参考。"
            f"先说优点：{aspect}方面表现不错，{aspect_desc}，日常使用比较满意。"
            f"外观设计中规中矩，不算惊艳但也不容易过时。"
            f"内饰用料还可以，但部分细节做工有提升空间。"
            f"动力表现够用，不算激进但日常代步完全没问题。"
            f"空间方面表现中等，满足基本家用需求。"
            f"价格方面，目前终端优惠还算可以，性价比尚可。"
            f"总的来说，{model}是一款比较均衡的车，没有明显短板也没有特别突出的亮点。"
            f"建议感兴趣的消费者去4S店实际试驾体验后再做决定。"
        )


def _generate_comments(model_name, sentiment, aspect):
    """生成评论"""
    count = random.randint(3, 10)
    comments = []
    templates = COMMENT_TEMPLATES[sentiment]

    aspect_descs = ASPECTS.get(aspect, {}).get(sentiment, ["表现不错"])

    for i in range(count):
        template = random.choice(templates)
        content = template.format(
            model=model_name,
            aspect=random.choice(aspect_descs) if aspect_descs else "整体表现",
        )
        comments.append({
            "content": content,
            "author": random.choice(AUTHORS),
            "like_count": random.randint(0, 500),
        })

    return comments


def generate_daily_data(days=30):
    """生成近N天的模拟数据"""
    all_articles = []
    today = date.today()

    for day_offset in range(days):
        current_date = today - timedelta(days=day_offset)

        for brand_name, brand_info in BRAND_MODELS.items():
            # 每天每个品牌随机选2-5篇文章
            article_count = random.randint(2, 5)

            for _ in range(article_count):
                model = random.choice(brand_info["models"])
                source = random.choice(DATA_SOURCES)
                article = generate_article(brand_name, model, source)
                article["publish_time"] = datetime.combine(
                    current_date,
                    datetime.min.time().replace(
                        hour=random.randint(6, 23),
                        minute=random.randint(0, 59),
                    )
                )
                all_articles.append(article)

    return all_articles
