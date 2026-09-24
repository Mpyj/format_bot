from telebot import types
from config import ADMIN_ID


def main_menu_keyboard(user_id: int = None, page: int = None):
    """کیبورد اصلی — صفحه‌بندی شده"""
    # اگه page پاس نشد، از state بخون
    if page is None:
        if user_id:
            from utils.states import get_state
            page = get_state(user_id).get("menu_page", 1)
        else:
            page = 1

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    if page == 1:
        markup.add(
            types.KeyboardButton('🖼️ تبدیل عکس'),
            types.KeyboardButton('📄 استخراج متن'),
            types.KeyboardButton('🗜️ ساخت ZIP'),
            types.KeyboardButton('🌐 تحلیل سایت'),
            types.KeyboardButton('🌐 ابزار شبکه'),
            types.KeyboardButton('💰 ابزار مالی'),
            types.KeyboardButton('🛠 ابزار متنی'),
            types.KeyboardButton('📱 ساخت QR Code'),
        )
        markup.add(
            types.KeyboardButton('📄 صفحه ۲ ➡️'),
            types.KeyboardButton('ℹ️ راهنما'),
        )

    elif page == 2:
        markup.add(
            types.KeyboardButton('🎵 مبدل مدیا'),
            types.KeyboardButton('🎬 مدیا پیشرفته'),
            types.KeyboardButton('📄 ابزار PDF'),
            types.KeyboardButton('🎨 جعبه خلاقیت'),
        )
        markup.add(
            types.KeyboardButton('⬅️ صفحه ۱'),
            types.KeyboardButton('ℹ️ راهنما'),
        )

    if user_id and user_id == ADMIN_ID:
        markup.add(types.KeyboardButton('👑 پنل ادمین'))

    return markup


def zip_done_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ تمام شد'), types.KeyboardButton('❌ انصراف'))
    return markup