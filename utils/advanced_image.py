import os
import uuid
import logging
from collections import Counter
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps, ImageFont

from config import TEMP_DIR

logger = logging.getLogger(__name__)


# ============================================================
# 🎨 پالت رنگ
# ============================================================
def get_color_palette(input_path: str, num_colors: int = 5) -> dict:
    """رنگ‌های غالب عکس"""
    try:
        img = Image.open(input_path).convert("RGB")
        img_small = img.resize((150, 150))  # کوچیک کن برای سرعت

        # کوانتایز به n رنگ
        quantized = img_small.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()

        # شمارش پیکسل‌ها
        colors_count = Counter(quantized.getdata())

        result_colors = []
        for idx, count in colors_count.most_common(num_colors):
            r = palette[idx * 3]
            g = palette[idx * 3 + 1]
            b = palette[idx * 3 + 2]
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            percentage = (count / (150 * 150)) * 100
            result_colors.append({
                "hex": hex_color,
                "rgb": (r, g, b),
                "percentage": round(percentage, 1),
            })

        return {"success": True, "colors": result_colors}
    except Exception as e:
        logger.exception(f"خطا در پالت رنگ: {e}")
        return {"success": False, "error": str(e)}


def generate_palette_image(input_path: str, num_colors: int = 5) -> str | None:
    """تولید عکس پالت رنگ"""
    try:
        result = get_color_palette(input_path, num_colors)
        if not result.get("success"):
            return None

        colors = result["colors"]
        w, h = 800, 200
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)

        band_w = w // len(colors)
        for i, c in enumerate(colors):
            r, g, b = c["rgb"]
            draw.rectangle(
                [(i * band_w, 0), ((i + 1) * band_w, h - 50)],
                fill=(r, g, b)
            )
            draw.text(
                (i * band_w + 10, h - 40),
                c["hex"],
                fill="black"
            )
            draw.text(
                (i * band_w + 10, h - 20),
                f"{c['percentage']}%",
                fill="black"
            )

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_palette.jpg")
        img.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در تولید پالت: {e}")
        return None


# ============================================================
# 📊 تاریخچه رنگ
# ============================================================
def get_color_history(input_path: str) -> dict:
    """تحلیل رنگ‌های اصلی (قرمز، آبی، ...)"""
    try:
        img = Image.open(input_path).convert("RGB")
        img_small = img.resize((100, 100))
        pixels = list(img_small.getdata())

        # دسته‌بندی ساده
        categories = {
            "🔴 قرمز": 0,
            "🟠 نارنجی": 0,
            "🟡 زرد": 0,
            "🟢 سبز": 0,
            "🔵 آبی": 0,
            "🟣 بنفش": 0,
            "⚫ تیره": 0,
            "⚪ روشن": 0,
        }

        for r, g, b in pixels:
            # محاسبه روشنایی
            brightness = (r + g + b) / 3

            if brightness < 60:
                categories["⚫ تیره"] += 1
            elif brightness > 200:
                categories["⚪ روشن"] += 1
            else:
                # تشخیص رنگ
                max_c = max(r, g, b)
                min_c = min(r, g, b)
                diff = max_c - min_c

                if diff < 30:
                    # خاکستری
                    if brightness > 128:
                        categories["⚪ روشن"] += 1
                    else:
                        categories["⚫ تیره"] += 1
                elif r == max_c and g == min_c:
                    categories["🔴 قرمز"] += 1
                elif r == max_c and b == min_c:
                    if g > 128:
                        categories["🟡 زرد"] += 1
                    else:
                        categories["🟠 نارنجی"] += 1
                elif g == max_c and b == min_c:
                    categories["🟢 سبز"] += 1
                elif g == max_c and r == min_c:
                    categories["🔵 آبی"] += 1
                elif b == max_c and r == min_c:
                    categories["🔵 آبی"] += 1
                elif b == max_c and g == min_c:
                    categories["🟣 بنفش"] += 1
                else:
                    categories["⚪ روشن"] += 1

        total = sum(categories.values())
        result = [
            {"name": k, "percentage": round(v / total * 100, 1)}
            for k, v in categories.items() if v > 0
        ]
        result.sort(key=lambda x: x["percentage"], reverse=True)

        return {"success": True, "history": result}
    except Exception as e:
        logger.exception(f"خطا در تاریخچه رنگ: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 📐 چرخش خودکار (EXIF)
# ============================================================
def auto_rotate(input_path: str) -> str | None:
    """چرخش خودکار بر اساس EXIF"""
    try:
        img = Image.open(input_path)
        rotated = ImageOps.exif_transpose(img)

        ext = os.path.splitext(input_path)[1] or ".jpg"
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_rotated{ext}")

        if rotated.mode in ("RGBA", "LA", "P") and ext.lower() in (".jpg", ".jpeg"):
            rotated = rotated.convert("RGB")

        rotated.save(output)
        return output
    except Exception as e:
        logger.exception(f"خطا در چرخش: {e}")
        return None


# ============================================================
# 🔍 بزرگ‌نمایی
# ============================================================
def zoom_image(input_path: str, factor: int = 2) -> str | None:
    """بزرگ‌نمایی عکس با LANCZOS"""
    try:
        img = Image.open(input_path)
        w, h = img.size
        new_w, new_h = w * factor, h * factor

        # محدودیت اندازه
        if new_w > 8000 or new_h > 8000:
            return None

        zoomed = img.resize((new_w, new_h), Image.LANCZOS)

        ext = os.path.splitext(input_path)[1] or ".jpg"
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_zoom{ext}")

        if zoomed.mode in ("RGBA", "LA", "P") and ext.lower() in (".jpg", ".jpeg"):
            zoomed = zoomed.convert("RGB")

        zoomed.save(output)
        return output
    except Exception as e:
        logger.exception(f"خطا در بزرگ‌نمایی: {e}")
        return None


# ============================================================
# 📸 کولاژ
# ============================================================
def make_collage(image_paths: list, cols: int = 2, cell_size: int = 500) -> str | None:
    """کولاژ از چند عکس"""
    try:
        n = len(image_paths)
        if n < 2:
            return None

        # اگه cols ندادی، بهترین grid رو حساب کن
        if cols <= 0:
            cols = 2 if n <= 4 else 3

        rows = (n + cols - 1) // cols

        padding = 10
        total_w = cols * cell_size + (cols + 1) * padding
        total_h = rows * cell_size + (rows + 1) * padding

        # محدودیت اندازه
        if total_w > 5000 or total_h > 5000:
            return None

        collage = Image.new("RGB", (total_w, total_h), (255, 255, 255))

        for i, path in enumerate(image_paths):
            try:
                img = Image.open(path).convert("RGB")

                # کراپ به مربع
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                img = img.crop((left, top, left + side, top + side))

                # resize به cell_size
                img = img.resize((cell_size, cell_size), Image.LANCZOS)

                # موقعیت
                row = i // cols
                col = i % cols
                x = padding + col * (cell_size + padding)
                y = padding + row * (cell_size + padding)

                collage.paste(img, (x, y))
            except Exception as e:
                logger.warning(f"خطا در عکس {i}: {e}")
                continue

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_collage.jpg")
        collage.save(output, "JPEG", quality=90)
        return output
    except Exception as e:
        logger.exception(f"خطا در کولاژ: {e}")
        return None


# ============================================================
# 🖼️ افزودن فریم
# ============================================================
def add_frame(input_path: str, color: str = "#FFFFFF", thickness: int = 30) -> str | None:
    """افزودن فریم به عکس"""
    try:
        img = Image.open(input_path).convert("RGB")
        w, h = img.size

        # تبدیل hex به rgb
        color = color.lstrip("#")
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

        # ساخت عکس جدید با فریم
        new_w = w + 2 * thickness
        new_h = h + 2 * thickness

        framed = Image.new("RGB", (new_w, new_h), rgb)
        framed.paste(img, (thickness, thickness))

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_frame.jpg")
        framed.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در فریم: {e}")
        return None


# ============================================================
# ✂️ برش هوشمند
# ============================================================
def smart_crop(input_path: str, ratio: str = "1:1") -> str | None:
    """برش عکس با نسبت مشخص"""
    try:
        ratios = {
            "1:1": (1, 1),
            "16:9": (16, 9),
            "9:16": (9, 16),
            "4:3": (4, 3),
            "3:2": (3, 2),
            "2:3": (2, 3),
        }

        if ratio not in ratios:
            ratio = "1:1"

        rw, rh = ratios[ratio]

        img = Image.open(input_path)
        w, h = img.size

        target_ratio = rw / rh
        current_ratio = w / h

        if current_ratio > target_ratio:
            # عکس پهن‌تره → از چپ و راست کراپ
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            cropped = img.crop((left, 0, left + new_w, h))
        else:
            # عکس بلندتره → از بالا و پایین کراپ
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            cropped = img.crop((0, top, w, top + new_h))

        ext = os.path.splitext(input_path)[1] or ".jpg"
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_crop{ext}")

        if cropped.mode in ("RGBA", "LA", "P") and ext.lower() in (".jpg", ".jpeg"):
            cropped = cropped.convert("RGB")

        cropped.save(output)
        return output
    except Exception as e:
        logger.exception(f"خطا در برش: {e}")
        return None


# ============================================================
# 🎭 افکت هنری
# ============================================================
def artistic_effect(input_path: str, effect: str = "oil") -> str | None:
    """افکت هنری روی عکس"""
    try:
        img = Image.open(input_path).convert("RGB")

        if effect == "oil":
            # نقاشی روغنی (ساده)
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = ImageEnhance.Color(img).enhance(1.5)

        elif effect == "pencil":
            # طرح مدادی
            gray = ImageOps.grayscale(img)
            inverted = ImageOps.invert(gray)
            blurred = inverted.filter(ImageFilter.GaussianBlur(10))
            # dodge blend ساده
            img = Image.blend(gray, blurred, 0.5)
            img = ImageOps.autocontrast(img)

        elif effect == "watercolor":
            # آبرنگ
            img = img.filter(ImageFilter.GaussianBlur(2))
            img = ImageEnhance.Color(img).enhance(1.8)
            img = ImageEnhance.Contrast(img).enhance(1.2)

        elif effect == "cartoon":
            # کارتونی
            img = img.filter(ImageFilter.MedianFilter(size=5))
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = ImageEnhance.Color(img).enhance(1.6)

        elif effect == "hdr":
            # HDR
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Color(img).enhance(1.3)
            img = ImageEnhance.Brightness(img).enhance(1.1)

        elif effect == "vintage":
            # قدیمی
            img = ImageOps.grayscale(img).convert("RGB")
            sepia = Image.new("RGB", img.size)
            pixels = img.getdata()
            sepia_pixels = []
            for r, g, b in pixels:
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                sepia_pixels.append((min(255, tr), min(255, tg), min(255, tb)))
            sepia.putdata(sepia_pixels)
            img = sepia

        else:
            return None

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_art_{effect}.jpg")
        img.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در افکت هنری: {e}")
        return None


# ============================================================
# 🎬 عکس → GIF
# ============================================================
def images_to_gif(image_paths: list, duration: int = 500) -> str | None:
    """چند عکس → GIF متحرک"""
    try:
        if len(image_paths) < 2:
            return None

        images = []
        for path in image_paths:
            img = Image.open(path).convert("RGB")
            # resize به اندازه یکسان
            img = img.resize((400, 400), Image.LANCZOS)
            images.append(img)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.gif")
        images[0].save(
            output,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0,
        )
        return output
    except Exception as e:
        logger.exception(f"خطا در GIF: {e}")
        return None


# ============================================================
# 📦 ابعاد عکس
# ============================================================
def get_image_dimensions(input_path: str) -> dict:
    """ابعاد و اطلاعات عکس"""
    try:
        img = Image.open(input_path)
        return {
            "success": True,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "format": img.format or "?",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}