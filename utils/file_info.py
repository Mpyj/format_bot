import os
import logging
from datetime import datetime
from PIL import Image

logger = logging.getLogger(__name__)


def human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} بایت"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} کیلوبایت"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} مگابایت"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} گیگابایت"


def get_file_info(path: str) -> dict:
    if not os.path.exists(path):
        return {}

    info = {
        "name": os.path.basename(path),
        "ext": os.path.splitext(path)[1].lstrip(".").upper() or "?",
        "size_bytes": os.path.getsize(path),
        "size_human": human_size(os.path.getsize(path)),
        "modified": datetime.fromtimestamp(os.path.getmtime(path)),
    }

    try:
        with Image.open(path) as img:
            info["is_image"] = True
            info["width"] = img.width
            info["height"] = img.height
            info["mode"] = img.mode
            info["format"] = img.format or info["ext"]

            mode_names = {
                "RGB": "رنگی (RGB)",
                "RGBA": "رنگی + شفافیت (RGBA)",
                "L": "خاکستری (L)",
                "LA": "خاکستری + شفافیت (LA)",
                "P": "پالت رنگی (P)",
                "1": "سیاه و سفید (1)",
                "CMYK": "CMYK (چاپی)",
            }
            info["mode_fa"] = mode_names.get(img.mode, img.mode)

            dpi = img.info.get("dpi")
            if dpi:
                info["dpi"] = dpi
    except Exception:
        info["is_image"] = False

    return info


def format_file_info(info: dict, show_image_details: bool = True) -> str:
    if not info:
        return "❌ اطلاعات فایل در دسترس نیست."

    lines = [
        "📋 <b>اطلاعات فایل</b>",
        "━━━━━━━━━━━━━━━",
        f"📁 <b>اسم:</b> <code>{info.get('name', '?')}</code>",
        f"📄 <b>فرمت:</b> {info.get('ext', '?')}",
        f"📊 <b>حجم:</b> {info.get('size_human', '?')}",
    ]

    if show_image_details and info.get("is_image"):
        lines.append(f"📐 <b>ابعاد:</b> {info.get('width')} × {info.get('height')} پیکسل")
        lines.append(f"🎨 <b>حالت رنگ:</b> {info.get('mode_fa', info.get('mode', '?'))}")
        if info.get("dpi"):
            dpi = info["dpi"]
            lines.append(f"🖨 <b>رزولوشن:</b> {dpi[0]:.0f} × {dpi[1]:.0f} DPI")

    lines.append("━━━━━━━━━━━━━━━")
    return "\n".join(lines)