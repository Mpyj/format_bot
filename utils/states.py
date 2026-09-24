from typing import Any

_user_states: dict[int, dict[str, Any]] = {}


MENU_BUTTONS = {
    '🖼️ تبدیل عکس',
    '📄 استخراج متن',
    '🗜️ ساخت ZIP',
    '🌐 تحلیل سایت',
    '🌐 ابزار شبکه',
    '💰 ابزار مالی',
    '🛠 ابزار متنی',
    '📱 ساخت QR Code',
    '🎵 مبدل مدیا',
    '📄 ابزار PDF',
    '🎨 جعبه خلاقیت',
    'ℹ️ راهنما',
    '👑 پنل ادمین',
    '✅ تمام شد',
    '❌ انصراف',
}


def is_menu_button(text: str) -> bool:
    return text in MENU_BUTTONS


def set_state(user_id: int, **kwargs):
    _user_states.setdefault(user_id, {}).update(kwargs)


def get_state(user_id: int) -> dict[str, Any]:
    return _user_states.get(user_id, {})


def clear_state(user_id: int):
    _user_states.pop(user_id, None)