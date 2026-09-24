import os
import ssl
import socket
import time
import logging
import requests
from datetime import datetime
from urllib.parse import urlparse
import dns.resolver
import whois

logger = logging.getLogger(__name__)

TIMEOUT = 10


# ============================================================
# 🔍 WHOIS
# ============================================================
def get_whois(domain: str) -> dict:
    """اطلاعات WHOIS دامنه"""
    try:
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        w = whois.whois(domain)

        info = {
            "success": True,
            "domain": domain,
            "registrar": w.registrar or "—",
            "creation_date": _format_date(w.creation_date),
            "expiration_date": _format_date(w.expiration_date),
            "updated_date": _format_date(w.updated_date),
            "name_servers": w.name_servers if w.name_servers else [],
            "status": w.status if w.status else [],
            "emails": w.emails if w.emails else [],
            "country": w.country or "—",
            "org": w.org or "—",
        }
        return info
    except Exception as e:
        logger.warning(f"خطا در WHOIS: {e}")
        return {"success": False, "error": str(e)}


def _format_date(d):
    """تاریخ رو فرمت کن (ممکنه لیست باشه)"""
    if not d:
        return "—"
    if isinstance(d, list):
        d = d[0]
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    return str(d)


# ============================================================
# 📡 DNS Lookup
# ============================================================
def get_dns(domain: str) -> dict:
    """اطلاعات DNS دامنه"""
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    result = {"success": True, "domain": domain}

    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype)
            records = []
            for rdata in answers:
                if rtype == "MX":
                    records.append(f"{rdata.preference} {rdata.exchange}")
                elif rtype == "SOA":
                    records.append(f"{rdata.mname} (serial: {rdata.serial})")
                else:
                    records.append(str(rdata))
            result[rtype] = records
        except dns.resolver.NoAnswer:
            result[rtype] = []
        except dns.resolver.NXDOMAIN:
            return {"success": False, "error": "دامنه وجود نداره"}
        except Exception:
            result[rtype] = []

    return result


# ============================================================
# 🚪 اسکن پورت
# ============================================================
COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    27017: "MongoDB",
}


def scan_ports(host: str, ports: list = None) -> dict:
    """اسکن پورت‌های رایج"""
    if ports is None:
        ports = list(COMMON_PORTS.keys())

    host = host.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]

    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        return {"success": False, "error": f"دامنه resolve نشد: {e}"}

    open_ports = []
    closed_count = 0

    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            result = sock.connect_ex((ip, port))
            sock.close()

            if result == 0:
                service = COMMON_PORTS.get(port, "?")
                open_ports.append({"port": port, "service": service})
            else:
                closed_count += 1
        except Exception:
            closed_count += 1

    return {
        "success": True,
        "host": host,
        "ip": ip,
        "open_ports": open_ports,
        "total_scanned": len(ports),
        "closed_count": closed_count,
    }


# ============================================================
# 📶 تست سرعت دانلود (اصلاح‌شده — فایل ذخیره نمیشه)
# ============================================================
def test_download_speed(url: str, max_seconds: int = 5) -> dict:
    """
    سرعت دانلود از یه لینک.
    ⚠️ فایل روی دیسک ذخیره نمیشه — فقط توی RAM شمرده میشه و دور ریخته میشه.
    """
    response = None
    try:
        start = time.time()
        response = requests.get(
            url,
            stream=True,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (FormatBot/1.0)"}
        )
        response.raise_for_status()

        total_bytes = 0

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_bytes += len(chunk)

            elapsed = time.time() - start
            if elapsed >= max_seconds:
                break

        elapsed = time.time() - start
        speed_bps = total_bytes / elapsed if elapsed > 0 else 0
        speed_kbps = speed_bps / 1024
        speed_mbps = speed_kbps / 1024

        return {
            "success": True,
            "url": url,
            "downloaded_bytes": total_bytes,
            "downloaded_mb": total_bytes / (1024 * 1024),
            "elapsed": elapsed,
            "speed_kbps": speed_kbps,
            "speed_mbps": speed_mbps,
        }
    except requests.Timeout:
        return {"success": False, "error": "زمان پاسخ تموم شد (timeout)"}
    except requests.ConnectionError:
        return {"success": False, "error": "اتصال برقرار نشد"}
    except requests.HTTPError as e:
        return {"success": False, "error": f"خطای HTTP: {e.response.status_code}"}
    except Exception as e:
        logger.warning(f"خطا در تست سرعت: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # 👇 مهم: کانکشن رو قطع کن تا سرور درگیر نمونه
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


# ============================================================
# 🔒 جزئیات SSL
# ============================================================
def get_ssl_details(host: str) -> dict:
    """اطلاعات کامل SSL"""
    host = host.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                tls_version = ssock.version()
                cipher = ssock.cipher()

        not_after = cert.get("notAfter")
        expire_date = None
        days_left = None
        if not_after:
            expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            days_left = (expire_date - datetime.now()).days

        issuer = dict(x[0] for x in cert.get("issuer", []))
        subject = dict(x[0] for x in cert.get("subject", []))

        return {
            "success": True,
            "valid": True,
            "subject": subject.get("commonName", "—"),
            "issuer": issuer.get("organizationName", "—"),
            "issuer_cn": issuer.get("commonName", "—"),
            "tls_version": tls_version,
            "cipher": cipher[0] if cipher else "—",
            "expire_date": expire_date.strftime("%Y-%m-%d") if expire_date else "—",
            "days_left": days_left,
            "serial": cert.get("serialNumber", "—"),
        }
    except ssl.SSLError as e:
        return {"success": True, "valid": False, "error": str(e)}
    except Exception as e:
        logger.warning(f"خطا در SSL: {e}")
        return {"success": False, "error": str(e)}