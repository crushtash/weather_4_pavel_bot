import os
import logging
import requests
import schedule
import time
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from telegram.utils.request import Request

# 🔐 ТВОИ КЛЮЧИ
BOT_TOKEN = os.getenv('BOT_TOKEN')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
LATITUDE = 55.7734
LONGITUDE = 37.6218

# chat_id — ВСТАВЬ СВОИ
PASHAS_CHAT_ID = int(os.getenv('PASHAS_CHAT_ID'))
YOUR_CHAT_ID = int(os.getenv(''YOUR_CHAT_ID''))
# 📡 Telegram бот с таймаутом
request = Request(connect_timeout=5, read_timeout=10)
bot = Bot(token=BOT_TOKEN, request=request)

# 💌 Приветственное сообщение
WELCOME_TEXT = (
"Здравствуй дорогой, любимый + ненаглядный Павел. Я - маленькая частичка личности Наташи Соколовой, обладающая навыками синоптика, я буду присылать тебе информацию о погоде 4 раза в день (11:00, 14:00, 18:00, 23:00), тебе самому ничего делать не нужно. Не знаю, насколько полезным для тебя окажется этот процесс... по крайней мере, пусть это служит маленьким напоминанием о существовании моей хозяйки и о том, что она думает о тебе каждую свободную минуту (то есть все минуты всех дней). Пожалуйста отправь сюда любое сообщение, чтобы другая частичка Наташи, отвечающая за програмирование, могла внести твой id в код для моей корректной работы. Прогнозы ожидайте по расписанию."
)

# 🧠 Комментарии
def get_comment(temp_c, condition, feels_like):
    if "дожд" in condition.lower():
        return "дорогой Паша, не забудь дождевичок (положи в сумочку), ожидается дождь!!! целую"
    elif temp_c <= 10:
        return "дорогой Паша, на улице прохладней обычного, хоть ты и любишь мерзнуть, не забудь утеплиться!! целую"
    elif temp_c >= 25:
        return "ДОРОГОЙ ПАША! ТРЕВОГА, ПОТЕНИЕ!!!!! надень футболку и пей больше воды!! целую"
    else:
        return "дорогой Паша, погода комфортная!!! (вроде), одевайся, как обычно. целую!!"

# ☁ Получаем текущую погоду
def get_weather_data(forecast_tomorrow=False):
    url = f'https://api.weather.yandex.ru/v2/forecast?lat={LATITUDE}&lon={LONGITUDE}&lang=ru_RU&hours=true&limit=2'
    headers = {"X-Yandex-API-Key": YANDEX_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if forecast_tomorrow:
            day = data['forecasts'][1]['parts']['day']
        else:
            day = data['fact']
        temp = day['temp']
        feels_like = day['feels_like']
        condition = day['condition']
        wind_speed = day.get('wind_speed', '—')
        humidity = day.get('humidity', '—')
        precip = day.get('prec_mm', 0)
        precip_prob = day.get('prec_prob', '—') if forecast_tomorrow else '—'
        return temp, feels_like, condition, wind_speed, humidity, precip, precip_prob, data
    except Exception as e:
        print("Ошибка при получении погоды:", e)
        return None

# 🕒 Прогноз на ближайшие часы
def get_hourly_forecast(forecast_data, hours_ahead):
    now = datetime.now()
    current_hour = now.hour
    hourly_list = forecast_data['forecasts'][0]['hours']
    upcoming = [h for h in hourly_list if current_hour < int(h['hour']) <= current_hour + hours_ahead]

    if not upcoming:
        return "📅 Нет данных о ближайших часах."

    result = "📅 Прогноз на ближайшие часы:\n"
    for h in upcoming:
        hour = h['hour']
        temp = h['temp']
        feels = h['feels_like']
        wind = h['wind_speed']
        condition = h['condition']
        prec = h.get('prec_mm', 0)
        cond_text = "сухо" if prec == 0 else f"дождь ({prec} мм)"
        result += f"• {hour}:00 — {temp}°C, ощущается как {feels}°C, {cond_text}, ветер {wind} м/с\n"

    return result

# 💌 Прогноз + комментарий + почасовой
def send_weather_message(time_label):
    hours_ahead_map = {"11:00": 3, "14:00": 4, "18:00": 5}
    hours_ahead = hours_ahead_map.get(time_label, 0)

    weather = get_weather_data()
    if not weather:
        print("Ошибка получения погоды")
        return

    temp, feels_like, condition, wind_speed, humidity, precip, precip_prob, data = weather
    comment = get_comment(temp, condition, feels_like)

    intro = {
        "11:00": "Доброе утро, услада моих глаз!",
        "14:00": "Доброго дня, мое сокровище! Не забудь пообедать!",
        "18:00": "Добрый вечер, жопка!"
    }.get(time_label, "")

    message = f"""{intro}

{comment}

Температура: {temp}°C, ощущается как {feels_like}°C
Осадки: {precip_prob}% вероятность, {precip} мм
Ветер: {wind_speed} м/с
Влажность: {humidity}%
"""

    if hours_ahead:
        message += "\n" + get_hourly_forecast(data, hours_ahead)

    for user_id in [PASHAS_CHAT_ID, YOUR_CHAT_ID]:
        if user_id:
            bot.send_message(chat_id=user_id, text=message)

# 🌙 Ночной прогноз (не меняется)
def send_night_forecast():
    weather = get_weather_data(forecast_tomorrow=True)
    if not weather:
        print("Ошибка получения прогноза на завтра")
        return

    temp, feels_like, condition, wind_speed, humidity, precip, precip_prob, _ = weather

    message = f"""🌙 Завтрашняя погода в Москве:

Температура: {temp}°C, ощущается как {feels_like}°C
Осадки: вероятность {precip_prob}%, {precip} мм
Ветер: {wind_speed} м/с
Влажность: {humidity}%

Приятных сновидений, Паша. Целую в правый и левый глазик."""

    for user_id in [PASHAS_CHAT_ID, YOUR_CHAT_ID]:
        if user_id:
            bot.send_message(chat_id=user_id, text=message)

# ✅ Команды
def test_command(update: Update, context: CallbackContext):
    if update.effective_chat.id in [PASHAS_CHAT_ID, YOUR_CHAT_ID]:
        send_weather_message("14:00") # для теста

def start_command(update: Update, context: CallbackContext):
    if update.effective_chat.id == PASHAS_CHAT_ID:
        bot.send_message(chat_id=PASHAS_CHAT_ID, text=WELCOME_TEXT)

# 🔎 Показывать chat_id при любом сообщении
def echo_id(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    print(f"➤ Сообщение от {user_name} — chat_id: {user_id}")

# 🕓 Планируем задачи
def setup_schedules():
    schedule.every().day.at("11:00").do(send_weather_message, "11:00")
    schedule.every().day.at("14:00").do(send_weather_message, "14:00")
    schedule.every().day.at("18:00").do(send_weather_message, "18:00")
    schedule.every().day.at("23:00").do(send_night_forecast)

# 🚀 Запуск
def main():
    global PASHAS_CHAT_ID, YOUR_CHAT_ID

    print("⚡ Бот запущен. Напишите ему в Telegram, чтобы увидеть chat_id.")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("test", test_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_id))
    updater.start_polling()

    setup_schedules()
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()
