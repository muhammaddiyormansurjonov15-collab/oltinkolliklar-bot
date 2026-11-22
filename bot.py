"""Oltinkolliklar Telegram boti.

Ishga tushirish:
    pip install -r requirements.txt
    BOT_TOKEN=... SITE_URL=https://sizning-sayt.uz ADMIN_ID=123456789 python bot.py
"""
import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

SITE_URL = os.environ.get("SITE_URL", "https://example.com")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # fikrlar shu ID ga keladi

# ---------------------------------------------------------------- baza
db = sqlite3.connect("oltinkolliklar.db")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')")
db.execute(
    "CREATE TABLE IF NOT EXISTS ads ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, "
    "created TEXT DEFAULT CURRENT_TIMESTAMP)"
)
db.commit()


def get_lang(uid: int) -> str:
    row = db.execute("SELECT lang FROM users WHERE id = ?", (uid,)).fetchone()
    return row[0] if row else "uz"


def set_lang(uid: int, lang: str) -> None:
    db.execute(
        "INSERT INTO users (id, lang) VALUES (?, ?) "
        "ON CONFLICT(id) DO UPDATE SET lang = excluded.lang",
        (uid, lang),
    )
    db.commit()


# ---------------------------------------------------------------- matnlar
BTN = {
    "uz": {
        "kafe": "🍽 Kafelar", "kommunal": "⚡ Kommunal", "usta": "🔧 Ustalar",
        "bozor": "🛍 Bozor", "taksi": "🚕 Taksi", "fav": "🚑 Favqulodda",
        "ads": "📋 E'lonlarim", "feedback": "💬 Fikr / Yordam", "about": "ℹ️ Haqida",
        "settings": "⚙️ Sozlamalar", "lang": "🌐 Til / Язык", "portal": "📱 Portalni ochish",
    },
    "ru": {
        "kafe": "🍽 Кафе", "kommunal": "⚡ Коммунальные", "usta": "🔧 Мастера",
        "bozor": "🛍 Базар", "taksi": "🚕 Такси", "fav": "🚑 Экстренные",
        "ads": "📋 Мои объявления", "feedback": "💬 Отзыв / Помощь", "about": "ℹ️ О проекте",
        "settings": "⚙️ Настройки", "lang": "🌐 Til / Язык", "portal": "📱 Открыть портал",
    },
}

# Bo'limlar matnini shu yerda tahrirlang. Real raqamlar tayyor bo'lsa, shu yerga qo'shing.
SOON = {
    "uz": "Bu bo'limga ma'lumotlar tez orada qo'shiladi. Hozircha portaldan qidirib ko'ring.",
    "ru": "Данные для этого раздела скоро появятся. Пока попробуйте поиск на портале.",
}
SECTIONS = {
    "kafe": SOON, "kommunal": SOON, "usta": SOON, "bozor": SOON, "taksi": SOON,
    "fav": {
        "uz": "🚑 Favqulodda raqamlar\n\nTez yordam: 103\nPolitsiya: 102\nO't o'chirish: 101\nGaz avariya: 104",
        "ru": "🚑 Экстренные номера\n\nСкорая помощь: 103\nПолиция: 102\nПожарная: 101\nГаз (авария): 104",
    },
}

T = {
    "uz": {
        "hello": "Oltinkolliklar portaliga xush kelibsiz! Kerakli bo'limni tanlang 👇",
        "about": "Oltinkolliklar: Oltinko'l tumani uchun kafe, kommunal xizmat, usta va e'lonlar bitta joyda.",
        "ads_menu": "📋 E'lonlarim",
        "ad_new": "➕ Yangi e'lon", "ad_list": "📋 Mening e'lonlarim",
        "ad_ask": "E'lon matnini yozing (narx va telefon raqamingiz bilan):",
        "ad_saved": "✅ E'lon saqlandi.",
        "ad_none": "Sizda hali e'lon yo'q.",
        "ad_del": "🗑 O'chirish", "ad_deleted": "E'lon o'chirildi.",
        "ad_long": "Matn juda uzun. 1000 belgidan oshmasin.",
        "fb_ask": "Fikr yoki savolingizni yozing:",
        "fb_ok": "Rahmat! Xabaringiz yuborildi.",
        "settings": "⚙️ Sozlamalar\n\nTil: O'zbekcha",
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_set": "Til o'zgartirildi.",
    },
    "ru": {
        "hello": "Добро пожаловать на портал Oltinkolliklar! Выберите раздел 👇",
        "about": "Oltinkolliklar: кафе, коммунальные службы, мастера и объявления Алтынкульского района в одном месте.",
        "ads_menu": "📋 Мои объявления",
        "ad_new": "➕ Новое объявление", "ad_list": "📋 Мои объявления",
        "ad_ask": "Напишите текст объявления (с ценой и номером телефона):",
        "ad_saved": "✅ Объявление сохранено.",
        "ad_none": "У вас пока нет объявлений.",
        "ad_del": "🗑 Удалить", "ad_deleted": "Объявление удалено.",
        "ad_long": "Текст слишком длинный. Не более 1000 символов.",
        "fb_ask": "Напишите ваш отзыв или вопрос:",
        "fb_ok": "Спасибо! Сообщение отправлено.",
        "settings": "⚙️ Настройки\n\nЯзык: Русский",
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_set": "Язык изменён.",
    },
}


def menu_kb(lang: str) -> ReplyKeyboardMarkup:
    b = BTN[lang]
    rows = [
        [b["kafe"], b["kommunal"]],
        [b["usta"], b["bozor"]],
        [b["taksi"], b["fav"]],
        [b["ads"], b["feedback"]],
        [b["about"], b["settings"]],
    ]
    keyboard = [[KeyboardButton(text=t) for t in row] for row in rows]
    keyboard.append([KeyboardButton(text=b["lang"])])
    keyboard.append([KeyboardButton(text=b["portal"], web_app=WebAppInfo(url=SITE_URL))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def is_btn(key: str):
    return F.text.in_({BTN["uz"][key], BTN["ru"][key]})


class AdForm(StatesGroup):
    text = State()


class Feedback(StatesGroup):
    text = State()


router = Router()


# ---------------------------------------------------------------- buyruqlar va menyu
@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    lang = get_lang(m.from_user.id)
    set_lang(m.from_user.id, lang)
    await m.answer(T[lang]["hello"], reply_markup=menu_kb(lang))


def section_handler(key: str):
    async def handler(m: Message, state: FSMContext):
        await state.clear()
        lang = get_lang(m.from_user.id)
        await m.answer(SECTIONS[key][lang])

    return handler


for _key in SECTIONS:
    router.message.register(section_handler(_key), is_btn(_key))


@router.message(is_btn("about"))
async def about(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(T[get_lang(m.from_user.id)]["about"])


@router.message(is_btn("settings"))
async def settings(m: Message, state: FSMContext):
    await state.clear()
    lang = get_lang(m.from_user.id)
    await m.answer(T[lang]["settings"])


@router.message(is_btn("lang"))
async def choose_lang(m: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
    ]])
    await m.answer(T[get_lang(m.from_user.id)]["choose_lang"], reply_markup=kb)


@router.callback_query(F.data.startswith("lang:"))
async def set_language(c: CallbackQuery):
    lang = c.data.split(":")[1]
    if lang not in T:
        return await c.answer()
    set_lang(c.from_user.id, lang)
    await c.message.answer(T[lang]["lang_set"], reply_markup=menu_kb(lang))
    await c.answer()


# ---------------------------------------------------------------- e'lonlarim
@router.message(is_btn("ads"))
async def ads_menu(m: Message, state: FSMContext):
    await state.clear()
    t = T[get_lang(m.from_user.id)]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["ad_new"], callback_data="ad:new")],
        [InlineKeyboardButton(text=t["ad_list"], callback_data="ad:list")],
    ])
    await m.answer(t["ads_menu"], reply_markup=kb)


@router.callback_query(F.data == "ad:new")
async def ad_new(c: CallbackQuery, state: FSMContext):
    await state.set_state(AdForm.text)
    await c.message.answer(T[get_lang(c.from_user.id)]["ad_ask"])
    await c.answer()


@router.callback_query(F.data == "ad:list")
async def ad_list(c: CallbackQuery):
    t = T[get_lang(c.from_user.id)]
    rows = db.execute(
        "SELECT id, text FROM ads WHERE user_id = ? ORDER BY id DESC LIMIT 20", (c.from_user.id,)
    ).fetchall()
    if not rows:
        await c.message.answer(t["ad_none"])
    for ad_id, text in rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t["ad_del"], callback_data=f"ad:del:{ad_id}")
        ]])
        await c.message.answer(text, reply_markup=kb)
    await c.answer()


@router.callback_query(F.data.startswith("ad:del:"))
async def ad_delete(c: CallbackQuery):
    ad_id = int(c.data.split(":")[2])
    db.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (ad_id, c.from_user.id))
    db.commit()
    await c.message.edit_text(T[get_lang(c.from_user.id)]["ad_deleted"])
    await c.answer()


# ---------------------------------------------------------------- fikr / yordam
@router.message(is_btn("feedback"))
async def feedback_start(m: Message, state: FSMContext):
    await state.set_state(Feedback.text)
    await m.answer(T[get_lang(m.from_user.id)]["fb_ask"])


# ---------------------------------------------------------------- holatdagi matnlar
# Menyu tugmalari yuqorida ro'yxatdan o'tgan, shuning uchun ular holatni tozalaydi.
@router.message(AdForm.text, F.text)
async def ad_save(m: Message, state: FSMContext):
    t = T[get_lang(m.from_user.id)]
    if len(m.text) > 1000:
        return await m.answer(t["ad_long"])
    db.execute("INSERT INTO ads (user_id, text) VALUES (?, ?)", (m.from_user.id, m.text))
    db.commit()
    await state.clear()
    await m.answer(t["ad_saved"])


@router.message(Feedback.text, F.text)
async def feedback_send(m: Message, state: FSMContext):
    await state.clear()
    if ADMIN_ID:
        name = m.from_user.full_name
        username = f"@{m.from_user.username}" if m.from_user.username else "-"
        await m.bot.send_message(
            ADMIN_ID, f"💬 Fikr\n{name} ({username}, id {m.from_user.id}):\n\n{m.text}"
        )
    await m.answer(T[get_lang(m.from_user.id)]["fb_ok"])


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(os.environ["BOT_TOKEN"])
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
