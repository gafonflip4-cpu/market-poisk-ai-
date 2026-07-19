import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import os
import re

# ===== НАСТРОЙКИ =====
TG_TOKEN = os.getenv("BOT_TOKEN")
WB_REF_ID = os.getenv("WB_REF_ID", "partner123")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Хранилище для пагинации (в реальном проекте лучше использовать БД)
user_pages = {}

# ===== Flask-сервер для Render =====
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ===== Клавиатура с кнопками =====
def get_nav_keyboard(page: int, total_pages: int):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"page_{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

# ===== Telegram-бот =====
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👟 Привет! Я ищу кроссовки 42 размера до 3000 ₽.\n"
        "Просто отправь название модели (например, 'Nike Air Max') или бренда.\n\n"
        "🔍 Искать буду на Wildberries с реферальной ссылкой."
    )

@dp.message()
async def search_wb(message: types.Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Слишком короткий запрос. Напиши хотя бы 2 символа.")
        return

    # Добавляем размер в запрос для точности
    search_query = f"{query} 42 размер"
    search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&query={search_query}&page=1&ab_testing=false"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url) as resp:
                if resp.status != 200:
                    await message.answer("Ошибка поиска. Попробуй позже.")
                    return

                data = await resp.json()
                all_products = data.get("data", {}).get("products", [])

                # Фильтр по цене ДО 3000 руб.
                filtered = []
                for p in all_products:
                    price = p.get("priceU", 0) / 100
                    if price <= 3000:
                        filtered.append(p)

                if not filtered:
                    await message.answer("😕 Ничего не найдено до 3000 ₽ с 42 размером. Попробуй другой запрос.")
                    return

                # Сохраняем результаты для пагинации
                user_id = message.from_user.id
                user_pages[user_id] = {
                    "products": filtered,
                    "total_pages": (len(filtered) + 4) // 5  # по 5 товаров на страницу
                }

                # Показываем первую страницу
                await show_page(message, user_id, 0)

        except Exception as e:
            await message.answer(f"Ошибка: {e}")

async def show_page(message: types.Message, user_id: int, page: int):
    data = user_pages.get(user_id)
    if not data:
        await message.answer("Данные устарели. Отправь запрос заново.")
        return

    products = data["products"]
    total_pages = data["total_pages"]
    start = page * 5
    end = min(start + 5, len(products))
    page_products = products[start:end]

    result = f"🔍 Страница {page+1} из {total_pages}\n\n"
    for p in page_products:
        name = p.get("name", "Без названия")
        price = p.get("priceU", 0) / 100
        rating = p.get("rating", 0)
        article = p.get("id", "")
        link = f"https://www.wildberries.ru/catalog/{article}/detail.aspx?targetUrl=partner&ref={WB_REF_ID}"

        result += f"📦 {name[:50]}\n"
        result += f"💰 {price:.0f} ₽ | ⭐ {rating}\n"
        result += f"🔗 {link}\n\n"

    keyboard = get_nav_keyboard(page, total_pages)
    if keyboard:
        await message.answer(result, reply_markup=keyboard)
    else:
        await message.answer(result)

# ===== Обработка нажатий на кнопки =====
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    if callback.data.startswith("page_"):
        page = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        await show_page(callback.message, user_id, page)
        await callback.answer()  # Убираем "часики"

# ===== Запуск =====
async def main():
    print("✅ Бот запущен и работает...")
    threading.Thread(target=run_flask).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
