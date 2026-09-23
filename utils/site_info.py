import os
import ssl
import socket
import time
import logging
import requests
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

# timeout برای همه درخواست‌ها
TIMEOUT = 10


def _normalize_url(url: str) -> str:
    """اگه پروتکل نداشت، https:// اضافه کن"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_host(url: str) -> str:
    """اسم دامنه رو از URL در بیار"""
    parsed = urlparse(_normalize_url(url))
    return parsed.hostname or ""


def ping_host(host: str, port: int = 443, count: int = 3) -> dict:
    """
    پینگ TCP به هاست (اتصال به پورت خاص).
    میانگین زمان رو برمی‌گردونه.
    """
    times = []
    for _ in range(count):
        try:
            start = time.time()
            sock = socket.create_connection((host, port), timeout=TIMEOUT)
            sock.close()
            elapsed = (time.time() - start) * 1000  # میلی‌ثانیه
            times.append(elapsed)
        except Exception as e:
            logger.warning(f"پینگ ناموفق به {host}:{port}: {e}")

    if not times:
        return {"success": False}

    return {
        "success": True,
        "min": min(times),
        "max": max(times),
        "avg": sum(times) / len(times),
        "packets": f"{len(times)}/{count}",
    }


def get_ssl_info(host: str, port: int = 443) -> dict:
    """اطلاعات SSL certificate رو می‌گیره"""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                tls_version = ssock.version()
                cipher = ssock.cipher()

        # تاریخ انقضا
        not_after = cert.get("notAfter")
        if not_after:
            expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expire_date - datetime.now()).days
        else:
            expire_date = None
            days_left = None

        # صادرکننده
        issuer = dict(x[0] for x in cert.get("issuer", []))
        issuer_org = issuer.get("organizationName", "?")

        return {
            "success": True,
            "valid": True,
            "issuer": issuer_org,
            "tls_version": tls_version,
            "expire_date": expire_date.strftime("%Y-%m-%d") if expire_date else "?",
            "days_left": days_left,
            "cipher": cipher[0] if cipher else "?",
        }
    except ssl.SSLError as e:
        logger.warning(f"SSL error برای {host}: {e}")
        return {"success": True, "valid": False, "error": str(e)}
    except Exception as e:
        logger.warning(f"خطا در گرفتن SSL: {e}")
        return {"success": False}


def get_ip_info(host: str) -> dict:
    """IP هاست رو می‌گیره و اطلاعات جغرافیایی از API رایگان می‌گیره"""
    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        logger.warning(f"خطا در گرفتن IP {host}: {e}")
        return {"success": False}

    info = {"success": True, "ip": ip, "country": "?", "isp": "?", "city": "?"}

    # اطلاعات جغرافیایی از ip-api.com (رایگان، بدون کلید)
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,city,isp,org,as"},
            timeout=TIMEOUT
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                info["country"] = data.get("country", "?")
                info["city"] = data.get("city", "?")
                info["isp"] = data.get("isp") or data.get("org") or data.get("as", "?")
    except Exception as e:
        logger.warning(f"خطا در گرفتن اطلاعات IP: {e}")

    return info


def check_http(url: str) -> dict:
    """اطلاعات HTTP response رو می‌گیره"""
    try:
        start = time.time()
        r = requests.get(
            _normalize_url(url),
            timeout=TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (FormatBot/1.0)"}
        )
        elapsed = (time.time() - start) * 1000

        return {
            "success": True,
            "status_code": r.status_code,
            "reason": r.reason,
            "elapsed_ms": elapsed,
            "server": r.headers.get("Server", "?"),
            "content_type": r.headers.get("Content-Type", "?"),
            "content_length": len(r.content),
            "final_url": r.url,
            "redirects": len(r.history),
        }
    except requests.Timeout:
        return {"success": False, "error": "timeout", "message": "زمان پاسخ‌دهی تموم شد"}
    except requests.ConnectionError:
        return {"success": False, "error": "connection", "message": "اتصال برقرار نشد"}
    except Exception as e:
        logger.exception(f"خطا در HTTP check: {e}")
        return {"success": False, "error": "unknown", "message": str(e)}


def analyze_site(url: str) -> dict:
    """همه اطلاعات رو یه جا جمع می‌کنه"""
    host = _extract_host(url)
    if not host:
        return {"success": False, "error": "invalid_url"}

    result = {"success": True, "host": host, "url": _normalize_url(url)}

    # HTTP check
    result["http"] = check_http(url)

    # IP + Geo
    result["ip"] = get_ip_info(host)

    # Ping
    result["ping"] = ping_host(host)

    # SSL
    if _normalize_url(url).startswith("https://"):
        result["ssl"] = get_ssl_info(host)
    else:
        result["ssl"] = {"success": True, "valid": False, "error": "بدون HTTPS"}

    return result