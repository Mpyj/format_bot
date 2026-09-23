import os
import uuid
import logging
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer
from config import TEMP_DIR

logger = logging.getLogger(__name__)


def generate_qr(
    data: str,
    fill_color: str = "black",
    back_color: str = "white",
    box_size: int = 10,
    rounded: bool = True,
) -> str | None:
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        fill_rgb = _hex_to_rgb(fill_color) if fill_color.startswith("#") else _name_to_rgb(fill_color)
        back_rgb = _hex_to_rgb(back_color) if back_color.startswith("#") else _name_to_rgb(back_color)

        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer() if rounded else SquareModuleDrawer(),
            color_mask=SolidFillColorMask(
                back_color=back_rgb,
                front_color=fill_rgb,
            ),
        )

        path = os.path.join(TEMP_DIR, f"qr_{uuid.uuid4().hex}.png")
        img.save(path)
        return path
    except Exception as e:
        logger.exception(f"خطا در ساخت QR: {e}")
        return None


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _name_to_rgb(name: str) -> tuple:
    mapping = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
    }
    return mapping.get(name.lower(), (0, 0, 0))