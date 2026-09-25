import os
import uuid
import logging
from pypdf import PdfReader, PdfWriter

from config import TEMP_DIR

logger = logging.getLogger(__name__)


# ============================================================
# 📝 افزودن شماره صفحه
# ============================================================
def add_page_numbers(input_path: str, start: int = 1, position: str = "bottom-center") -> str | None:
    """شماره‌گذاری صفحات PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import black

        reader = PdfReader(input_path)
        total_pages = len(reader.pages)

        # ساخت PDF شماره‌ها
        numbers_pdf = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_numbers.pdf")
        c = canvas.Canvas(numbers_pdf)
        c.setFont("Helvetica", 10)
        c.setFillColor(black)

        for i in range(total_pages):
            # ابعاد صفحه
            page = reader.pages[i]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            c.setPageSize((width, height))

            # متن شماره
            number_text = str(i + start)

            # موقعیت
            if position == "bottom-center":
                x = width / 2 - 10
                y = 20
            elif position == "bottom-right":
                x = width - 50
                y = 20
            elif position == "bottom-left":
                x = 30
                y = 20
            elif position == "top-center":
                x = width / 2 - 10
                y = height - 30
            elif position == "top-right":
                x = width - 50
                y = height - 30
            else:
                x = width / 2 - 10
                y = 20

            c.drawString(x, y, number_text)
            c.showPage()

        c.save()

        # اعمال روی PDF اصلی
        numbers_reader = PdfReader(numbers_pdf)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            page.merge_page(numbers_reader.pages[i])
            writer.add_page(page)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_numbered.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        try:
            os.remove(numbers_pdf)
        except Exception:
            pass

        return output
    except Exception as e:
        logger.exception(f"خطا در شماره‌گذاری: {e}")
        return None


# ============================================================
# 🔍 جستجو در PDF
# ============================================================
def search_pdf(input_path: str, query: str) -> dict:
    """جستجوی کلمه توی PDF"""
    try:
        reader = PdfReader(input_path)
        results = []

        query_lower = query.lower()

        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            text_lower = text.lower()

            if query_lower in text_lower:
                # شمارش تعداد
                count = text_lower.count(query_lower)
                # پیدا کردن جملات
                snippets = []
                idx = 0
                while True:
                    idx = text_lower.find(query_lower, idx)
                    if idx == -1:
                        break
                    start = max(0, idx - 30)
                    end = min(len(text), idx + len(query) + 30)
                    snippet = text[start:end].strip()
                    snippets.append(snippet)
                    idx += len(query)
                    if len(snippets) >= 3:
                        break

                results.append({
                    "page": i,
                    "count": count,
                    "snippets": snippets,
                })

        return {
            "success": True,
            "query": query,
            "total_pages": len(reader.pages),
            "found_pages": len(results),
            "results": results,
        }
    except Exception as e:
        logger.exception(f"خطا در جستجو: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 📋 استخراج متن
# ============================================================
def extract_text(input_path: str, max_pages: int = None) -> str | None:
    """استخراج متن از PDF"""
    try:
        reader = PdfReader(input_path)
        total = len(reader.pages)

        if max_pages:
            total = min(total, max_pages)

        text = ""
        for i in range(total):
            page_text = reader.pages[i].extract_text() or ""
            text += f"\n\n--- صفحه {i+1} ---\n\n{page_text}"

        return text.strip()
    except Exception as e:
        logger.exception(f"خطا در استخراج متن: {e}")
        return None


# ============================================================
# 🖼️ استخراج عکس‌ها
# ============================================================
def extract_images(input_path: str) -> list:
    """استخراج عکس‌های داخل PDF"""
    try:
        reader = PdfReader(input_path)
        output_paths = []

        for i, page in enumerate(reader.pages, 1):
            try:
                for img_idx, img in enumerate(page.images):
                    try:
                        # img.data = bytes, img.name = اسم
                        ext = os.path.splitext(img.name)[1] or ".png"
                        output = os.path.join(
                            TEMP_DIR,
                            f"{uuid.uuid4().hex}_p{i}_{img_idx}{ext}"
                        )
                        with open(output, "wb") as f:
                            f.write(img.data)

                        # حجم چک
                        if os.path.getsize(output) > 100:
                            output_paths.append(output)
                        else:
                            os.remove(output)

                        # حداکثر ۲۰ عکس
                        if len(output_paths) >= 20:
                            return output_paths
                    except Exception:
                        continue
            except Exception:
                continue

        return output_paths
    except Exception as e:
        logger.exception(f"خطا در استخراج عکس: {e}")
        return []


# ============================================================
# ✂️ حذف صفحات
# ============================================================
def delete_pages(input_path: str, pages_to_delete: list) -> str | None:
    """
    حذف صفحات مشخص.
    pages_to_delete: لیست شماره صفحات (۱-indexed)
    """
    try:
        reader = PdfReader(input_path)
        total = len(reader.pages)

        # تبدیل به ۰-indexed و فیلتر
        delete_set = set()
        for p in pages_to_delete:
            idx = p - 1
            if 0 <= idx < total:
                delete_set.add(idx)

        if not delete_set:
            return None

        if len(delete_set) >= total:
            return None  # همه صفحات حذف میشه

        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i not in delete_set:
                writer.add_page(page)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_deleted.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در حذف صفحات: {e}")
        return None


# ============================================================
# 🔄 مرتب‌سازی صفحات
# ============================================================
def reorder_pages(input_path: str, new_order: list) -> str | None:
    """
    مرتب‌سازی مجدد صفحات.
    new_order: لیست شماره صفحات به ترتیب دلخواه (۱-indexed)
    """
    try:
        reader = PdfReader(input_path)
        total = len(reader.pages)

        writer = PdfWriter()
        added = set()

        # اضافه کردن به ترتیب جدید
        for p in new_order:
            idx = p - 1
            if 0 <= idx < total and idx not in added:
                writer.add_page(reader.pages[idx])
                added.add(idx)

        # اضافه کردن صفحات باقی‌مانده
        for i in range(total):
            if i not in added:
                writer.add_page(reader.pages[i])

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_reordered.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در مرتب‌سازی: {e}")
        return None


# ============================================================
# 💧 واترمارک عکس
# ============================================================
def add_image_watermark(pdf_path: str, image_path: str, opacity: float = 0.3, position: str = "center") -> str | None:
    """واترمارک عکس روی PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import Color
        import io
        from PIL import Image

        # بارگذاری عکس
        img = Image.open(image_path)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")

        # ذخیره به bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        img_reader = ImageReader(img_bytes)

        # ساخت واترمارک
        wm_pdf_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_wm.pdf")

        reader = PdfReader(pdf_path)
        c = canvas.Canvas(wm_pdf_path)

        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            c.setPageSize((width, height))

            # اندازه عکس (۳۰٪ صفحه)
            img_size = min(width, height) * 0.3
            x_center = width / 2
            y_center = height / 2

            # موقعیت
            if position == "center":
                x = x_center - img_size / 2
                y = y_center - img_size / 2
            elif position == "bottom-right":
                x = width - img_size - 20
                y = 20
            elif position == "bottom-left":
                x = 20
                y = 20
            elif position == "top-right":
                x = width - img_size - 20
                y = height - img_size - 20
            elif position == "top-left":
                x = 20
                y = height - img_size - 20
            else:
                x = x_center - img_size / 2
                y = y_center - img_size / 2

            # ذخیره state
            c.saveState()
            c.setFillAlpha(opacity)
            c.drawImage(
                img_reader, x, y,
                width=img_size, height=img_size,
                mask="auto"
            )
            c.restoreState()
            c.showPage()

        c.save()

        # اعمال روی PDF اصلی
        wm_reader = PdfReader(wm_pdf_path)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            page.merge_page(wm_reader.pages[i])
            writer.add_page(page)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_img_watermarked.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        try:
            os.remove(wm_pdf_path)
        except Exception:
            pass

        return output
    except Exception as e:
        logger.exception(f"خطا در واترمارک عکس: {e}")
        return None


# ============================================================
# 📊 آمار PDF
# ============================================================
def get_pdf_stats(input_path: str) -> dict:
    """آمار کامل PDF"""
    try:
        reader = PdfReader(input_path)

        total_pages = len(reader.pages)
        total_words = 0
        total_chars = 0
        total_lines = 0

        # فقط ۲۰ صفحه اول برای سرعت
        max_check = min(total_pages, 20)

        for i in range(max_check):
            text = reader.pages[i].extract_text() or ""
            total_chars += len(text)
            total_words += len(text.split())
            total_lines += len(text.splitlines())

        # میانگین
        if max_check > 0:
            avg_words = total_words / max_check
            avg_chars = total_chars / max_check
        else:
            avg_words = 0
            avg_chars = 0

        # اطلاعات متادیتا
        meta = reader.metadata or {}
        title = meta.get("/Title", "") or ""
        author = meta.get("/Author", "") or ""
        creator = meta.get("/Creator", "") or ""

        # حجم
        size = os.path.getsize(input_path)

        return {
            "success": True,
            "pages": total_pages,
            "words": total_words,
            "words_checked": max_check,
            "avg_words_per_page": avg_words,
            "avg_chars_per_page": avg_chars,
            "lines": total_lines,
            "size": size,
            "encrypted": reader.is_encrypted,
            "title": title,
            "author": author,
            "creator": creator,
            "note": f"آمار بر اساس {max_check} صفحه اول" if max_check < total_pages else "",
        }
    except Exception as e:
        logger.exception(f"خطا در آمار: {e}")
        return {"success": False, "error": str(e)}


def parse_pages_input(text: str) -> list:
    """
    پارس ورودی صفحات: "1,3,5-8"
    """
    result = []
    try:
        parts = text.replace(" ", "").split(",")
        for part in parts:
            if "-" in part:
                start, end = part.split("-")
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(part))
        return result
    except Exception:
        return []


def parse_order_input(text: str) -> list:
    """
    پارس ترتیب صفحات: "1,3,2,4,5"
    """
    try:
        parts = text.replace(" ", "").split(",")
        return [int(p) for p in parts]
    except Exception:
        return []