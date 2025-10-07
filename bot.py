import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from eth_account import Account

# Получаем токен из переменной окружения (Railway)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ Переменная окружения TELEGRAM_BOT_TOKEN не задана!")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

user_state = {}

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔍 Проверить баланс")],
            [KeyboardButton("📜 Проверить транзакции")],
            [KeyboardButton("🔄 Конвертировать seed в адрес")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = "main"
    await update.message.reply_text(
        "👋 Привет! Выберите действие:",
        reply_markup=get_main_keyboard(),
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_state.get(user_id, "main")

    if text == "🔍 Проверить баланс":
        user_state[user_id] = "awaiting_address_balance"
        await update.message.reply_text("Введите Ethereum-адрес (начинается с 0x):")
    elif text == "📜 Проверить транзакции":
        user_state[user_id] = "awaiting_address_tx"
        await update.message.reply_text("Введите Ethereum-адрес (начинается с 0x):")
    elif text == "🔄 Конвертировать seed в адрес":
        user_state[user_id] = "awaiting_seed"
        await update.message.reply_text("Введите seed-фразу (12 или 24 слова через пробел):")
    else:
        if state == "awaiting_address_balance":
            if text.startswith("0x") and len(text) == 42:
                balance = get_eth_balance(text)
                await update.message.reply_text(f"💰 Баланс: {balance} ETH")
            else:
                await update.message.reply_text("❌ Неверный адрес. Должен быть 42 символа, начинаться с 0x.")
            user_state[user_id] = "main"

        elif state == "awaiting_address_tx":
            if text.startswith("0x") and len(text) == 42:
                txs = get_eth_transactions(text)
                if txs:
                    msg = "📨 Последние транзакции:\n\n" + "\n\n".join(txs[:3])
                else:
                    msg = "📭 Транзакций не найдено или ошибка запроса."
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text("❌ Неверный адрес. Должен быть 42 символа, начинаться с 0x.")
            user_state[user_id] = "main"

        elif state == "awaiting_seed":
            try:
                account = Account.from_mnemonic(text)
                address = account.address
                private_key = account.key.hex()
                await update.message.reply_text(
                    f"✅ Адрес: `{address}`\n"
                    f"🔑 Приватный ключ: `{private_key}`\n\n"
                    f"⚠️ НИКОМУ НЕ ОТПРАВЛЯЙТЕ ПРИВАТНЫЙ КЛЮЧ!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {str(e)}\nПроверьте правильность seed-фразы.")
            user_state[user_id] = "main"
        else:
            await update.message.reply_text("Пожалуйста, используйте кнопки.", reply_markup=get_main_keyboard())

def get_eth_balance(address: str) -> str:
    url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("status") == "1":
            return f"{int(data['result']) / 1e18:.6f}"
        else:
            return "0.0"
    except Exception as e:
        return f"ошибка: {str(e)[:50]}"

def get_eth_transactions(address: str) -> list:
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=5&sort=desc"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("status") == "1" and data.get("result"):
            txs = []
            for tx in data["result"][:3]:
                value_eth = int(tx['value']) / 1e18
                txs.append(
                    f"Hash: `{tx['hash'][:12]}...`\n"
                    f"From: `{tx['from'][:10]}...`\n"
                    f"To: `{tx['to'][:10]}...`\n"
                    f"Value: {value_eth:.6f} ETH"
                )
            return txs
        else:
            return []
    except:
        return []

if __name__ == "__main__":
    print("🚀 Запуск бота на Railway...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен!")
    app.run_polling()
