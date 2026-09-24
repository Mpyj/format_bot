from telebot import types
from config import ADMIN_ID


def main_menu_keyboard(user_id: int = None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🖼️ تبدیل عکس'),
        types.KeyboardButton('📄 استخراج متن'),
        types.KeyboardButton('🗜️ ساخت ZIP'),
        types.KeyboardButton('🌐 تحلیل سایت'),
        types.KeyboardButton('🌐 ابزار شبکه'),
        types.KeyboardButton('💰 ابزار مالی'),
        types.KeyboardButton('📱 ساخت QR Code'),
        types.KeyboardButton('🎵 مبدل مدیا'),
        types.KeyboardButton('📄 ابزار PDF'),
        types.KeyboardButton('🎨 جعبه خلاقیت'),
        types.KeyboardButton('ℹ️ راهنما'),
    )

    if user_id and user_id == ADMIN_ID:
        markup.add(types.KeyboardButton('👑 پنل ادمین'))

    return markup


def zip_done_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ تمام شد'), types.KeyboardButton('❌ انصراف'))
    return markup