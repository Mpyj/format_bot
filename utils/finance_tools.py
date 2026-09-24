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
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < ttl:
            return data
    return None


def _set_cache(key: str, data):
    _cache[key] = (data, time.time())


# ============================================================
# 💵 قیمت ارز دیجیتال (CoinGecko)
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
    symbol = symbol.lower().strip()
    if symbol not in CRYPTO_NAMES:
        return {"success": False, "error": f"ارز {symbol} پشتیبانی نمیشه"}

    cache_key = f"crypto_{symbol}"
    cached = _get_cache(cache_key, 300)
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
# 💱 نرخ ارز جهانی
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
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"خطا در ExchangeRate-API: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 🇮🇷 نرخ ارز، طلا و سکه ایران (چند API جایگزین)
# ============================================================
def get_iran_rates() -> dict:
    """
    نرخ ارز، طلا و سکه ایران — از چند API جایگزین
    """
    cache_key = "iran_rates"
    cached = _get_cache(cache_key, 600)
    if cached:
        return cached

    # تلاش ۱: Bonbast (اول این چون IP خارجی رو بلاک نمی‌کنه)
    result = _try_bonbast()
    if result and result.get("success") and result.get("data"):
        _set_cache(cache_key, result)
        logger.info("✅ نرخ‌ها از Bonbast")
        return result

    # تلاش ۲: TGJU scrape
    result = _try_tgju_scrape()
    if result and result.get("success") and result.get("data"):
        _set_cache(cache_key, result)
        logger.info("✅ نرخ‌ها از TGJU scrape")
        return result

    # تلاش ۳: TGJU API غیررسمی
    result = _try_tgju_api()
    if result and result.get("success") and result.get("data"):
        _set_cache(cache_key, result)
        logger.info("✅ نرخ‌ها از TGJU API")
        return result

    return {"success": False, "error": "هیچ API جواب نداد"}


def _try_bonbast() -> dict:
    """Bonbast.com — نرخ ارز و طلا"""
    try:
        url = "https://www.bonbast.com/json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.bonbast.com/",
        }
        r = requests.post(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()

        data = r.json()

        result = {
            "success": True,
            "data": {},
            "updated": datetime.now().strftime("%H:%M:%S"),
        }

        mapping = {
            "usd1": "دلار",
            "eur1": "یورو",
            "gbp1": "پوند",
            "aed1": "درهم امارات",
            "try1": "لیر ترکیه",
            "cny1": "یوان چین",
            "rub1": "روبل",
            "gold_18k": "طلای ۱۸ عیار",
            "gold_24k": "طلای ۲۴ عیار",
            "emami1": "سکه امامی",
            "azadi1": "سکه بهار آزادی",
            "nim1": "نیم سکه",
            "rob1": "ربع سکه",
            "gerami1": "سکه گرمی",
        }

        for key, name in mapping.items():
            if key in data:
                try:
                    result["data"][name] = int(str(data[key]).replace(",", ""))
                except (ValueError, TypeError):
                    pass

        if not result["data"]:
            return {"success": False, "error": "Bonbast داده نداد"}

        return result
    except Exception as e:
        logger.warning(f"Bonbast خطا: {e}")
        return {"success": False, "error": str(e)}


def _try_tgju_scrape() -> dict:
    """scrape TGJU با selectorهای جدید"""
    try:
        url = "https://www.tgju.org/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "fa,en;q=0.9",
        }
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        result = {
            "success": True,
            "data": {},
            "updated": datetime.now().strftime("%H:%M:%S"),
        }

        # پیدا کردن همه ردیف‌های جدول
        rows = soup.select("tr")

        keyword_map = {
            "دلار": "دلار",
            "یورو": "یورو",
            "پوند": "پوند",
            "درهم": "درهم امارات",
            "لیر": "لیر ترکیه",
            "یوان": "یوان چین",
            "طلا 18": "طلای ۱۸ عیار",
            "طلا 24": "طلای ۲۴ عیار",
            "سکه امامی": "سکه امامی",
            "نیم سکه": "نیم سکه",
            "ربع سکه": "ربع سکه",
            "سکه گرمی": "سکه گرمی",
        }

        for row in rows:
            try:
                text = row.get_text(" ", strip=True)

                for keyword, name in keyword_map.items():
                    if keyword in text and name not in result["data"]:
                        price_el = row.select_one(
                            ".info-price, .price, [data-col='info-price'], td.nf"
                        )
                        if price_el:
                            price_text = (
                                price_el.get_text(strip=True)
                                .replace(",", "")
                                .replace("٫", "")
                                .replace("٬", "")
                            )
                            try:
                                result["data"][name] = int(price_text)
                                break
                            except ValueError:
                                pass
            except Exception:
                continue

        if not result["data"]:
            return {"success": False, "error": "TGJU scrape داده نداد"}

        return result
    except Exception as e:
        logger.warning(f"TGJU scrape خطا: {e}")
        return {"success": False, "error": str(e)}


def _try_tgju_api() -> dict:
    """TGJU API غیررسمی"""
    try:
        url = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code != 200:
            return {"success": False}

        try:
            data = r.json()
        except Exception:
            return {"success": False}

        result = {
            "success": True,
            "data": {},
            "updated": datetime.now().strftime("%H:%M:%S"),
        }

        if isinstance(data, dict) and data.get("data"):
            if isinstance(data["data"], list):
                for item in data["data"]:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("title")
                        price = item.get("price") or item.get("value")
                        if name and price:
                            try:
                                result["data"][name] = int(
                                    str(price).replace(",", "")
                                )
                            except ValueError:
                                result["data"][name] = str(price)

        if not result["data"]:
            return {"success": False}

        return result
    except Exception as e:
        logger.warning(f"TGJU API خطا: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 📅 تبدیل تاریخ
# ============================================================
def convert_date(date_str: str) -> dict:
    try:
        date_str = date_str.strip().replace("-", "/").replace(".", "/")
        parts = date_str.split("/")

        if len(parts) != 3:
            return {"success": False, "error": "فرمت اشتباه. مثال: 1403/06/15"}

        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])

        if y < 1700:
            jalali = jdatetime.date(y, m, d)
            gregorian = jalali.togregorian()
            hijri = Gregorian(
                gregorian.year, gregorian.month, gregorian.day
            ).to_hijri()
        else:
            gregorian = datetime(y, m, d).date()
            jalali = jdatetime.date.fromgregorian(date=gregorian)
            hijri = Gregorian(y, m, d).to_hijri()

        weekdays_fa = [
            "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه",
            "جمعه", "شنبه", "یکشنبه"
        ]
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
    try:
        allowed = set("0123456789+-*/().^ %")
        expr_clean = (
            expression
            .replace("^", "**")
            .replace("×", "*")
            .replace("÷", "/")
        )

        if not all(c in allowed for c in expr_clean):
            return {"success": False, "error": "عبارت شامل کاراکتر غیرمجاز"}

        result = sp.sympify(expr_clean)
        result_float = float(result)

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