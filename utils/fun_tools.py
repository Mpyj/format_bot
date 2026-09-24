import random
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

TIMEOUT = 15

# ============================================================
# 🎲 تاس و سکه
# ============================================================
def roll_dice() -> int:
    """تاس ۱ تا ۶"""
    return random.randint(1, 6)


def flip_coin() -> str:
    """شیر یا خط"""
    return random.choice(["🦁 شیر", "✍️ خط"])


def random_number(min_val: int = 1, max_val: int = 100) -> int:
    return random.randint(min_val, max_val)


# ============================================================
# 🎯 قرعه‌کشی
# ============================================================
def lottery(items: list) -> str | None:
    """انتخاب تصادفی از لیست"""
    if not items:
        return None
    return random.choice(items)


# ============================================================
# 😂 جوک
# ============================================================
def get_joke() -> dict:
    """جوک فارسی از API"""
    try:
        # API جوک فارسی
        url = "https://api.code4.ir/api/joke"
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            # ساختار ممکنه فرق کنه
            joke = None
            if isinstance(data, dict):
                joke = data.get("joke") or data.get("text") or data.get("result")
            elif isinstance(data, list) and data:
                joke = data[0] if isinstance(data[0], str) else data[0].get("joke")

            if joke:
                return {"success": True, "joke": joke}
    except Exception as e:
        logger.warning(f"خطا در جوک API: {e}")

    # fallback: جوک محلی
    local_jokes = [
        "به یه نفر می‌گن چرا دستت شکسته؟ می‌گه رفتم دکتر بگم دستم درد می‌کنه، دکتر گفت کدوم دستت؟ گفتم این دستم، گفت پس اون یکی رو بده! 😂",
        "یه روز یه مرد چاق می‌ره دکتر، دکتر می‌گه باید کمتر بخوری. مرد می‌گه: آقای دکتر، من که فقط ۳ وعده می‌خورم. دکتر می‌گه: آره، ولی هر وعده ۱۲ ساعت! 😂",
        "به یه نفر می‌گن چرا اینقدر لاغری؟ می‌گه چون هر چی می‌خورم، هضم نمی‌شه. گفتن پس چی می‌خوری؟ گفت: هیچی! 😂",
        "یه روز یه برنامه‌نویس می‌ره رستوران، گارسون می‌پرسه چی می‌خوری؟ می‌گه: بستگی داره، شرط چیه؟ 😂",
        "دکتر به بیمار: باید سیگار رو ترک کنی. بیمار: آقای دکتر، من سیگار نمی‌کشم! دکتر: پس چرا می‌لرزی؟ بیمار: چون شما رو دیدم! 😂",
    ]
    return {"success": True, "joke": random.choice(local_jokes)}


# ============================================================
# 📖 فال حافظ
# ============================================================
def get_hafez_fal() -> dict:
    """فال حافظ از API"""
    try:
        url = "https://api.code4.ir/api/hafez/random"
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                poem = data.get("poem") or data.get("text") or data.get("result")
                interpretation = data.get("interpretation") or data.get("meaning") or data.get("tafsir")
                if poem:
                    return {
                        "success": True,
                        "poem": poem,
                        "interpretation": interpretation or "",
                    }
    except Exception as e:
        logger.warning(f"خطا در فال حافظ: {e}")

    # fallback محلی
    local_fals = [
        {
            "poem": "دوش دیدم که ملائک در میخانه زدند\nگل آدم بسرشتند و به پیمانه زدند",
            "interpretation": "روزی پر از خبرهای خوب در انتظار شماست. با توکل به خدا پیش بروید.",
        },
        {
            "poem": "بیا تا گل برافشانیم و می در ساغر اندازیم\nفلک را سقف بشکافیم و طرحی نو در اندازیم",
            "interpretation": "زمان شروع کارهای جدید است. از فرصت‌ها استفاده کنید.",
        },
        {
            "poem": "در این شب سیاهم گم گشت راه مقصود\nاز گوشه‌ای برون آی ای کوکب هدایت",
            "interpretation": "راه‌حل مشکلات از جایی می‌آید که انتظارش را ندارید.",
        },
    ]
    fal = random.choice(local_fals)
    return {"success": True, "poem": fal["poem"], "interpretation": fal["interpretation"]}


# ============================================================
# 🧩 معما و چیستان
# ============================================================
LOCAL_RIDDLES = [
    ("آن چیست که هرچه از آن بگیری بزرگ‌تر می‌شود؟", "چاله"),
    ("آن چیست که هرچه بیشتر از آن برداری، بزرگ‌تر می‌شود؟", "چاله"),
    ("آن چیست که همیشه می‌آید ولی هرگز نمی‌رسد؟", "فردا"),
    ("آن چیست که پر است ولی خالی است؟", "قفس"),
    ("آن چیست که سر دارد ولی مو ندارد؟", "کوه"),
    ("آن چیست که می‌خورد ولی سیر نمی‌شود؟", "آتش"),
    ("آن چیست که هرچه از آن بدهی، بیشتر می‌شود؟", "دانش"),
    ("آن چیست که با آن که کار می‌کند، کار نمی‌کند؟", "قلم"),
    ("آن چیست که همیشه سرد است ولی یخ نیست؟", "سایه"),
    ("آن چیست که با یک چشم همه جا را می‌بیند؟", "سوزن"),
    ("چیست که وقتی شکسته می‌شود، درست می‌شود؟", "تخم مرغ"),
    ("آن چیست که هرچه بزرگ‌تر شود، سبک‌تر می‌شود؟", "بادکنک"),
]


def get_riddle() -> dict:
    """معما تصادفی"""
    q, a = random.choice(LOCAL_RIDDLES)
    return {"success": True, "question": q, "answer": a}


# ============================================================
# 💬 جمله انگیزشی
# ============================================================
LOCAL_MOTIVATIONS = [
    "🌟 موفقیت از جایی شروع می‌شود که ترس تمام می‌شود.",
    "💪 هیچ‌وقت دیر نیست، همیشه می‌شود از نو شروع کرد.",
    "🚀 رویاهایت را جدی بگیر، شاید فردا دیر باشد.",
    "🎯 هر روز یک قدم به هدف نزدیک‌تر شو.",
    "✨ تغییر از خودت شروع می‌شود.",
    "🔥 سختی‌ها بهترین معلم هستند.",
    "💎 ارزشمندترین چیزها با سختی به دست می‌آیند.",
    "🌈 بعد از هر باران، رنگین‌کمان می‌آید.",
    "🌱 هر روز فرصتی برای رشد است.",
    "⭐ بهترین نسخه خودت باش، نه نسخه‌ی دیگران.",
    "🎨 زندگی بوم نقاشی توست، خودت رنگش کن.",
    "🏆 برنده کسی است که بلند می‌شود، نه کسی که نمی‌افتد.",
]


def get_motivation() -> str:
    return random.choice(LOCAL_MOTIVATIONS)


# ============================================================
# 🎨 رنگ تصادفی
# ============================================================
def random_color() -> dict:
    """تولید رنگ تصادفی"""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    hex_color = f"#{r:02X}{g:02X}{b:02X}"

    # پیدا کردن اسم رنگ
    color_name = _get_color_name(r, g, b)

    return {
        "success": True,
        "rgb": (r, g, b),
        "hex": hex_color,
        "name": color_name,
    }


def _get_color_name(r: int, g: int, b: int) -> str:
    """اسم ساده رنگ"""
    if r < 50 and g < 50 and b < 50:
        return "⚫ مشکی"
    if r > 200 and g > 200 and b > 200:
        return "⚪ سفید"
    if abs(r - g) < 30 and abs(g - b) < 30:
        return "🩶 خاکستری"
    if r > g and r > b:
        if g > 150:
            return "🟡 زرد/نارنجی"
        if b > 100:
            return "🟣 بنفش/صورتی"
        return "🔴 قرمز"
    if g > r and g > b:
        return "🟢 سبز"
    return "🔵 آبی"


# ============================================================
# 📅 امروز
# ============================================================
def get_today_info() -> dict:
    """اطلاعات امروز"""
    import jdatetime
    now = datetime.now()
    jalali = jdatetime.date.fromgregorian(date=now.date())

    weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = weekdays_fa[now.weekday()]

    return {
        "success": True,
        "jalali": f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}",
        "gregorian": now.strftime("%Y-%m-%d"),
        "weekday": weekday,
        "time": now.strftime("%H:%M:%S"),
    }


# ============================================================
# 🎁 چی بخوریم؟
# ============================================================
FOODS = [
    "🍕 پیتزا", "🍔 همبرگر", "🍝 پاستا", "🍚 چلوکباب",
    "🌯 شاورما", "🥘 قورمه‌سبزی", "🍲 آش رشته", "🥗 سالاد",
    "🍗 مرغ سوخاری", "🥙 کباب ترکی", "🍜 نودل", "🍤 میگو",
    "🌮 تاکو", "🥪 ساندویچ", "🍖 کباب کوبیده", "🍛 بریانی",
    "🐟 ماهی", "🍳 املت", "🧆 فلافل", "🥟 سمبوسه",
]


def what_to_eat() -> str:
    return random.choice(FOODS)