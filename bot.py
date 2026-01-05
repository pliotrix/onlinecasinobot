import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Dice, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ChatMemberStatus, DiceEmoji
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
from datetime import datetime

# Konfiguratsiya
BOT_TOKEN = "8245165101:AAFwKriOLyPNexD0yljM6brh3yeF8nrD2TQ"
ADMIN_USERNAME = "jlekavicius"
CHANNEL_USERNAME = "@pliotrix"
CHANNEL_ID = "@pliotrix"

# Logging
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# IMPORTANT: FSM ga user_id qo'shish
from aiogram.fsm.storage.base import StorageKey

# FSM States
class BroadcastState(StatesGroup):
    waiting_message = State()

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_balance = State()

class GameState(StatesGroup):
    waiting_bet = State()
    game_type = State()

class SaperState(StatesGroup):
    waiting_bet = State()
    playing = State()

class AviatorState(StatesGroup):
    waiting_bet = State()
    flying = State()

class AviatorState(StatesGroup):
    waiting_bet = State()
    flying = State()

# Database
def init_db():
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  balance INTEGER DEFAULT 1000,
                  referrals INTEGER DEFAULT 0,
                  blocked INTEGER DEFAULT 0,
                  joined_date TEXT,
                  last_bonus TEXT,
                  total_games INTEGER DEFAULT 0,
                  total_wins INTEGER DEFAULT 0,
                  total_lost INTEGER DEFAULT 0,
                  vip_status INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (referrer_id INTEGER, referred_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  game_type TEXT,
                  bet INTEGER,
                  win INTEGER,
                  result INTEGER,
                  date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tournaments
                 (user_id INTEGER PRIMARY KEY,
                  weekly_wins INTEGER DEFAULT 0,
                  week_number INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                  (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except:
        pass
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    user = get_user(user_id)
    return user[2] if user else 0

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT * FROM referrals WHERE referred_id=?", (referred_id,))
    if not c.fetchone():
        c.execute("INSERT INTO referrals VALUES (?, ?)", (referrer_id, referred_id))
        c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
        update_balance(referrer_id, 500)
        conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, balance FROM users WHERE blocked=0 ORDER BY balance DESC LIMIT ?", (limit,))
    users = c.fetchall()
    conn.close()
    return users

def get_all_users():
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE blocked=0")
    users = c.fetchall()
    conn.close()
    return [u[0] for u in users]

def block_user(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET blocked=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET blocked=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_blocked(user_id):
    user = get_user(user_id)
    return user[4] == 1 if user else False

def add_game_history(user_id, game_type, bet, win, result):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("INSERT INTO game_history (user_id, game_type, bet, win, result, date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, game_type, bet, win, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE users SET total_games = total_games + 1 WHERE user_id = ?", (user_id,))
    if win > bet:
        c.execute("UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?", (user_id,))
    else:
        c.execute("UPDATE users SET total_lost = total_lost + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_game_history(user_id, limit=10):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT game_type, bet, win, result, date FROM game_history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    history = c.fetchall()
    conn.close()
    return history

def get_user_stats(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT total_games, total_wins, total_lost FROM users WHERE user_id = ?", (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats if stats else (0, 0, 0)

def check_daily_bonus(user_id):
    user = get_user(user_id)
    if not user or not user[6]:
        return True
    last_bonus = user[6]
    if not last_bonus:
        return True
    try:
        last_date = datetime.strptime(last_bonus, "%Y-%m-%d %H:%M:%S").date()
        today = datetime.now().date()
        return today > last_date
    except:
        return True

def claim_daily_bonus(user_id):
    bonus = 1000
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ?, balance = balance + ? WHERE user_id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bonus, user_id))
    conn.commit()
    conn.close()
    return bonus

def add_game_history(user_id, game_type, bet, win, result):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("INSERT INTO game_history (user_id, game_type, bet, win, result, date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, game_type, bet, win, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE users SET total_games = total_games + 1 WHERE user_id = ?", (user_id,))
    if win > bet:
        c.execute("UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?", (user_id,))
    else:
        c.execute("UPDATE users SET total_lost = total_lost + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_game_history(user_id, limit=10):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT game_type, bet, win, result, date FROM game_history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    history = c.fetchall()
    conn.close()
    return history

def get_user_stats(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT total_games, total_wins, total_lost, vip_status FROM users WHERE user_id = ?", (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats if stats else (0, 0, 0, 0)

def check_daily_bonus(user_id):
    user = get_user(user_id)
    if not user:
        return False
    last_bonus = user[6]
    if not last_bonus:
        return True
    last_date = datetime.strptime(last_bonus, "%Y-%m-%d %H:%M:%S").date()
    today = datetime.now().date()
    return today > last_date

def claim_daily_bonus(user_id):
    bonus = 1000
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ?, balance = balance + ? WHERE user_id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bonus, user_id))
    conn.commit()
    conn.close()
    return bonus

def update_vip_status(user_id):
    stats = get_user_stats(user_id)
    total_games = stats[0]
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    if total_games >= 100:
        c.execute("UPDATE users SET vip_status = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_weekly_tournament():
    import calendar
    today = datetime.now()
    week_num = today.isocalendar()[1]
    
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, weekly_wins FROM users JOIN tournaments ON users.user_id = tournaments.user_id WHERE week_number = ? ORDER BY weekly_wins DESC LIMIT 10", (week_num,))
    leaders = c.fetchall()
    conn.close()
    return leaders, week_num

def update_tournament(user_id):
    import calendar
    today = datetime.now()
    week_num = today.isocalendar()[1]
    
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT week_number FROM tournaments WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result and result[0] == week_num:
        c.execute("UPDATE tournaments SET weekly_wins = weekly_wins + 1 WHERE user_id = ?", (user_id,))
    else:
        c.execute("INSERT OR REPLACE INTO tournaments (user_id, weekly_wins, week_number) VALUES (?, 1, ?)", (user_id, week_num))
    
    conn.commit()
    conn.close()

# Obuna tekshirish
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except:
        return False

# Keyboards
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Slot"), KeyboardButton(text="🎲 Kub")],
            [KeyboardButton(text="🎯 Dart"), KeyboardButton(text="🏀 Basketbol")],
            [KeyboardButton(text="⚽️ Futbol"), KeyboardButton(text="🎳 Bouling")],
            [KeyboardButton(text="✈️ Aviator"), KeyboardButton(text="🎁 Bonus")],
            [KeyboardButton(text="💰 Balans"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🏆 Turnir"), KeyboardButton(text="📜 Tarix")],
            [KeyboardButton(text="👥 Referal"), KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )

def bet_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="50 jL"), KeyboardButton(text="100 jL"), KeyboardButton(text="500 jL")],
            [KeyboardButton(text="1000 jL"), KeyboardButton(text="5000 jL"), KeyboardButton(text="10000 jL")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

def aviator_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 To'xtatish")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

def aviator_control_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 To'xtatish")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Balans qo'shish", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="🚫 Bloklash", callback_data="admin_block"),
         InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data="admin_unblock")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📣 Hammaga xabar", callback_data="admin_broadcast")]
    ])

# Yutuq hisoblash funksiyalari
def calculate_slot_win(value, bet):
    """🎰 Slot machine"""
    if value == 64:  # 777 (Bar Bar Bar)
        return bet * 50
    elif value in [43, 64]:
        return bet * 30
    elif value in [22, 43]:
        return bet * 20
    elif value in [1, 22]:
        return bet * 15
    elif value % 7 == 0:
        return bet * 10
    elif value % 3 == 0:
        return bet * 2
    else:
        return 0

def calculate_dice_win(value, bet):
    """🎲 Kub (1-6)"""
    if value == 6:
        return bet * 5
    elif value == 5:
        return bet * 3
    elif value == 4:
        return bet * 2
    else:
        return 0

def calculate_dart_win(value, bet):
    """🎯 Dart (1-6)"""
    if value == 6:  # Markazga
        return bet * 10
    elif value == 5:
        return bet * 5
    elif value == 4:
        return bet * 3
    else:
        return 0

def calculate_basketball_win(value, bet):
    """🏀 Basketbol (1-5)"""
    if value in [4, 5]:  # Gol
        return bet * 4
    else:
        return 0

def calculate_football_win(value, bet):
    """⚽️ Futbol (1-5)"""
    if value in [3, 4, 5]:  # Gol
        return bet * 3
    else:
        return 0

def calculate_bowling_win(value, bet):
    """🎳 Bouling (1-6)"""
    if value == 6:  # Strike
        return bet * 8
    elif value == 5:
        return bet * 4
    elif value == 4:
        return bet * 2
    else:
        return 0

# Handlers
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    if is_blocked(user_id):
        await message.answer("❌ Siz bloklangansiz!")
        return
    
    # Referal
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referrer_id = int(args[1].replace("ref", ""))
            if referrer_id != user_id and not get_user(user_id):
                add_user(user_id, username)
                add_referral(referrer_id, user_id)
                await bot.send_message(referrer_id, f"🎉 Yangi referal! +500 jL coin\n👤 @{username}")
        except:
            pass
    
    if not get_user(user_id):
        add_user(user_id, username)
    
    if not await check_subscription(user_id):
        await message.answer(
            "🎰 <b>Casino Bot</b>ga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun kanalimizga obuna bo'ling:",
            reply_markup=subscribe_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        f"🎰 <b>Xush kelibsiz, {username}!</b>\n\n"
        f"💰 Balans: {get_balance(user_id)} jL coin\n\n"
        "O'ynash uchun o'yinni tanlang!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if await check_subscription(user_id):
        await callback.message.answer(
            f"✅ <b>Obuna tasdiqlandi!</b>\n\n"
            f"💰 Balans: {get_balance(user_id)} jL coin\n\n"
            "O'ynash uchun o'yinni tanlang!",
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Siz hali obuna bo'lmadingiz!", show_alert=True)

# O'yin turini tanlash
@dp.message(F.text.in_(["🎰 Slot", "🎲 Kub", "🎯 Dart", "🏀 Basketbol", "⚽️ Futbol", "🎳 Bouling"]))
async def select_game(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_blocked(user_id):
        await bot.send_message(user_id, "❌ Siz bloklangansiz!")
        return
    
    if not await check_subscription(user_id):
        await bot.send_message(
            user_id,
            "❌ Kanalga obuna bo'lishingiz kerak!",
            reply_markup=subscribe_keyboard()
        )
        return
    
    # O'yin turini saqlash
    game_map = {
        "🎰 Slot": "slot",
        "🎲 Kub": "dice",
        "🎯 Dart": "dart",
        "🏀 Basketbol": "basketball",
        "⚽️ Futbol": "football",
        "🎳 Bouling": "bowling"
    }
    
    game_type = game_map[message.text]
    await state.update_data(game_type=game_type)
    await state.set_state(GameState.waiting_bet)
    
    balance = get_balance(user_id)
    await bot.send_message(
        user_id,
        f"<b>{message.text}</b> tanlandi!\n\n"
        f"💰 Balansingiz: {balance} jL coin\n\n"
        "Qancha tikmoqchisiz? (minimum 50 jL coin)\n"
        "Yoki pastdagi tugmalardan tanlang:",
        reply_markup=bet_keyboard(),
        parse_mode="HTML"
    )

# ✈️ AVIATOR O'YINI
@dp.message(F.text == "✈️ Aviator")
async def aviator_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_blocked(user_id):
        await bot.send_message(user_id, "❌ Siz bloklangansiz!")
        return
    
    if not await check_subscription(user_id):
        await bot.send_message(
            user_id,
            "❌ Kanalga obuna bo'lishingiz kerak!",
            reply_markup=subscribe_keyboard()
        )
        return
    
    balance = get_balance(user_id)
    await bot.send_message(
        user_id,
        "✈️ <b>AVIATOR</b>\n\n"
        "Samolyot ko'tariladi, koeffitsiyent oshib boradi!\n"
        "Vaqtida to'xtating va yutib oling! 🚀\n\n"
        f"💰 Balansingiz: {balance} jL coin\n\n"
        "Qancha tikmoqchisiz? (minimum 50 jL coin)",
        reply_markup=bet_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AviatorState.waiting_bet)

@dp.message(AviatorState.waiting_bet)
async def aviator_process_bet(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "🔙 Orqaga":
        await state.clear()
        await bot.send_message(user_id, "Bosh menyu:", reply_markup=main_keyboard())
        return
    
    bet_text = message.text.replace("jL", "").replace(" ", "").strip()
    
    try:
        bet = int(bet_text)
    except:
        await bot.send_message(user_id, "❌ Noto'g'ri miqdor! Raqam kiriting (masalan: 100)")
        return
    
    if bet < 50:
        await bot.send_message(user_id, "❌ Minimum tikish 50 jL coin!")
        return
    
    balance = get_balance(user_id)
    if balance < bet:
        await bot.send_message(
            user_id,
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizda: {balance} jL coin\n"
            f"📊 Kerak: {bet} jL coin",
            reply_markup=main_keyboard()
        )
        await state.clear()
        return
    
    update_balance(user_id, -bet)
    await state.update_data(bet=bet, crashed=False)
    
    # Aviator animatsiyasi
    crash_point = random.uniform(1.01, 10.0)
    await state.update_data(crash_point=crash_point)
    
    msg = await bot.send_message(
        user_id,
        "✈️ <b>AVIATOR</b>\n\n"
        "🚀 Samolyot uchmoqda...\n"
        "💰 Koeffitsiyent: 1.00x\n\n"
        "📊 To'xtatish tugmasini bosing!",
        reply_markup=aviator_control_keyboard(),
        parse_mode="HTML"
    )
    
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AviatorState.flying)
    
    # Animatsiya loop
    current = 1.0
    await asyncio.sleep(1)
    
    while current < crash_point:
        current += random.uniform(0.1, 0.3)
        if current > crash_point:
            current = crash_point
        
        data = await state.get_data()
        if data.get("crashed", False):
            break
        
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=msg.message_id,
                text=f"✈️ <b>AVIATOR</b>\n\n"
                     f"🚀 Samolyot uchmoqda...\n"
                     f"💰 Koeffitsiyent: {current:.2f}x\n\n"
                     f"📊 To'xtatish tugmasini bosing!",
                parse_mode="HTML"
            )
        except:
            pass
        
        await asyncio.sleep(0.5)
    
    # Agar user to'xtatmagan bo'lsa - crash
    data = await state.get_data()
    if not data.get("crashed", False):
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=msg.message_id,
            text=f"💥 <b>CRASH!</b>\n\n"
                 f"Samolyot {crash_point:.2f}x da quladi!\n"
                 f"😔 Yutqazdingiz: -{bet} jL coin\n\n"
                 f"💰 Balans: {get_balance(user_id)} jL coin",
            parse_mode="HTML"
        )
        add_game_history(user_id, "Aviator", bet, 0, int(crash_point * 100))
        await bot.send_message(user_id, "Yana o'ynaysizmi?", reply_markup=main_keyboard())
        await state.clear()

@dp.message(AviatorState.flying, F.text == "💰 To'xtatish")
async def aviator_cashout(message: Message, state: FSMContext):
    data = await state.get_data()
    bet = data.get("bet", 0)
    crash_point = data.get("crash_point", 2.0)
    msg_id = data.get("msg_id")
    user_id = message.from_user.id
    
    # Hozirgi koeffitsiyentni olish (crash pointdan past bo'lishi kerak)
    current_multi = random.uniform(1.1, min(crash_point - 0.1, crash_point * 0.9))
    
    win = int(bet * current_multi)
    profit = win - bet
    
    update_balance(user_id, win)
    await state.update_data(crashed=True)
    
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=msg_id,
                text=f"🎉 <b>YUTUQ!</b>\n\n"
                     f"✈️ To'xtatdingiz: {current_multi:.2f}x\n"
                     f"💰 Yutuq: +{win} jL coin\n"
                     f"📈 Foyda: +{profit} jL coin\n\n"
                     f"💰 Balans: {get_balance(user_id)} jL coin",
                parse_mode="HTML"
            )
        except:
            pass
    
    add_game_history(user_id, "Aviator", bet, win, int(current_multi * 100))
    update_tournament(user_id)
    update_vip_status(user_id)
    
    await bot.send_message(user_id, "Yana o'ynaysizmi?", reply_markup=main_keyboard())
    await state.clear()

# Orqaga tugmasi
@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await bot.send_message(
        user_id,
        "Bosh menyu:",
        reply_markup=main_keyboard()
    )

# Tikish miqdorini olish
@dp.message(GameState.waiting_bet)
async def process_bet(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Miqdorni ajratib olish
    bet_text = message.text.replace("jL", "").replace(" ", "").strip()
    
    try:
        bet = int(bet_text)
    except:
        await bot.send_message(user_id, "❌ Noto'g'ri miqdor! Raqam kiriting (masalan: 100)")
        return
    
    if bet < 50:
        await bot.send_message(user_id, "❌ Minimum tikish 50 jL coin!")
        return
    
    balance = get_balance(user_id)
    if balance < bet:
        await bot.send_message(
            user_id,
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizda: {balance} jL coin\n"
            f"📊 Kerak: {bet} jL coin\n\n"
            "Referal orqali balans to'plang!",
            reply_markup=main_keyboard()
        )
        await state.clear()
        return
    
    # Balansdan ayirish
    update_balance(user_id, -bet)
    
    # O'yin turini olish
    data = await state.get_data()
    game_type = data['game_type']
    
    # O'yinni boshlash
    games = {
        "slot": (DiceEmoji.SLOT_MACHINE, calculate_slot_win, "🎰 Slot Machine"),
        "dice": (DiceEmoji.DICE, calculate_dice_win, "🎲 Kub"),
        "dart": (DiceEmoji.DART, calculate_dart_win, "🎯 Dart"),
        "basketball": (DiceEmoji.BASKETBALL, calculate_basketball_win, "🏀 Basketbol"),
        "football": (DiceEmoji.FOOTBALL, calculate_football_win, "⚽️ Futbol"),
        "bowling": (DiceEmoji.BOWLING, calculate_bowling_win, "🎳 Bouling")
    }
    
    emoji, calc_func, game_name = games[game_type]
    
    # O'yin yuborish - PRIVATE CHATGA
    dice_message = await bot.send_dice(
        chat_id=user_id,
        emoji=emoji
    )
    
    # Animatsiya tugashini kutish
    await asyncio.sleep(3)
    
    # Natijani hisoblash
    dice_value = dice_message.dice.value
    win = calc_func(dice_value, bet)
    
    if win > 0:
        update_balance(user_id, win)
        result_text = f"🎉 <b>YUTUQ!</b>\n\n💰 +{win} jL coin!"
        profit = win - bet
        if profit > 0:
            result_text += f"\n📈 Foyda: +{profit} jL coin"
        update_tournament(user_id)
    else:
        result_text = f"😔 <b>Yutqazdingiz</b>\n\n💸 -{bet} jL coin"
    
    new_balance = get_balance(user_id)
    result_text += f"\n\n🎮 {game_name}"
    result_text += f"\n🎯 Natija: {dice_value}"
    result_text += f"\n💰 Balans: {new_balance} jL coin"
    
    add_game_history(user_id, game_name, bet, win, dice_value)
    update_vip_status(user_id)
    
    await bot.send_message(
        user_id,
        result_text,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    
    await state.clear()

@dp.message(F.text == "💰 Balans")
async def show_balance(message: Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    user = get_user(user_id)
    stats = get_user_stats(user_id)
    
    vip_emoji = "💎" if stats[3] == 1 else ""
    
    await bot.send_message(
        user_id,
        f"💰 <b>Balans</b>\n\n"
        f"jL coin: {balance} {vip_emoji}\n"
        f"👥 Referallar: {user[3]}\n"
        f"🎮 Jami o'yinlar: {stats[0]}\n"
        f"✅ Yutganlar: {stats[1]}\n"
        f"❌ Yutqazganlar: {stats[2]}\n\n"
        f"💡 Do'stlaringizni taklif qilib balans to'plang!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# 🎁 KUNLIK BONUS
@dp.message(F.text == "🎁 Bonus")
async def daily_bonus(message: Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await bot.send_message(
            user_id,
            "❌ Kanalga obuna bo'lishingiz kerak!",
            reply_markup=subscribe_keyboard()
        )
        return
    
    if check_daily_bonus(user_id):
        bonus = claim_daily_bonus(user_id)
        await bot.send_message(
            user_id,
            f"🎁 <b>Kunlik bonus!</b>\n\n"
            f"💰 +{bonus} jL coin\n"
            f"Ertaga yana keling!\n\n"
            f"💰 Yangi balans: {get_balance(user_id)} jL coin",
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            user_id,
            "⏰ <b>Bonus olindi!</b>\n\n"
            "Ertaga qayta keling!",
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )

# 📊 STATISTIKA
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    balance = get_balance(user_id)
    
    win_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
    vip_status = "💎 VIP" if stats[3] == 1 else "👤 Oddiy"
    
    await bot.send_message(
        user_id,
        f"📊 <b>Statistika</b>\n\n"
        f"Status: {vip_status}\n"
        f"💰 Balans: {balance} jL coin\n\n"
        f"🎮 Jami o'yinlar: {stats[0]}\n"
        f"✅ Yutganlar: {stats[1]}\n"
        f"❌ Yutqazganlar: {stats[2]}\n"
        f"📈 Yutuq foizi: {win_rate:.1f}%\n\n"
        f"💡 100+ o'yin o'ynab VIP bo'ling!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# 🏆 TURNIR
@dp.message(F.text == "🏆 Turnir")
async def show_tournament(message: Message):
    user_id = message.from_user.id
    leaders, week_num = get_weekly_tournament()
    
    text = f"🏆 <b>Haftalik Turnir</b>\n"
    text += f"📅 {week_num}-hafta\n\n"
    
    if leaders:
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, username, wins) in enumerate(leaders[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} @{username or 'User'}: {wins} yutuq\n"
    else:
        text += "Hali hech kim yo'q! Birinchi bo'ling! 🚀"
    
    text += "\n💡 Har bir yutuq turnirga qo'shiladi!"
    
    await bot.send_message(user_id, text, reply_markup=main_keyboard(), parse_mode="HTML")

# 📜 TARIX
@dp.message(F.text == "📜 Tarix")
async def show_history(message: Message):
    user_id = message.from_user.id
    history = get_game_history(user_id, 10)
    
    if not history:
        await bot.send_message(
            user_id,
            "📜 <b>O'yinlar tarixi</b>\n\n"
            "Hali o'yin o'ynamagansiz!",
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "📜 <b>Oxirgi 10 o'yin</b>\n\n"
    
    for game_type, bet, win, result, date in history:
        if win > bet:
            emoji = "✅"
            outcome = f"+{win - bet}"
        else:
            emoji = "❌"
            outcome = f"-{bet}"
        
        text += f"{emoji} {game_type}: {outcome} jL\n"
    
    await bot.send_message(user_id, text, reply_markup=main_keyboard(), parse_mode="HTML")

@dp.message(F.text == "📊 Top")
async def show_top(message: Message):
    user_id = message.from_user.id
    top = get_top_users(10)
    text = "🏆 <b>Top 10 o'yinchilar</b>\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, username, balance) in enumerate(top):
        stats = get_user_stats(uid)
        vip = "💎" if stats[3] == 1 else ""
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} @{username or 'User'}: {balance} jL {vip}\n"
    
    await bot.send_message(user_id, text, reply_markup=main_keyboard(), parse_mode="HTML")

@dp.message(F.text == "👥 Referal")
async def show_referral(message: Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    user = get_user(user_id)
    
    await bot.send_message(
        user_id,
        f"👥 <b>Referal tizimi</b>\n\n"
        f"Har bir referal uchun: +500 jL coin\n"
        f"Sizning referallaringiz: {user[3]}\n\n"
        f"🔗 Sizning linkingiz:\n<code>{ref_link}</code>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: Message):
    user_id = message.from_user.id
    await bot.send_message(
        user_id,
        "ℹ️ <b>Yordam</b>\n\n"
        "<b>O'yinlar:</b>\n"
        "🎰 Slot - x50 gacha\n"
        "🎲 Kub - x5 gacha\n"
        "🎯 Dart - x10 gacha\n"
        "🏀 Basketbol - x4 gacha\n"
        "⚽️ Futbol - x3 gacha\n"
        "🎳 Bouling - x8 gacha\n"
        "✈️ Aviator - x10 gacha\n\n"
        "<b>Funksiyalar:</b>\n"
        "🎁 Bonus - Kunlik 1000 jL coin\n"
        "📊 Statistika - Sizning statistikangiz\n"
        "🏆 Turnir - Haftalik musobaqa\n"
        "📜 Tarix - Oxirgi o'yinlar\n"
        "👥 Referal - Har biri 500 jL coin\n"
        "💎 VIP - 100+ o'yin o'ynang",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# Admin commands
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    # Faqat private chatda
    if message.chat.type != "private":
        await message.answer("⚠️ Admin panel faqat private chatda ishlaydi!")
        return
    
    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return
    
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE blocked=1")
    blocked = c.fetchone()[0]
    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0] or 0
    conn.close()
    
    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"🚫 Bloklangan: {blocked}\n"
        f"💰 Umumiy balans: {total_balance} jL coin",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text("Foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminState.waiting_user_id)

@dp.message(AdminState.waiting_user_id)
async def admin_add_balance_amount(message: Message, state: FSMContext):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.answer("Balans miqdorini kiriting:")
        await state.set_state(AdminState.waiting_balance)
    except:
        await message.answer("❌ Noto'g'ri ID!")
        await state.clear()

@dp.message(AdminState.waiting_balance)
async def admin_add_balance_finish(message: Message, state: FSMContext):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data['user_id']
        
        update_balance(user_id, amount)
        await message.answer(f"✅ {user_id} ga {amount} jL coin qo'shildi!", reply_markup=admin_keyboard())
        await bot.send_message(user_id, f"🎁 Admin sizga {amount} jL coin qo'shdi!")
    except:
        await message.answer("❌ Xatolik!")
    
    await state.clear()

@dp.callback_query(F.data == "admin_block")
async def admin_block_user(callback: CallbackQuery):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text("Bloklash uchun ID yuboring:\n/block [user_id]")

@dp.message(Command("block"))
async def block_user_cmd(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    try:
        user_id = int(message.text.split()[1])
        block_user(user_id)
        await message.answer(f"✅ {user_id} bloklandi!", reply_markup=admin_keyboard())
    except:
        await message.answer("❌ Xatolik! Format: /block [user_id]")

@dp.callback_query(F.data == "admin_unblock")
async def admin_unblock_user(callback: CallbackQuery):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text("Blokdan chiqarish uchun ID yuboring:\n/unblock [user_id]")

@dp.message(Command("unblock"))
async def unblock_user_cmd(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    try:
        user_id = int(message.text.split()[1])
        unblock_user(user_id)
        await message.answer(f"✅ {user_id} blokdan chiqarildi!", reply_markup=admin_keyboard())
    except:
        await message.answer("❌ Xatolik! Format: /unblock [user_id]")

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text("📣 Hammaga yuboriladigan xabarni kiriting:")
    await state.set_state(BroadcastState.waiting_message)

@dp.message(BroadcastState.waiting_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.username != ADMIN_USERNAME:
        return
    
    users = get_all_users()
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"Yuborilmoqda... 0/{len(users)}")
    
    for i, user_id in enumerate(users):
        try:
            await bot.send_message(user_id, message.text, parse_mode="HTML")
            success += 1
        except:
            failed += 1
        
        if (i + 1) % 10 == 0:
            await status_msg.edit_text(f"Yuborilmoqda... {i+1}/{len(users)}")
        
        await asyncio.sleep(0.05)
    
    await status_msg.edit_text(
        f"✅ Xabar yuborildi!\n\n"
        f"Muvaffaqiyatli: {success}\n"
        f"Xatolik: {failed}",
        reply_markup=admin_keyboard()
    )
    await state.clear()

# Main
async def main():
    init_db()
    print("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())