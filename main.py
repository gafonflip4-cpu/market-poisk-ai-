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
    
