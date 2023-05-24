import logging
import os
import psycopg2 as pg
import re
import requests
import json
import threading, time
import numpy as np
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# Create a new bot by instantiating the Bot class.
bot_token = ('6121301545:AAEFl8I_lmMPldudcCuhGtJk9vT_F90sIm4')
bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

def get_currency_rates():
    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT currency_name,  rate FROM currencies")
    rows = cursor.fetchall()
    conn.close()
    logging.info(rows)
    return rows

api_key = "98X0NBIA93MCV2KS"
url = f"https://alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey={api_key}"
response = requests.get(url)
data = json.loads(response.text)
print(data)

def get_daily_closing_prices(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={'OVNNX0FLXSSXLEWB'}"
        response = requests.get(url)
        data = response.json()
        time_series = data["Time Series (Daily)"]
        closing_prices = [float(entry["4. close"]) for entry in time_series.values()]  #
        median_price = np.median(closing_prices)
        print(median_price)
        return median_price
    except KeyError:
        return None

get_daily_closing_prices('aapl')

start = KeyboardButton(text='старт')
Add = KeyboardButton(text='Добавить')
save = KeyboardButton(text='посмотреть')

user_commands = [
    BotCommand(command="/start", description="START"),
    BotCommand(command="/Add", description="add"),
    BotCommand(command="/save", description="save")
]
admin_commands = [
    BotCommand(command="/start", description="START"),
    BotCommand(command="/Add", description="add"),
    BotCommand(command="/save", description="save")

]

async def setup_bot_commands(dispatcher: Dispatcher):
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    for admin in ADMIN_ID:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin))


class ManageStateGroup(StatesGroup):
    Add_currency_name_state = State()
    Add_currency_rate_state = State()
    Edit_currency_name_state = State()
    Edit_currency_rate_state = State()
    Delete_currency_state = State()


class Step2(StatesGroup):
    currency_name2 = State()
    amount = State()

saved_state_global = {}

@dp.message_handler(commands=['start'])
async def add_chat_id(message: types.Message):
    await message.reply("Добро пожаловать в бота")

@dp.message_handler(commands=['Add'])
async def add_currency_command(message: types.Message):
    await ManageStateGroup.Add_currency_name_state.set()
    await message.reply("Введите имя ценной бумаги")

@dp.message_handler(state=ManageStateGroup.Add_currency_name_state)
async def process_currency(message: types.Message, state: FSMContext):
    await state.update_data(currency_name=message.text)
    user_data = await state.get_data()
    print(user_data)
    rate_shadow = get_daily_closing_prices(user_data['currency_name'])
    print(rate_shadow)
    await ManageStateGroup.Add_currency_rate_state.set()
    await message.reply(rate_shadow)
    try:
        add_currency_in_database(currency_name=user_data['currency_name'], rate=int(rate_shadow))
        await message.reply("Ценная бумага сохранена ")
    except Exception as e:
        logging.error("Ошибка записи в БД", e)
        error_message = e.args[0] if len(e.args) > 0 else "Причина неизвестна"
        await message.reply(f"ценную бумагу не удалось мохранить не удалось сохранить: {error_message}")
    finally:
        await state.finish()


def add_currency_in_database(currency_name: str, rate: int):
    conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="postgres"
        )
    cursor = conn.cursor()
    # Запрашиваем все имеющиеся валюты, по параметру currency_name
    cursor.execute("SELECT 1 FROM currencies WHERE currency_name = %(currency_name)s", {"currency_name": currency_name})
    found_currencies = cursor.fetchall()

    # Если найдена хотя бы одна валюта, currency_name которой совпадает с тем, что мы пытаемся сохранить, тогда
    # кидаем исключение с текстом "Валюта уже существует"
    if len(found_currencies) > 0:
        raise Exception("Валюта уже существует")

    cursor.execute(
        "INSERT INTO currencies(currency_name, rate) VALUES (%(currency_name)s, %(rate)s)",
        {
            "currency_name": currency_name,
            "rate": rate
        }
    )
    conn.commit()
    conn.close()
@dp.message_handler(commands=['save'])
async def add_currency_command(message: types.Message):
    currencies = get_currency_rates()
    response = ""
    if currencies:
        response = "Курсы ценной бумаги:\n"
        for rate in currencies:
            response += f"{rate[0]}: {rate[1]} руб.\n"
    else:
        response = "Курсы валют не найдены"
    await bot.send_message(message.chat.id, response)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
