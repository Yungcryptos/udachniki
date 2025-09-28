# -*- coding: utf-8 -*-
import logging
import json
import os
import asyncio
from datetime import datetime, date
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters

# Импортируем настройки из config.py
import config

# Настройка логирования чтобы видеть ошибки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === СИСТЕМА РАБОТЫ С ДАННЫМИ ПОЛЬЗОВАТЕЛЕЙ (JSON) ===

def load_users():
    """Загружает данные пользователей из JSON-файла."""
    if os.path.exists(config.USER_DATA_FILE):
        with open(config.USER_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    """Сохраняет данные пользователей в JSON-файл."""
    with open(config.USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def get_user_data(user_id):
    """Возвращает данные пользователя. Создает нового, если не существует."""
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        # Создаем нового пользователя
        users[user_id_str] = {
            'username': '',
            'balance': config.REGISTRATION_BONUS, # Выдаем регистрационный бонус
            'last_bonus_date': None # Дата последнего получения бонуса
        }
        save_users(users)
        logging.info(f"Создан новый пользователь: {user_id}")
    
    return users[user_id_str]

def update_user_data(user_id, data):
    """Обновляет данные пользователя."""
    users = load_users()
    user_id_str = str(user_id)
    users[user_id_str].update(data)
    save_users(users)

# === ОСНОВНЫЕ КОМАНДЫ БОТА ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start. Приветствует и регистрирует пользователя."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    # Сохраняем username, если его еще нет
    if not user_data.get('username') and user.username:
        update_user_data(user.id, {'username': user.username})
    
    # Формируем приветственное сообщение
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        f"Добро пожаловать в наше казино! 🎰\n"
        f"Твой стартовый бонус: {config.REGISTRATION_BONUS} Stars! ⭐\n\n"
        f"💎 <b>Приведи друга и получи 100 Stars!</b>\n"
        f"Просто отправь ему эту ссылку:\n"
        f"https://t.me/ВашБот?start=ref_{user.id}\n\n"
        f"<b>Доступные команды:</b>\n"
        f"/game - 🎲 Сыграть в кости\n"
        f"/balance - 💰 Мой баланс\n"
        f"/bonus - 🎁 Получить ежедневный бонус\n"
        f"/buy - 💵 Купить еще Stars\n\n"
        f"<i>Удачи! Пусть фортуна будет на твоей стороне!</i> 🍀"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /balance. Показывает текущий баланс."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    balance_text = (
        f"💰 <b>Твой баланс:</b> {user_data['balance']} Stars\n\n"
        f"Хочешь пополнить? Используй /buy"
    )
    await update.message.reply_html(balance_text)

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /bonus. Выдает ежедневный бонус."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    today = date.today().isoformat()
    last_bonus_date = user_data.get('last_bonus_date')
    
    if last_bonus_date == today:
        # Бонус уже получали сегодня
        bonus_text = "❌ Ты уже получал сегодняшний бонус. Возвращайся завтра!"
        await update.message.reply_html(bonus_text)
        return
    
    # Начисляем бонус (0 Stars)
    new_balance = user_data['balance'] + config.DAILY_BONUS
    update_user_data(user.id, {
        'balance': new_balance,
        'last_bonus_date': today
    })
    
    bonus_text = (
        f"🎁 Поздравляем! Ты получил ежедневный бонус:\n"
        f"+{config.DAILY_BONUS} Stars!\n\n"
        f"💰 <b>Твой новый баланс:</b> {new_balance} Stars"
    )
    await update.message.reply_html(bonus_text)

# === ИГРОВАЯ МЕХАНИКА "КУБИК" ===

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /game. Предлагает сделать ставку."""
    user_data = get_user_data(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("5 Stars", callback_data="bet_5")],
        [InlineKeyboardButton("10 Stars", callback_data="bet_10")],
        [InlineKeyboardButton("25 Stars", callback_data="bet_25")],
        [InlineKeyboardButton("50 Stars", callback_data="bet_50")],
        [InlineKeyboardButton("100 Stars", callback_data="bet_100")],
        [InlineKeyboardButton("Другая сумма", callback_data="custom_bet")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"🎲 <b>Игра в Кости</b>\n\n"
        f"Правила:\n"
        f"• Ставь Stars и бросай кубик\n"
        f"• Выпадает 6 - победа 🎉 (x{config.WIN_MULTIPLIER})\n"
        f"• Выпадает 1-5 - проигрыш 😢\n\n"
        f"💰 <b>Твой баланс:</b> {user_data['balance']} Stars\n"
        f"Выбери ставку:",
        reply_markup=reply_markup
    )

async def handle_bet_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор ставки из кнопок."""
    query = update.callback_query
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    user_balance = user_data['balance']
    
    if query.data == "custom_bet":
        # Запрос произвольной ставки
        await query.edit_message_text(
            f"💎 Введи свою ставку (от {config.MIN_BET} до {config.MAX_BET} Stars):\n"
            f"💰 Твой баланс: {user_balance} Stars"
        )
        # Устанавливаем состояние ожидания ввода ставки
        context.user_data['waiting_for_bet'] = True
        return
    
    # Обрабатываем стандартные ставки из кнопок
    bet_amount = int(query.data.split('_')[1])
    
    if bet_amount > user_balance:
        await query.edit_message_text(f"❌ Недостаточно Stars! Твой баланс: {user_balance} Stars")
        return
    
    if bet_amount < config.MIN_BET or bet_amount > config.MAX_BET:
        await query.edit_message_text(f"❌ Ставка должна быть от {config.MIN_BET} до {config.MAX_BET} Stars")
        return
    
    # Запускаем игру с выбранной ставкой
    await play_dice_game(query, context, bet_amount)

async def handle_custom_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает произвольную ставку, введенную пользователем."""
    if not context.user_data.get('waiting_for_bet'):
        return
    
    user_data = get_user_data(update.effective_user.id)
    user_balance = user_data['balance']
    
    try:
        bet_amount = int(update.message.text)
        
        if bet_amount < config.MIN_BET:
            await update.message.reply_html(f"❌ Минимальная ставка: {config.MIN_BET} Stars")
            return
        if bet_amount > config.MAX_BET:
            await update.message.reply_html(f"❌ Максимальная ставка: {config.MAX_BET} Stars")
            return
        if bet_amount > user_balance:
            await update.message.reply_html(f"❌ Недостаточно Stars! Твой баланс: {user_balance} Stars")
            return
        
        # Сбрасываем состояние ожидания
        context.user_data['waiting_for_bet'] = False
        
        # Запускаем игру
        await play_dice_game_from_message(update, context, bet_amount)
        
    except ValueError:
        await update.message.reply_html("❌ Пожалуйста, введи число!")

async def play_dice_game(query, context, bet_amount):
    """Запускает игру в кости из callback query."""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    # Списываем ставку
    new_balance = user_data['balance'] - bet_amount
    update_user_data(user_id, {'balance': new_balance})
    
    # Отправляем анимацию кубика
    message = await context.bot.send_dice(
        chat_id=query.message.chat_id,
        emoji='🎲',
        reply_to_message_id=query.message.message_id
    )
    
    # Ждем завершения анимации (3-4 секунды)
    await asyncio.sleep(4)
    
    # Обрабатываем результат
    dice_value = message.dice.value
    await process_game_result(context, user_id, bet_amount, dice_value, message.chat_id, message.message_id)

async def play_dice_game_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount):
    """Запускает игру в кости из текстового сообщения."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    # Списываем ставку
    new_balance = user_data['balance'] - bet_amount
    update_user_data(user_id, {'balance': new_balance})
    
    # Отправляем анимацию кубика
    message = await context.bot.send_dice(
        chat_id=update.effective_chat.id,
        emoji='🎲'
    )
    
    # Ждем завершения анимации (3-4 секунды)
    await asyncio.sleep(4)
    
    # Обрабатываем результат
    dice_value = message.dice.value
    await process_game_result(context, user_id, bet_amount, dice_value, message.chat_id, message.message_id)

async def process_game_result(context, user_id, bet_amount, dice_value, chat_id, message_id):
    """Обрабатывает результат броска кубика."""
    user_data = get_user_data(user_id)
    current_balance = user_data['balance']
    
    # Проверяем результат по настройкам из config.py
    if dice_value in config.WINNING_DICE_VALUES:
        # ПОБЕДА
        win_amount = bet_amount * config.WIN_MULTIPLIER
        new_balance = current_balance + win_amount
        update_user_data(user_id, {'balance': new_balance})
        
        result_text = (
            f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
            f"🎲 Выпало: {dice_value}\n"
            f"💰 Ставка: {bet_amount} Stars\n"
            f"🏆 Выигрыш: {win_amount} Stars (x{config.WIN_MULTIPLIER})\n"
            f"💎 Новый баланс: {new_balance} Stars\n\n"
            f"<i>Удача на твоей стороне! 🍀</i>"
        )
    else:
        # ПРОИГРЫШ
        result_text = (
            f"😢 <b>ПРОИГРЫШ</b>\n\n"
            f"🎲 Выпало: {dice_value}\n"
            f"💰 Ставка: {bet_amount} Stars\n"
            f"💎 Твой баланс: {current_balance} Stars\n\n"
            f"<i>Попробуй еще раз! Удача ждет тебя! ✨</i>"
        )
    
    # Отправляем результат игры
    await context.bot.send_message(
        chat_id=chat_id,
        text=result_text,
        reply_to_message_id=message_id,
        parse_mode='HTML'
    )

# === СИСТЕМА ОПЛАТЫ ЧЕРЕЗ TELEGRAM STARS ===

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /buy. Предлагает купить Stars."""
    # Создаем инвойс (счет) для оплаты через Stars
    chat_id = update.effective_chat.id
    title = "Покупка Stars для казино"
    description = f"Пополнение баланса. Курс: 1 Stars = {config.STARS_TO_COINS_RATE} Stars"
    
    # Выбираем варианты пополнения
    payload = "CASINO_PAYMENT"  # Уникальный идентификатор платежа
    provider_token = "XTR"  # Для Telegram Stars используется "XTR"
    currency = "XTR"  # Валюта Telegram Stars
    prices = [LabeledPrice("100 Stars", 100)]  # Цена в Stars (100 Stars = 100 Stars по нашему курсу 1:1)
    
    # Отправляем инвойс
    await context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        provider_token,
        currency,
        prices,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        is_flexible=False,
        start_parameter="casino-deposit"
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает предварительный запрос на оплату."""
    query = update.pre_checkout_query
    # Проверяем payload, можно добавить дополнительную валидацию
    if query.invoice_payload != 'CASINO_PAYMENT':
        await query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает успешный платеж."""
    user = update.effective_user
    payment = update.message.successful_payment
    
    # Рассчитываем количество Stars (Total_amount / 100 * курс)
    # Telegram передает сумму в центах/копейках, поэтому делим на 100
    stars_amount = payment.total_amount / 100
    coins_to_add = int(stars_amount * config.STARS_TO_COINS_RATE)
    
    # Зачисляем Stars на баланс
    user_data = get_user_data(user.id)
    new_balance = user_data['balance'] + coins_to_add
    update_user_data(user.id, {'balance': new_balance})
    
    payment_text = (
        f"✅ <b>Платеж успешно завершен!</b>\n\n"
        f"💳 Оплачено: {stars_amount} Stars\n"
        f"🎰 Зачислено: {coins_to_add} Stars\n\n"
        f"💰 <b>Твой новый баланс:</b> {new_balance} Stars\n\n"
        f"Удачи в игре! 🍀"
    )
    
    await update.message.reply_html(payment_text)

# === ЗАПУСК И НАСТРОЙКА БОТА ===

def main():
    """Запускает бота."""
    # Создаем приложение с токеном из config.py
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("bonus", bonus))
    application.add_handler(CommandHandler("game", game))
    application.add_handler(CommandHandler("buy", buy))
    
    # Регистрируем обработчики кнопок и сообщений
    application.add_handler(CallbackQueryHandler(handle_bet_selection, pattern="^bet_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_bet))
    
    # Регистрируем обработчики платежей
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # Запускаем бота
    print("Бот запускается...")
    application.run_polling()
    print("Бот остановлен")

if __name__ == '__main__':
    main()