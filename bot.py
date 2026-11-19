import logging
import os
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from parser import parse, ParseError

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
USER_ID = os.getenv('TELEGRAM_USER_ID', '').strip()
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary').strip()
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Moscow').strip()
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
# Telegram URLs contain the bot token; never log request URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)
log = logging.getLogger(__name__)

def allowed(update):
    return bool(update.effective_user and update.effective_chat and update.effective_chat.type == 'private' and str(update.effective_user.id) == USER_ID)

def calendar_insert(event):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open('token.json', 'w', encoding='utf-8') as f: f.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    body = {'summary': event.title, 'start': {'dateTime': event.start.isoformat(), 'timeZone': TIMEZONE}, 'end': {'dateTime': event.end.isoformat(), 'timeZone': TIMEZONE}}
    return service.events().insert(calendarId=CALENDAR_ID, body=body).execute()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    await update.message.reply_text('Привет! Напиши, например:\n«вторник 17:00 встреча с Максимом два часа»\n«завтра 17 тренировка»\n«25.11 15:30 врач на 30 минут»\n\nБез даты выберу ближайшее такое время. Без длительности — 1 час. Перед добавлением попрошу подтверждение. Часовой пояс: ' + TIMEZONE)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    try:
        event = parse(update.message.text, datetime.now(ZoneInfo(TIMEZONE)))
    except ParseError as e:
        await update.message.reply_text(str(e))
        return
    nonce = secrets.token_hex(8)
    context.user_data['pending'] = (nonce, event)
    text = f'Добавить в календарь?\n\n{event.title}\n{event.start:%d.%m.%Y, %H:%M} — {event.end:%d.%m.%Y, %H:%M}\nЧасовой пояс: {TIMEZONE}'
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('✅ Добавить', callback_data='confirm:' + nonce), InlineKeyboardButton('❌ Отмена', callback_data='cancel:' + nonce)]]))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not allowed(update):
        await q.answer(); return
    await q.answer()
    pending = context.user_data.get('pending')
    action, _, nonce = q.data.partition(':')
    if not pending or pending[0] != nonce:
        await q.edit_message_text('Запрос устарел. Отправьте событие ещё раз.'); return
    context.user_data.pop('pending', None)
    event = pending[1]
    if action == 'cancel':
        await q.edit_message_text('Отменено.'); return
    try:
        import asyncio
        result = await asyncio.to_thread(calendar_insert, event)
    except Exception:
        log.exception('Calendar request failed')
        await q.edit_message_text('Не удалось добавить событие. Проверьте авторизацию Google, доступ к календарю и журнал бота. Отправьте событие ещё раз.')
        return
    await q.edit_message_text('✅ Добавлено: ' + event.title + '\n' + event.start.strftime('%d.%m.%Y %H:%M') + '\n' + result.get('htmlLink', ''))

def main():
    if not TOKEN or not USER_ID.isdecimal():
        raise SystemExit('Заполните TELEGRAM_BOT_TOKEN и числовой TELEGRAM_USER_ID в .env')
    try: ZoneInfo(TIMEZONE)
    except ZoneInfoNotFoundError: raise SystemExit('Неизвестный TIMEZONE в .env')
    if not os.path.isfile('token.json'):
        raise SystemExit('Нет token.json: сначала выполните python authorize.py')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.add_handler(CallbackQueryHandler(callback, pattern=r'^(confirm|cancel):[0-9a-f]{16}$'))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__': main()
