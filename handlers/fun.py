import logging
from telebot import types

from main import bot
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.fun_tools import (
    roll_dice, flip_coin, random_number, lottery,
    get_joke, get_hafez_fal, get_riddle, get_motivation,
    random_color, get_today_info, what_to_eat,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منو
# ============================================================
def _fun_menu(user_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 تاس", callback_data="fun_dice"),
        types.InlineKeyboardButton("🪙 سکه", callback_data="fun_coin"),
    )
    markup.add(
        types.InlineKeyboardButton("🔢 عدد تصادفی", callback_data="fun_number"),
        types.InlineKeyboardButton("🎯 قرعه‌کشی", callback_data="fun_lottery"),
    )
    markup.add(
        types.InlineKeyboardButton("😂 جوک", callback_data="fun_joke"),
        types.InlineKeyboardButton("📖 فال حافظ", callback_data="fun_hafez"),
    )
    markup.add(
        types.InlineKeyboardButton("🧩 معما", callback_data="fun_riddle"),
        types.InlineKeyboardButton("💬 جمله انگیزشی", callback_data="fun_motivation"),
    )
    markup.add(
        types.InlineKeyboardButton("🎨 رنگ تصادفی", callback_data="fun_color"),
        types.InlineKeyboardButton("📅 امروز", callback_data="fun_today"),
    )
    markup.add(
        types.InlineKeyboardButton("🍕 چی بخوریم؟", callback_data="fun_food"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="fun_close"))
    return markup


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '🎮 سرگرمی')
def fun_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="fun", waiting_for=None)

    bot.send_message(
        message.chat.id,
        "🎮 <b>سرگرمی</b>\n\n"
        "🎲 <b>تاس</b> — ۱ تا ۶\n"
        "🪙 <b>سکه</b> — شیر یا خط\n"
        "🔢 <b>عدد تصادفی</b> — ۱ تا ۱۰۰\n"
        "🎯 <b>قرعه‌کشی</b> — از لیست\n"
        "😂 <b>جوک</b> — جوک فارسی\n"
        "📖 <b>فال حافظ</b> — فال روزانه\n"
        "🧩 <b>معما</b> — چیستان\n"
        "💬 <b>جمله انگیزشی</b> — انرژی مثبت\n"
        "🎨 <b>رنگ تصادفی</b> — رنگ رندوم\n"
        "📅 <b>امروز</b> — تاریخ و ساعت\n"
        "🍕 <b>چی بخوریم؟</b> — پیشنهاد غذا",
        parse_mode='HTML',
        reply_markup=_fun_menu(user_id)
    )


# ============================================================
# callback
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("fun_"))
def fun_action(call):
    user_id = call.from_user.id
    action = call.data.replace("fun_", "")

    # 👇 اول back رو چک کن
    if action == "back":
        bot.answer_callback_query(call.id)
        clear_state(user_id)
        set_state(user_id, mode="fun", waiting_for=None)
        try:
            bot.edit_message_text(
                "🎮 <b>سرگرمی</b>\n\nیه گزینه انتخاب کن:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_fun_menu(user_id)
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "🎮 <b>سرگرمی</b>",
                parse_mode='HTML', reply_markup=_fun_menu(user_id)
            )
        return

    # 👇 نمایش پاسخ معما
    if action == "riddle_show":
        state = get_state(user_id)
        answer = state.get("fun_riddle_answer", "?")
        question = state.get("fun_riddle_question", "?")

        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                f"🧩 <b>معما</b>\n━━━━━━━━━━━━━━━\n\n"
                f"❓ {question}\n\n"
                f"✅ <b>پاسخ:</b> {answer}",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup(row_width=2).add(
                    types.InlineKeyboardButton("🧩 معما بعدی", callback_data="fun_riddle"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
        except Exception:
            pass
        return

    # 👇 بستن
    if action == "close":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "بسته شد")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(
            call.message.chat.id,
            "منوی اصلی:",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    bot.answer_callback_query(call.id)

    try:
        if action == "dice":
            n = roll_dice()
            emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
            bot.edit_message_text(
                f"🎲 <b>تاس</b>\n\n"
                f"{emojis[n-1]}  <b>{n}</b>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🎲 دوباره", callback_data="fun_dice"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "coin":
            result = flip_coin()
            bot.edit_message_text(
                f"🪙 <b>سکه</b>\n\n"
                f"{result}",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🪙 دوباره", callback_data="fun_coin"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "number":
            n = random_number(1, 100)
            bot.edit_message_text(
                f"🔢 <b>عدد تصادفی</b>\n\n"
                f"🎯 <b>{n}</b>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔢 دوباره", callback_data="fun_number"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "lottery":
            set_state(user_id, mode="fun", waiting_for="fun_lottery")
            try:
                bot.edit_message_text(
                    "🎯 <b>قرعه‌کشی</b>\n\n"
                    "گزینه‌ها رو با کاما (,) یا خط جدید جدا کن.\n\n"
                    "💡 مثال:\n"
                    "<code>علی، رضا، سارا، مریم</code>",
                    call.message.chat.id, call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                    )
                )
            except Exception:
                bot.send_message(call.message.chat.id, "🎯 گزینه‌ها رو بفرست:")
            return

        elif action == "joke":
            bot.edit_message_text(
                "⏳ در حال دریافت جوک...",
                call.message.chat.id, call.message.message_id
            )
            result = get_joke()
            if result.get("success"):
                bot.edit_message_text(
                    f"😂 <b>جوک</b>\n\n{result['joke']}",
                    call.message.chat.id, call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("😂 جوک بعدی", callback_data="fun_joke"),
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                    )
                )
                mark_user_used(user_id)
            else:
                bot.edit_message_text(
                    "❌ خطا در دریافت جوک.",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                    )
                )

        elif action == "hafez":
            bot.edit_message_text(
                "⏳ در حال گرفتن فال...",
                call.message.chat.id, call.message.message_id
            )
            result = get_hafez_fal()
            if result.get("success"):
                text = f"📖 <b>فال حافظ</b>\n━━━━━━━━━━━━━━━\n\n"
                text += f"<i>{result['poem']}</i>\n\n"
                if result.get("interpretation"):
                    text += f"💫 <b>تفسیر:</b>\n{result['interpretation']}"

                bot.edit_message_text(
                    text,
                    call.message.chat.id, call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("📖 فال بعدی", callback_data="fun_hafez"),
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                    )
                )
                mark_user_used(user_id)
            else:
                bot.edit_message_text(
                    "❌ خطا در گرفتن فال.",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                    )
                )

        elif action == "riddle":
            result = get_riddle()
            # پاسخ رو ذخیره کن
            set_state(user_id, fun_riddle_answer=result["answer"],
                      fun_riddle_question=result["question"])

            bot.edit_message_text(
                f"🧩 <b>معما</b>\n━━━━━━━━━━━━━━━\n\n"
                f"❓ {result['question']}\n\n"
                f"💡 <i>می‌تونی پاسخ رو ببینی یا معمای بعدی رو بزنی.</i>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup(row_width=2).add(
                    types.InlineKeyboardButton("👁 نمایش پاسخ", callback_data="fun_riddle_show"),
                    types.InlineKeyboardButton("🧩 معما بعدی", callback_data="fun_riddle"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "motivation":
            msg = get_motivation()
            bot.edit_message_text(
                f"💬 <b>جمله انگیزشی</b>\n━━━━━━━━━━━━━━━\n\n{msg}",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("💬 بعدی", callback_data="fun_motivation"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "color":
            result = random_color()
            r, g, b = result["rgb"]
            bot.edit_message_text(
                f"🎨 <b>رنگ تصادفی</b>\n━━━━━━━━━━━━━━━\n\n"
                f"🎨 نام: {result['name']}\n"
                f"🔹 HEX: <code>{result['hex']}</code>\n"
                f"🔸 RGB: <code>rgb({r}, {g}, {b})</code>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🎨 رنگ بعدی", callback_data="fun_color"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "today":
            result = get_today_info()
            text = (
                f"📅 <b>امروز</b>\n━━━━━━━━━━━━━━━\n\n"
                f"🇮🇷 <b>شمسی:</b> <code>{result['jalali']}</code>\n"
                f"🌍 <b>میلادی:</b> <code>{result['gregorian']}</code>\n"
                f"📆 <b>روز:</b> {result['weekday']}\n"
                f"🕐 <b>ساعت:</b> <code>{result['time']}</code>"
            )
            bot.edit_message_text(
                text,
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

        elif action == "food":
            food = what_to_eat()
            bot.edit_message_text(
                f"🍕 <b>چی بخوریم؟</b>\n━━━━━━━━━━━━━━━\n\n"
                f"امروز پیشنهاد می‌کنم:\n\n"
                f"<b>{food}</b>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🍕 دوباره", callback_data="fun_food"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="fun_back"),
                )
            )
            mark_user_used(user_id)

    except Exception as e:
        logger.exception("خطا در سرگرمی")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")


# ============================================================
# 🎯 قرعه‌کشی — دریافت ورودی
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "fun_lottery"
        and get_state(m.from_user.id).get("mode") == "fun"
        and m.text
        and not is_menu_button(m.text)
)
def fun_lottery_receive(message):
    user_id = message.from_user.id
    text = message.text.strip()

    # جدا کردن گزینه‌ها
    if "," in text or "،" in text:
        items = [x.strip() for x in text.replace("،", ",").split(",") if x.strip()]
    else:
        items = [x.strip() for x in text.splitlines() if x.strip()]

    if len(items) < 2:
        bot.send_message(message.chat.id, "⚠️ حداقل ۲ گزینه بفرست.")
        return

    winner = lottery(items)

    text_result = "🎯 <b>قرعه‌کشی</b>\n━━━━━━━━━━━━━━━\n\n"
    text_result += f"📋 <b>گزینه‌ها:</b> {len(items)}\n\n"
    for i, item in enumerate(items[:10], 1):
        emoji = "🏆" if item == winner else "▪️"
        text_result += f"{emoji} {item}\n"

    if len(items) > 10:
        text_result += f"... و {len(items) - 10} تا دیگه\n"

    text_result += f"\n🎉 <b>برنده:</b> <b>{winner}</b>"

    bot.send_message(message.chat.id, text_result, parse_mode='HTML')
    mark_user_used(user_id)

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))