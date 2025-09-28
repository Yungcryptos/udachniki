# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Файл конфигурации бота
# Токен теперь берется из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройки валюты и платежей
STARS_TO_COINS_RATE = 1

# Настройки бонусов
REGISTRATION_BONUS = 15
DAILY_BONUS = 0

# Настройки игры "Кубик"
WIN_MULTIPLIER = 2
WINNING_DICE_VALUES = [6]

# Настройки минимальной и максимальной ставки
MIN_BET = 5
MAX_BET = 1000

# Файл для хранения данных пользователей
USER_DATA_FILE = "users.json"