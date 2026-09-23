import os
import uuid
import logging
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from config import TEMP_DIR

logger = logging.getLogger(__name__)

# ⚠️ مسیر poppler روی ویندوز
POPPLER_PATH = r"C:\poppler\Library\bin"
if not os.path.exists(POPPLER_PATH):
    POPPLER_PATH = None


# ---------- ادغام ----------
def merge_pdfs(paths: list[str]) -> str | None:
    """چند PDF رو با هم ادغام می‌کنه"""
    try:
        writer = PdfWriter()
        for p in paths:
            writer.append(p)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_merged.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در ادغام PDF: {e}")
        return None


# ---------- تقسیم ----------
def split_pdf(input_path: str, ranges: list[tuple[int, int]]) -> list[str]:
    outputs = []
    try:
        reader = PdfReader(input_path)
        total_pages = len(reader.pages)

        for idx, (start, end) in enumerate(ranges, 1):
            s = max(0, start - 1)
            e = min(total_pages, end)
            if s >= e:
                continue

            writer = PdfWriter()
            for page_num in range(s, e):
                writer.add_page(reader.pages[page_num])

            output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_part{idx}_{s+1}-{e}.pdf")
            with open(output, "wb") as f:
                writer.write(f)
            outputs.append(output)
        return outputs
    except Exception as e:
        logger.exception(f"خطا در تقسیم PDF: {e}")
        return []


# ---------- قفل ----------
def encrypt_pdf(input_path: str, password: str) -> str | None:
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=password, owner_password=password)
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_locked.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در قفل PDF: {e}")
        return None


# ---------- باز کردن قفل ----------
def decrypt_pdf(input_path: str, password: str) -> str | None:
    try:
        reader = PdfReader(input_path)
        if reader.is_encrypted:
            if not reader.decrypt(password):
                logger.warning("رمز اشتباه")
                return None
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_unlocked.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در باز کردن قفل: {e}")
        return None


# ---------- چرخش ----------
def rotate_pdf(input_path: str, angle: int) -> str | None:
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(angle)
            writer.add_page(page)
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_rotated.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در چرخش PDF: {e}")
        return None


# ---------- PDF → عکس ----------
def pdf_to_images(input_path: str, dpi: int = 150, max_pages: int = 10) -> list[str]:
    try:
        from pdf2image import convert_from_path
        kwargs = {
            "dpi": dpi, "fmt": "jpeg",
            "output_folder": TEMP_DIR, "paths_only": True,
            "first_page": 1, "last_page": max_pages,
        }
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH
        return convert_from_path(input_path, **kwargs)
    except Exception as e:
        logger.exception(f"خطا در تبدیل PDF به عکس: {e}")
        return []


# ---------- عکس → PDF ----------
def images_to_pdf(image_paths: list[str]) -> str | None:
    try:
        from PIL import Image
        images = []
        for p in image_paths:
            img = Image.open(p)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            images.append(img)
        if not images:
            return None
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_images.pdf")
        images[0].save(output, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
        return output
    except Exception as e:
        logger.exception(f"خطا در تبدیل عکس به PDF: {e}")
        return None


# ---------- فشرده‌سازی ----------
def compress_pdf(input_path: str) -> str | None:
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        writer.compress_identical_objects()
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_compressed.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در فشرده‌سازی PDF: {e}")
        return None


# ---------- واترمارک ----------
def add_watermark(input_path: str, text: str) -> str | None:
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import Color

        wm_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_wm.pdf")
        c = canvas.Canvas(wm_path, pagesize=A4)
        width, height = A4
        c.saveState()
        c.setFont("Helvetica-Bold", 60)
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.3))
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, text)
        c.restoreState()
        c.save()

        reader = PdfReader(input_path)
        wm_reader = PdfReader(wm_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.merge_page(wm_reader.pages[0])
            writer.add_page(page)
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_watermarked.pdf")
        with open(output, "wb") as f:
            writer.write(f)
        return output
    except Exception as e:
        logger.exception(f"خطا در واترمارک: {e}")
        return None


# ---------- اطلاعات PDF ----------
def get_pdf_info(input_path: str) -> dict:
    info = {"success": False, "pages": 0, "encrypted": False, "size": 0}
    try:
        reader = PdfReader(input_path)
        info["pages"] = len(reader.pages)
        info["encrypted"] = reader.is_encrypted
        info["size"] = os.path.getsize(input_path)
        if reader.metadata:
            meta = reader.metadata
            info["title"] = meta.get("/Title", "")
            info["author"] = meta.get("/Author", "")
            info["creator"] = meta.get("/Creator", "")
        info["success"] = True
        return info
    except Exception as e:
        logger.warning(f"خطا در اطلاعات PDF: {e}")
        return info