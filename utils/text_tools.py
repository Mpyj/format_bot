import re
import base64
import urllib.parse
import logging
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================
# 🔤 شمارش کلمات
# ============================================================
def count_text(text: str) -> dict:
    """آمار متن"""
    try:
        # کلمات
        words = re.findall(r"\S+", text)
        word_count = len(words)

        # حروف (فارسی + انگلیسی)
        letter_count = sum(1 for c in text if c.isalpha())

        # خطوط
        lines = [l for l in text.splitlines() if l.strip()]
        line_count = len(lines)

        # پاراگراف‌ها (جدا شده با خط خالی)
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        para_count = len(paragraphs)

        # جملات (بر اساس . ! ? و ؟ !)
        sentences = re.split(r"[.!?؟!؛]+", text)
        sentence_count = len([s for s in sentences if s.strip()])

        # زمان تقریبی خوندن (۲۰۰ کلمه در دقیقه)
        reading_time = max(1, round(word_count / 200))

        # زمان تقریبی صحبت (۱۵۰ کلمه در دقیقه)
        speaking_time = max(1, round(word_count / 150))

        # کاراکترها
        char_count = len(text)
        char_no_space = len(text.replace(" ", "").replace("\n", ""))

        return {
            "success": True,
            "word_count": word_count,
            "letter_count": letter_count,
            "char_count": char_count,
            "char_no_space": char_no_space,
            "line_count": line_count,
            "para_count": para_count,
            "sentence_count": sentence_count,
            "reading_time": reading_time,
            "speaking_time": speaking_time,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🔄 تبدیل حالت حروف
# ============================================================
def transform_case(text: str) -> dict:
    """حالت‌های مختلف حروف"""
    try:
        # Alternate: HeLlO wOrLd
        alt = "".join(
            c.upper() if i % 2 == 0 else c.lower()
            for i, c in enumerate(text)
        )

        # Inverse: hELLO wORLD
        inverse = text.swapcase()

        # Sentence case: Hello world
        sentences = re.split(r"([.!?]\s+)", text)
        sentence_case = ""
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:
                sentence_case += part[0].upper() + part[1:].lower() if part else ""
            else:
                sentence_case += part

        return {
            "success": True,
            "upper": text.upper(),
            "lower": text.lower(),
            "title": text.title(),
            "capitalize": text.capitalize(),
            "sentence": sentence_case,
            "alternate": alt,
            "inverse": inverse,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🎭 تغییر یونیکد
# ============================================================
def unicode_styles(text: str) -> dict:
    """متن رو به استایل‌های یونیکد تبدیل می‌کنه"""
    try:
        # نگاشت کاراکترها
        bold_map = {
            'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠',
            'h': '𝐡', 'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧',
            'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮',
            'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
            'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆',
            'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍',
            'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔',
            'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
            '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔',
            '7': '𝟕', '8': '𝟖', '9': '𝟗',
        }

        italic_map = {
            'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒', 'f': '𝑓', 'g': '𝑔',
            'h': 'ℎ', 'i': '𝑖', 'j': '𝑗', 'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛',
            'o': '𝑜', 'p': '𝑝', 'q': '𝑞', 'r': '𝑟', 's': '𝑠', 't': '𝑡', 'u': '𝑢',
            'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦', 'z': '𝑧',
            'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸', 'F': '𝐹', 'G': '𝐺',
            'H': '𝐻', 'I': '𝐼', 'J': '𝐽', 'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁',
            'O': '𝑂', 'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇', 'U': '𝑈',
            'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 'Z': '𝑍',
        }

        script_map = {
            'a': '𝒶', 'b': '𝒷', 'c': '𝒸', 'd': '𝒹', 'e': 'ℯ', 'f': '𝒻', 'g': 'ℊ',
            'h': '𝒽', 'i': '𝒾', 'j': '𝒿', 'k': '𝓀', 'l': '𝓁', 'm': '𝓂', 'n': '𝓃',
            'o': 'ℴ', 'p': '𝓅', 'q': '𝓆', 'r': '𝓇', 's': '𝓈', 't': '𝓉', 'u': '𝓊',
            'v': '𝓋', 'w': '𝓌', 'x': '𝓍', 'y': '𝓎', 'z': '𝓏',
            'A': '𝒜', 'B': 'ℬ', 'C': '𝒞', 'D': '𝒟', 'E': 'ℰ', 'F': 'ℱ', 'G': '𝒢',
            'H': 'ℋ', 'I': 'ℐ', 'J': '𝒥', 'K': '𝒦', 'L': 'ℒ', 'M': 'ℳ', 'N': '𝒩',
            'O': '𝒪', 'P': '𝒫', 'Q': '𝒬', 'R': 'ℛ', 'S': '𝒮', 'T': '𝒯', 'U': '𝒰',
            'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴', 'Z': '𝒵',
        }

        fraktur_map = {
            'a': '𝔞', 'b': '𝔟', 'c': '𝔠', 'd': '𝔡', 'e': '𝔢', 'f': '𝔣', 'g': '𝔤',
            'h': '𝔥', 'i': '𝔦', 'j': '𝔧', 'k': '𝔨', 'l': '𝔩', 'm': '𝔪', 'n': '𝔫',
            'o': '𝔬', 'p': '𝔭', 'q': '𝔮', 'r': '𝔯', 's': '𝔰', 't': '𝔱', 'u': '𝔲',
            'v': '𝔳', 'w': '𝔴', 'x': '𝔵', 'y': '𝔶', 'z': '𝔷',
            'A': '𝔄', 'B': '𝔅', 'C': 'ℭ', 'D': '𝔇', 'E': '𝔈', 'F': '𝔉', 'G': '𝔊',
            'H': 'ℌ', 'I': 'ℑ', 'J': '𝔍', 'K': '𝔎', 'L': '𝔏', 'M': '𝔐', 'N': '𝔑',
            'O': '𝔒', 'P': '𝔓', 'Q': '𝔔', 'R': 'ℜ', 'S': '𝔖', 'T': '𝔗', 'U': '𝔘',
            'V': '𝔙', 'W': '𝔚', 'X': '𝔛', 'Y': '𝔜', 'Z': 'ℨ',
        }

        mono_map = {
            'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐',
            'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗',
            'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
            'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣',
            'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
            'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
            'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
            'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
        }

        def apply_map(text, mapping):
            return "".join(mapping.get(c, c) for c in text)

        return {
            "success": True,
            "bold": apply_map(text, bold_map),
            "italic": apply_map(text, italic_map),
            "script": apply_map(text, script_map),
            "fraktur": apply_map(text, fraktur_map),
            "mono": apply_map(text, mono_map),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🔁 Reverse
# ============================================================
def reverse_text(text: str) -> dict:
    """متن رو برعکس می‌کنه"""
    try:
        # Reverse کل متن
        reversed_text = text[::-1]

        # Reverse کلمات (ترتیب کلمات عوض میشه، خود کلمه نه)
        reversed_words = " ".join(text.split()[::-1])

        # Reverse هر کلمه (حروفش برعکس)
        each_word_reversed = " ".join(w[::-1] for w in text.split())

        return {
            "success": True,
            "reversed": reversed_text,
            "reversed_words": reversed_words,
            "each_word_reversed": each_word_reversed,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🧹 پاک‌سازی متن
# ============================================================
def clean_text(text: str) -> dict:
    """متن رو تمیز می‌کنه"""
    try:
        # حذف فاصله اضافه
        no_extra_space = re.sub(r" +", " ", text).strip()

        # حذف خط خالی
        no_empty_lines = re.sub(r"\n\s*\n+", "\n", text).strip()

        # حذف کاراکترهای غیرحرفی (فقط حروف و فاصله)
        only_letters = re.sub(r"[^\w\s\u0600-\u06FF]", "", text)

        # حذف اعداد
        no_numbers = re.sub(r"\d+", "", text)

        # حذف ایموجی
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U00002600-\U000026FF"
            "]+",
            flags=re.UNICODE,
        )
        no_emoji = emoji_pattern.sub("", text)

        # حذف فاصله اول و آخر خطوط
        stripped_lines = "\n".join(l.strip() for l in text.splitlines())

        return {
            "success": True,
            "no_extra_space": no_extra_space,
            "no_empty_lines": no_empty_lines,
            "only_letters": only_letters,
            "no_numbers": no_numbers,
            "no_emoji": no_emoji,
            "stripped_lines": stripped_lines,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🔐 Base64
# ============================================================
def base64_encode(text: str) -> dict:
    try:
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return {"success": True, "result": encoded}
    except Exception as e:
        return {"success": False, "error": str(e)}


def base64_decode(text: str) -> dict:
    try:
        # اگه padding نداشت، اضافه کن
        text = text.strip()
        missing_padding = len(text) % 4
        if missing_padding:
            text += "=" * (4 - missing_padding)

        decoded = base64.b64decode(text).decode("utf-8")
        return {"success": True, "result": decoded}
    except Exception as e:
        return {"success": False, "error": f"متن Base64 معتبر نیست: {e}"}


# ============================================================
# 🔗 URL Encode/Decode
# ============================================================
def url_encode(text: str) -> dict:
    try:
        encoded = urllib.parse.quote(text, safe="")
        return {"success": True, "result": encoded}
    except Exception as e:
        return {"success": False, "error": str(e)}


def url_decode(text: str) -> dict:
    try:
        decoded = urllib.parse.unquote(text)
        return {"success": True, "result": decoded}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🔢 تبدیل اعداد
# ============================================================
def convert_number(number_str: str) -> dict:
    """عدد رو بین پایه‌ها تبدیل می‌کنه"""
    try:
        # اگه عدد انگلیسی نبود، فارسی رو تبدیل کن
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        for i, c in enumerate(persian_digits):
            number_str = number_str.replace(c, str(i))
        for i, c in enumerate(arabic_digits):
            number_str = number_str.replace(c, str(i))

        n = int(number_str.strip())

        return {
            "success": True,
            "decimal": str(n),
            "binary": bin(n)[2:],
            "octal": oct(n)[2:],
            "hex": hex(n)[2:].upper(),
        }
    except ValueError:
        return {"success": False, "error": "عدد معتبر نیست"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 📊 تحلیل متن
# ============================================================
def analyze_text(text: str, top_n: int = 10) -> dict:
    """پربسامدترین کلمات"""
    try:
        # کلمات (حذف علائم)
        words = re.findall(r"\S+", text)
        # حذف علائم نقطه‌گذاری
        words = [re.sub(r"[^\w\u0600-\u06FF]", "", w) for w in words]
        words = [w for w in words if len(w) >= 2]

        if not words:
            return {"success": False, "error": "کلمه‌ای پیدا نشد"}

        counter = Counter(words)
        top = counter.most_common(top_n)

        return {
            "success": True,
            "total_words": len(words),
            "unique_words": len(counter),
            "top_words": top,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🎨 ASCII Art
# ============================================================
def ascii_art(text: str, font: str = "standard") -> dict:
    """متن رو به ASCII art تبدیل می‌کنه"""
    try:
        import pyfiglet

        # فونت‌های موجود
        fonts = pyfiglet.FigletFont.getFonts()

        if font not in fonts:
            font = "standard"

        result = pyfiglet.figlet_format(text, font=font)

        # اگه طولانی بود، خط‌ها رو کوتاه کن
        if len(result) > 3500:
            return {"success": False, "error": "متن خیلی طولانیه برای ASCII art"}

        return {"success": True, "result": result, "font": font}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_ascii_fonts() -> list:
    """لیست فونت‌های موجود"""
    try:
        import pyfiglet
        return pyfiglet.FigletFont.getFonts()
    except Exception:
        return []