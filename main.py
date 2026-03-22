import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, logger
from database import db
from steam_api import steam_api
from sale_db import sale_tracker, real_sale_checker


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()




# Команды бота
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    db.add_user(user_id, username)

    welcome_text = """
🎮 <b>Steam Discount Bot</b>

Я помогу тебе отслеживать скидки на игры в Steam!

Также я имею отправлять уведомления, когда начнется крупная распродажа.

    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти игру", callback_data="search_game"), InlineKeyboardButton(text='💬Получать уведомления',callback_data='get_notify')],
        [InlineKeyboardButton(text="🔥 Горячие скидки", callback_data="hot_deals"),InlineKeyboardButton(text='📉Топ скидок недели', callback_data='top_games')],
        [InlineKeyboardButton(text="🎮 Мои игры", callback_data="my_games"), InlineKeyboardButton(text='💸Поддержать разработчика', callback_data='support_author')],

    ])

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')


@dp.callback_query(F.data == 'search_game')
async def cmd_search(call: CallbackQuery):
    await call.message.answer(
        "🔍 <b>Поиск игр в Steam</b>\n\n"
        "Введите название игры для поиска:\n\n"
        "<i>Примеры:</i>\n"
        "<code>Counter-Strike</code>\n"
        "<code>The Witcher 3</code>\n"
        "<code>Cyberpunk 2077</code>",
        parse_mode='HTML'
    )
    await call.answer()


@dp.callback_query(F.data == 'my_games')
async def cmd_mygames(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"🔍 Команда /mygames от пользователя {user_id}")

    tracked_games = db.get_tracked_games(user_id)
    logger.info(f"📊 Найдено игр в базе для user_id={user_id}: {len(tracked_games)}")

    if tracked_games:
        for game_id, game_name in tracked_games:
            logger.info(f"🎮 Игра в базе: ID={game_id}, Name={game_name}")

    if not tracked_games:
        await call.message.answer(
            "📋 <b>У вас нет отслеживаемых игр</b>\n\n"
            "Используйте команду /search чтобы добавить игры для отслеживания скидок!",
            parse_mode='HTML'
        )
        return

    text = "📋 <b>Ваши отслеживаемые игры:</b>\n\n"
    keyboard_buttons = []

    for i, (game_id, game_name) in enumerate(tracked_games, 1):
        logger.info(f"🎮 Обрабатываем игру {i}: ID={game_id}, Name={game_name}")

        # Получаем актуальную информацию об игре для отображения цены
        game_details = await steam_api.get_game_details(game_id)

        if game_details:
            if game_details['is_free']:
                price_info = " 🆓 Бесплатно"
            elif game_details['discount'] > 0:
                price_info = f" 💰 {game_details['final_price']:,.0f} руб (-{game_details['discount']}%)"
            else:
                price_info = f" 💰 {game_details['final_price']:,.0f} руб"
        else:
            price_info = " ⚠️ Не удалось загрузить данные"

        text += f"{i}. <b>{game_name}</b>{price_info}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"❌ Удалить {game_name[:15]}",
                callback_data=f"remove_{game_id}"
            )
        ])

    keyboard_buttons.append([InlineKeyboardButton(text="🔍 Добавить еще", callback_data="search_game")])

    logger.info(f"📝 Отправляем сообщение с {len(tracked_games)} играми для user_id={user_id}")
    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons), parse_mode='HTML')
    await call.answer()



@dp.callback_query(F.data == 'hot_deals')
async def cmd_deals(call: CallbackQuery):
    await call.message.answer("🔄 <b>Ищу горячие скидки...</b>", parse_mode='HTML')

    deals = await steam_api.get_featured_deals()

    if not deals:
        await call.message.answer("😔 <b>Не удалось загрузить акционные предложения</b>", parse_mode='HTML')
        return

    text = "🔥 <b>Горячие скидки в Steam:</b>\n\n"

    for deal in deals:
        text += (
            f"🎮 <b>{deal['name']}</b>\n"
            f"💰 <s>{deal['original_price']:,.0f} руб</s> → {deal['final_price']:,.0f} руб\n"
            f"🎯 Скидка: <b>-{deal['discount']}%</b>\n"
            f"🔗 https://store.steampowered.com/app/{deal['id']}/\n\n"
        )

    await call.message.answer(text, disable_web_page_preview=True, parse_mode='HTML')
    await call.answer()


@dp.callback_query(F.data == 'top_games')
async def cmd_top(call: CallbackQuery):
    await call.message.answer(
        "🔥 <b>Топ скидок недели</b>\n\n"
        "🔄 <i>Функция в разработке...</i>\n\n",

        parse_mode='HTML'
    )
    await call.answer()




@dp.callback_query(F.data == 'support_author')
async def cmd_donate(call: CallbackQuery):
    donate_text = '❌Функция пока недоступна'


    await call.message.answer(donate_text, parse_mode='HTML')
    await call.answer()


# Обработка поиска игр
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_search_query(message: types.Message):
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос", parse_mode='HTML')
        return

    await message.answer(f"🔍 <b>Ищу</b> \"{query}\" <b>в Steam...</b>", parse_mode='HTML')

    games = await steam_api.search_games(query)

    if not games:
        await message.answer("😔 <b>Игры не найдены</b>\n\nПопробуйте другой запрос", parse_mode='HTML')
        return

    text = f"🎮 <b>Найдено игр по запросу</b> \"{query}\":\n\n"
    keyboard_buttons = []

    for game in games[:8]:  # Показываем первые 8 результатов
        game_name = game.get('name', 'Unknown')
        game_id = game.get('appid')

        if game_id and game_name != 'Unknown':
            # Получаем актуальную цену для отображения
            game_details = await steam_api.get_game_details(game_id)
            if game_details:
                if game_details['is_free']:
                    price_text = " 🆓 Бесплатно"
                elif game_details['discount'] > 0:
                    price_text = f" 💰 {game_details['final_price']:,.0f} руб (-{game_details['discount']}%)"
                else:
                    price_text = f" 💰 {game_details['final_price']:,.0f} руб"
            else:
                price_text = ""

            text += f"• {game_name}{price_text}\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📌 {game_name[:25]}",
                    callback_data=f"track_{game_id}"
                )
            ])

    if not keyboard_buttons:
        await message.answer("😔 <b>Не удалось найти подходящие игры</b>", parse_mode='HTML')
        return

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode='HTML'
    )


# Обработка callback кнопок
@dp.callback_query(F.data.startswith("track_"))
async def track_game(callback: types.CallbackQuery):
    game_id = int(callback.data.replace("track_", ""))

    # Получаем детали игры
    game_details = await steam_api.get_game_details(game_id)

    if not game_details:
        await callback.answer("❌ Не удалось получить информацию об игре")
        return

    user_id = callback.from_user.id
    game_name = game_details['name']

    # Добавляем в отслеживаемые
    db.track_game(user_id, game_id, game_name)

    # Формируем ответ с ПРАВИЛЬНЫМИ ценами
    if game_details['is_free']:
        response = (
            f"✅ <b>Игра добавлена в отслеживаемые!</b>\n\n"
            f"🎮 <b>{game_name}</b>\n"
            f"💰 <b>БЕСПЛАТНО</b>\n\n"
            f"<i>Вы получите уведомление, если игра станет платной</i>"
        )
    elif game_details['discount'] > 0:
        response = (
            f"✅ <b>Игра добавлена в отслеживаемые!</b>\n\n"
            f"🎮 <b>{game_name}</b>\n"
            f"🎯 <b>Текущая скидка: -{game_details['discount']}%</b>\n"
            f"💰 <s>{game_details['initial_price']:,.0f} руб</s> → {game_details['final_price']:,.0f} руб\n\n"
            f"<i>Вы получите уведомление, когда скидка изменится</i>"
        )
    else:
        response = (
            f"✅ <b>Игра добавлена в отслеживаемые!</b>\n\n"
            f"🎮 <b>{game_name}</b>\n"
            f"💰 Цена: {game_details['final_price']:,.0f} руб\n"
            f"📉 Скидки сейчас нет\n\n"
            f"<i>Вы получите уведомление, когда игра подешевеет</i>"
        )

    await callback.message.edit_text(response, parse_mode='HTML')
    await callback.answer()


@dp.callback_query(F.data.startswith("remove_"))
async def remove_game(callback: types.CallbackQuery):
    game_id = int(callback.data.replace("remove_", ""))
    user_id = callback.from_user.id

    db.remove_tracked_game(user_id, game_id)

    await callback.answer("✅ Игра удалена из отслеживаемых")
    await callback.message.edit_text(
        "✅ <b>Игра удалена из отслеживаемых</b>\n\n",
        parse_mode='HTML'
    )


# Фоновая задача для проверки скидок
async def check_discounts():
    """Проверяет скидки каждые 6 часов"""
    while True:
        try:
            logger.info("Checking for discounts...")

            all_users = db.get_all_users()
            if not all_users:
                await asyncio.sleep(6 * 3600)  # 6 часов
                continue

            for user_id in all_users:
                tracked_games = db.get_tracked_games(user_id)

                for game_id, game_name in tracked_games:
                    # Проверяем, не отправляли ли уже уведомление
                    if db.was_deal_sent(user_id, game_id):
                        continue

                    game_details = await steam_api.get_game_details(game_id)
                    if game_details and game_details.get('discount', 0) > 0:
                        # Отправляем уведомление о скидке с ПРАВИЛЬНЫМИ ценами
                        discount = game_details['discount']

                        message_text = (
                            f"🎉 <b>СКИДКА!</b>\n\n"
                            f"🎮 <b>{game_name}</b>\n"
                            f"🎯 Скидка: <b>-{discount}%</b>\n"
                            f"💰 <s>{game_details['initial_price']:,.0f} руб</s> → {game_details['final_price']:,.0f} руб\n"
                            f"🔗 {game_details['steam_url']}\n\n"
                            f"<i>Не упусти выгоду! 🏃‍♂️</i>"
                        )

                        try:
                            await bot.send_message(
                                user_id,
                                message_text,
                                disable_web_page_preview=True,
                                parse_mode='HTML'
                            )
                            db.mark_deal_sent(user_id, game_id)
                            await asyncio.sleep(1)  # Пауза между сообщениями
                        except Exception as e:
                            logger.error(f"Failed to send message to {user_id}: {e}")

            await asyncio.sleep(6 * 3600)  # Проверяем каждые 6 часов

        except Exception as e:
            logger.error(f"Discount check error: {e}")
            await asyncio.sleep(3600)  # Ждем 1 час при ошибке




async def monitor_sales_continuously():
    """Непрерывно мониторит распродажи и отправляет уведомления всем пользователям"""
    logger.info("🚀 Начинаем авто-мониторинг крупных распродаж Steam...")

    while True:
        try:
            # Проверяем активные распродажи
            active_sales = await real_sale_checker.check_active_sales()

            # Находим новые распродажи (которые только что начались)
            new_sales = []
            for sale in active_sales:
                if not sale_tracker.was_notification_sent(sale['id']):
                    new_sales.append(sale)
                    logger.info(f"🆕 Новая распродажа: {sale['name']}")

            # Отправляем уведомления о новых распродажах всем пользователям
            if new_sales:
                await send_sale_notifications_to_all(new_sales)

                # Помечаем как отправленные
                for sale in new_sales:
                    sale_tracker.mark_notification_sent(sale['id'], sale['name'])

            # Ждем перед следующей проверкой
            current_month = datetime.now().month
            if current_month in [12, 1, 6, 7, 11, 10]:  # Сезоны распродаж
                wait_time = 3600  # 1 час в сезон распродаж
            else:
                wait_time = 7200  # 2 часа в обычное время

            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"❌ Ошибка в мониторинге распродаж: {e}")
            await asyncio.sleep(3600)


async def send_sale_notifications_to_all(sales):
    """Отправляет уведомления о начале распродаж всем пользователям"""
    if not db.get_notification_users():
        logger.warning("⚠️ Нет пользователей для отправки уведомлений")
        return

    for sale in sales:
        notification_text = f"""
🎉 <b>СТАРТОВАЛА КРУПНАЯ РАСПРОДАЖА В STEAM!</b>

{sale['name']}

🔥 <b>Что вас ждет:</b>
• Тысячи игр со скидками до 90%
• Ежедневные предложения и акции
• Стикеры, достижения и карточки
• Специальные скидки на бестселлеры

🛒 <a href="{sale['url']}">Перейти к распродаже →</a>

⏰ <i>Успейте найти лучшие предложения!</i>

<code>Бот автоматически отслеживает распродажи</code>
        """

        success_count = 0
        for user_id in db.get_notification_users():
            try:
                await bot.send_message(
                    user_id,
                    notification_text,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                success_count += 1
                logger.info(f"✅ Уведомление отправлено пользователю {user_id}")
                await asyncio.sleep(0.1)  # Небольшая задержка между сообщениями
            except Exception as e:
                logger.error(f"❌ Не удалось отправить уведомление пользователю {user_id}: {e}")

        logger.info(
            f"📨 Уведомления о {sale['name']} отправлены {success_count}/{len(db.get_notification_users())} пользователям")





# Команда для добавления пользователя в список уведомлений
@dp.callback_query(F.data == 'get_notify')
async def cmd_add_me(call: CallbackQuery):
    """Добавляет пользователя в список для уведомлений"""
    user_id = call.from_user.id

    if user_id not in db.get_notification_users():
        db.add_notification_user(user_id)
        await call.message.answer(
            "✅ <b>Вы добавлены в список уведомлений!</b>\n\n"
            "Теперь вы будете получать автоматические уведомления о начале крупных распродаж Steam.\n\n"
            "🤖 <i>Бот проверяет распродажи каждые 1-2 часа</i>",
            parse_mode='HTML'
        )
        logger.info(f"➕ Пользователь {user_id} добавлен в список уведомлений")
    else:
        await call.message.answer(
            "ℹ️ <b>Вы уже в списке уведомлений!</b>\n\n"
            "Вы будете получать автоматические уведомления о распродажах.",
            parse_mode='HTML'
        )
    await call.answer()


async def main():
    # Запускаем фоновые задачи
    asyncio.create_task(check_discounts())
    asyncio.create_task(monitor_sales_continuously())

    logger.info("Steam Discount Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())