import time
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import jdatetime
from hijri_converter import Gregorian
import sympy as sp

logger = logging.getLogger(__name__)

TIMEOUT = 15

# ============================================================
# 🗄 Cache ساده در حافظه
# ============================================================
_cache = {}


def _get_cache(key: str, ttl: int):
    """اگه cache معتبر بود، برگردون"""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < ttl:
            return data
    return None


def _set_cache(key: str, data):
    _cache[key] = (data, time.time())


# ============================================================
# 💵 قیمت ارز دیجیتال (CoinGecko — بدون کلید)
# ============================================================
CRYPTO_NAMES = {
    "btc": ("bitcoin", "Bitcoin", "BTC"),
    "eth": ("ethereum", "Ethereum", "ETH"),
    "usdt": ("tether", "Tether", "USDT"),
    "bnb": ("binancecoin", "BNB", "BNB"),
    "sol": ("solana", "Solana", "SOL"),
    "xrp": ("ripple", "Ripple", "XRP"),
    "ada": ("cardano", "Cardano", "ADA"),
    "doge": ("dogecoin", "Dogecoin", "DOGE"),
    "trx": ("tron", "TRON", "TRX"),
    "matic": ("matic-network", "Polygon", "MATIC"),
}


def get_crypto_price(symbol: str) -> dict:
    """قیمت ارز دیجیتال از CoinGecko (cache ۵ دقیقه)"""
    symbol = symbol.lower().strip()

    if symbol not in CRYPTO_NAMES:
        return {"success": False, "error": f"ارز {symbol} پشتیبانی نمیشه"}

    cache_key = f"crypto_{symbol}"
    cached = _get_cache(cache_key, 300)  # ۵ دقیقه
    if cached:
        return cached

    coin_id, name_fa, ticker = CRYPTO_NAMES[symbol]

    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd,irr",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
        }
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

        if coin_id not in data:
            return {"success": False, "error": "اطلاعات پیدا نشد"}

        info = data[coin_id]
        result = {
            "success": True,
            "name": name_fa,
            "ticker": ticker,
            "price_usd": info.get("usd", 0),
            "price_irr": info.get("irr", 0),
            "change_24h": info.get("usd_24h_change", 0),
            "volume_24h": info.get("usd_24h_vol", 0),
            "updated": datetime.now().strftime("%H:%M:%S"),
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"خطا در CoinGecko: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 💱 نرخ ارز جهانی (ExchangeRate-API — Open Access)
# ============================================================
CURRENCY_NAMES = {
    "USD": "🇺🇸 دلار آمریکا",
    "EUR": "🇪🇺 یورو",
    "GBP": "🇬🇧 پوند",
    "AED": "🇦🇪 درهم امارات",
    "TRY": "🇹🇷 لیر ترکیه",
    "CNY": "🇨🇳 یوان چین",
    "RUB": "🇷🇺 روبل",
    "CAD": "🇨🇦 دلار کانادا",
    "AUD": "🇦🇺 دلار استرالیا",
    "JPY": "🇯🇵 ین ژاپن",
}


def get_global_rates(base: str = "USD") -> dict:
    """نرخ ارزهای جهانی نسبت به base (cache ۱ ساعت)"""
    cache_key = f"rates_{base}"
    cached = _get_cache(cache_key, 3600)
    if cached:
        return cached

    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

        if data.get("result") != "success":
            return {"success": False, "error": "API خطا داد"}

        rates = data.get("rates", {})
        result = {
            "success": True,
            "base": base,
            "rates": rates,
            "updated": data.get("time_last_update_utc", ""),
            "next_update": data.get("time_next_update_utc", ""),
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"خطا در ExchangeRate-API: {e}")
        return {"success": False, "error": str(e)}


def get_iran_rates() -> dict:
    """
    نرخ ارز، طلا و سکه ایران از TGJU (cache ۱۰ دقیقه)
    """
    cache_key = "iran_rates"
    cached = _get_cache(cache_key, 600)
    if cached:
        return cached

    try:
        url = "https://www.tgju.org/"
        headers = {
            "User-Agent": "Mozilla/5.0 (FormatBot/1.0)"
        }
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        result = {"success": True, "data": {}, "updated": datetime.now().strftime("%H:%M:%S")}

        # نگاشت اسلاگ‌های TGJU
        targets = {
            "price_dollar_rl": "دلار",
            "price_eur": "یورو",
            "price_aed": "درهم امارات",
            "price_try": "لیر ترکیه",
            "geram18": "طلای ۱۸ عیار",
            "geram24": "طلای ۲۴ عیار",
            "sekke_emami": "سکه امامی",
            "sekke_bahar": "سکه بهار آزادی",
            "nim_sekke": "نیم سکه",
            "rob_sekke": "ربع سکه",
            "gerami": "سکه گرمی",
        }

        for slug, name in targets.items():
            try:
                element = soup.select_one(f'[data-market-nameslug="{slug}"]')
                if element:
                    price_el = element.select_one(".info-price")
                    if price_el:
                        price_text = price_el.get_text(strip=True).replace(",", "")
                        try:
                            result["data"][name] = int(price_text)
                        except ValueError:
                            result["data"][name] = price_text
            except Exception as e:
                logger.warning(f"خطا در استخراج {slug}: {e}")

        if not result["data"]:
            return {"success": False, "error": "اطلاعات TGJU استخراج نشد"}

        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"خطا در TGJU: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 📅 تبدیل تاریخ
# ============================================================
def convert_date(date_str: str) -> dict:
    """تبدیل تاریخ شمسی ↔ میلادی ↔ قمری"""
    try:
        # تشخیص فرمت
        date_str = date_str.strip().replace("-", "/").replace(".", "/")
        parts = date_str.split("/")

        if len(parts) != 3:
            return {"success": False, "error": "فرمت اشتباه. مثال: 1403/06/15"}

        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])

        # اگه سال < 1700 → شمسی
        if y < 1700:
            jalali = jdatetime.date(y, m, d)
            gregorian = jalali.togregorian()
            hijri = Gregorian(gregorian.year, gregorian.month, gregorian.day).to_hijri()
        else:
            # میلادی
            gregorian = datetime(y, m, d).date()
            jalali = jdatetime.date.fromgregorian(date=gregorian)
            hijri = Gregorian(y, m, d).to_hijri()

        weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays_fa[gregorian.weekday()]

        return {
            "success": True,
            "jalali": f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}",
            "gregorian": f"{gregorian.year}-{gregorian.month:02d}-{gregorian.day:02d}",
            "hijri": f"{hijri.year}/{hijri.month:02d}/{hijri.day:02d}",
            "weekday": weekday,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 🧮 ماشین حساب
# ============================================================
def calculate(expression: str) -> dict:
    """محاسبه ریاضی امن با sympy"""
    try:
        # محدود کردن کاراکترها
        allowed = set("0123456789+-*/().^ %")
        expr_clean = expression.replace("^", "**").replace("×", "*").replace("÷", "/")

        if not all(c in allowed for c in expr_clean):
            return {"success": False, "error": "عبارت شامل کاراکتر غیرمجاز"}

        result = sp.sympify(expr_clean)
        result_float = float(result)

        # اگه عدد صحیح بود، بدون اعشار نشون بده
        if result_float.is_integer():
            result_str = str(int(result_float))
        else:
            result_str = f"{result_float:.6f}".rstrip("0").rstrip(".")

        return {
            "success": True,
            "expression": expression,
            "result": result_str,
        }
    except Exception as e:
        return {"success": False, "error": f"عبارت نامعتبر: {e}"}