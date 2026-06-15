import os
import random
import asyncio
import time
import re
import sqlite3
import datetime
import jdatetime
from zoneinfo import ZoneInfo
from pyrogram import Client, filters, errors, idle
from pyrogram.raw import functions, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ---------------------- Database functions ---------------------- #
def init_db():
    conn = sqlite3.connect("Operation_status.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Operation_status (
            admin INTEGER,
            operation_name TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def db_get_active_operation(admin_id: int):
    conn = sqlite3.connect("Operation_status.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Operation_status WHERE admin=? AND status='Active'", (admin_id,))
    row = cur.fetchone()
    conn.close()
    return row

def db_get_active_operation_any(except_admin: int):
    conn = sqlite3.connect("Operation_status.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Operation_status WHERE status='Active' AND admin != ?", (except_admin,))
    row = cur.fetchone()
    conn.close()
    return row

def db_add_operation(admin_id: int, operation_name: str):
    conn = sqlite3.connect("Operation_status.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO Operation_status (admin, operation_name, status) VALUES (?, ?, 'Active')", (admin_id, operation_name))
    conn.commit()
    conn.close()

def db_clear_active_for_admin(admin_id: int):
    conn = sqlite3.connect("Operation_status.db")
    cur = conn.cursor()
    cur.execute("UPDATE Operation_status SET status='Inactive' WHERE admin=? AND status='Active'", (admin_id,))
    conn.commit()
    conn.close()

init_db()
# ------------------ End Database functions ---------------------- #

# ------------------ Subscription Database functions ------------------ #
def init_subscription_db():
    conn = sqlite3.connect("Subscriptions.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Subscriptions (
            user INTEGER PRIMARY KEY,
            period TEXT,
            start_date TEXT,
            start_time TEXT,
            end_date TEXT,
            end_time TEXT,
            end_ts INTEGER
        )
    """)
    conn.commit()
    conn.close()

def db_add_subscription(user: int, period: str, start_date: str, start_time: str, end_date: str, end_time: str, end_ts: int):
    conn = sqlite3.connect("Subscriptions.db")
    cur = conn.cursor()
    # Insert or replace subscription
    cur.execute("""
        INSERT OR REPLACE INTO Subscriptions 
        (user, period, start_date, start_time, end_date, end_time, end_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user, period, start_date, start_time, end_date, end_time, end_ts))
    conn.commit()
    conn.close()

def db_get_subscription(user: int):
    conn = sqlite3.connect("Subscriptions.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Subscriptions WHERE user = ?", (user,))
    row = cur.fetchone()
    conn.close()
    return row

def db_remove_subscription(user: int):
    conn = sqlite3.connect("Subscriptions.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM Subscriptions WHERE user = ?", (user,))
    conn.commit()
    conn.close()

# New helper function to get all subscriptions
def db_get_all_subscriptions():
    conn = sqlite3.connect("Subscriptions.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Subscriptions")
    rows = cur.fetchall()
    conn.close()
    return rows

init_subscription_db()
# ------------------ End Subscription functions ---------------------- #

# ------------------ Limitation Database functions ---------------------- #
def init_limitation_db():
    conn = sqlite3.connect("Limitation.db")
    cur = conn.cursor()
    # تغییر نوع ستون start_ts به TEXT جهت ذخیره تاریخ شمسی به صورت رشته‌ای
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Limits (
            user INTEGER,
            operation_name TEXT,
            start_ts TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_operation_limit(user: int, operation_name: str):
    # تولید زمان شمسی جاری
    solar_now = jdatetime.datetime.fromgregorian(datetime=datetime.datetime.now(ZoneInfo("Asia/Tehran")))
    # فرمت موردنظر؛ (در سیستم‌های مبتنی بر لینوکس می‌توان از %-m/%-d استفاده کرد تا صفرهای اضافه حذف شود)
    try:
        solar_str = solar_now.strftime("%Y/%-m/%-d : %H:%M:%S")
    except Exception:
        # Windows-friendly fallback
        solar_str = solar_now.strftime("%Y/%m/%d : %H:%M:%S")
    conn = sqlite3.connect("Limitation.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO Limits (user, operation_name, start_ts) VALUES (?, ?, ?)", (user, operation_name, solar_str))
    conn.commit()
    conn.close()

def get_user_operation_count(user: int) -> int:
    conn = sqlite3.connect("Limitation.db")
    cur = conn.cursor()
    cur.execute("SELECT start_ts FROM Limits WHERE user=?", (user,))
    rows = cur.fetchall()
    count = 0
    now_greg = datetime.datetime.now(ZoneInfo("Asia/Tehran"))
    for (solar_str,) in rows:
        try:
            solar_dt = jdatetime.datetime.strptime(solar_str, "%Y/%-m/%-d : %H:%M:%S")
        except Exception:
            try:
                solar_dt = jdatetime.datetime.strptime(solar_str, "%Y/%m/%d : %H:%M:%S")
            except Exception as e:
                print(f"DEBUG parse error: {e}")
                continue
        greg_dt = solar_dt.togregorian()
        greg_dt = greg_dt.replace(tzinfo=ZoneInfo("Asia/Tehran"))
        diff = now_greg - greg_dt
        if diff.total_seconds() < 86400:
            count += 1
    conn.close()
    return count

init_limitation_db()
# ------------------ End Limitation functions ---------------------- #

api_id = 12134308
api_hash = '6d18eb5e69cfac7dfda54ce0fef6b07b'
bot_token = '8374341744:AAHcEWj7xhnjPpaoh70zIV3Pzo-3Z9WQVSU'
owner_id = 7193257772  # Owner's numeric ID

def load_admin_ids():
    if os.path.isfile('Admin.txt'):
        with open('Admin.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return [int(line.strip()) for line in lines if line.strip().isdigit()]
    return []

def save_admin_ids(admin_ids):
    with open('Admin.txt', 'w', encoding='utf-8') as f:
        for admin in admin_ids:
            f.write(f"{admin}\n")

# bot_admins will be computed dynamically using load_admin_ids() + owner_id
def get_bot_admins():
    return list(set(load_admin_ids() + [owner_id]))

sleeping = 2
step = None
tempClient = dict()
isWorking = list()

# Temporary variable for subscription process
tempSubUser = None

# Temp report link variables
tempReportLink_other = ""
tempReportLink_group_other = ""
tempReportLink_group_spam = ""
tempReportLink_group_pornography = ""
tempReportLink_group_violence = ""
tempReportLink_group_illegal = ""
tempReportLink_group_personal = ""
tempReportLink_group_copyright = ""
tempReportLink_child_abuse = ""
tempReportLink_scam = ""

# Preset report texts for pornography reports
porn_report_texts = [
    "This channel is distributing child sexual abuse material, leaked private photos, and pornography. Urgent removal needed.",
    "Sharing explicit pornography, leaked intimate images of women, and child exploitation content. Please ban now.",
    "Contains illegal child pornography, sexual exploitation, and leaked nude photos. Immediate action required.",
    "Posting obscene sexual abuse videos of minors and leaked girls’ private pictures. Remove this channel immediately.",
    "Spreading pornographic material along with leaked personal nude images without consent. Ban this account urgently.",
    "Distributing illegal pornography and child sexual exploitation content. Urgent moderation required.",
    "Sharing leaked private photos of girls and minors combined with explicit pornography. Immediate ban.",
    "This account is involved in child sexual abuse, leaked women’s intimate pictures, and hardcore pornography. Remove it.",
    "Uploading leaked nude pictures of minors and obscene sexual videos. Please take immediate action.",
    "Posting child pornography, sexual exploitation, and leaked personal content without consent. Ban now.",
    "Distributing obscene sexual material of minors and leaked private photos of women. Remove urgently.",
    "Sharing leaked personal nude pictures and child sexual exploitation material. Urgent removal.",
    "Distributing explicit pornography along with illegal leaked sexual images of minors. Please ban."
]

if not os.path.isdir('sessions'):
    os.mkdir('sessions')

if not os.path.isfile('app.txt'):
    with open('app.txt', 'w', encoding='utf-8') as file:
        file.write(f"{api_id} {api_hash}")

def parse_message_link(link: str):
    m = re.search(r"t\.me\/c\/(-?\d+)\/(\d+)", link)
    if m:
        chat_id = int("-100" + m.group(1))
        message_id = int(m.group(2))
        return chat_id, message_id
    m = re.search(r"t\.me\/([A-Za-z0-9_]+)\/(\d+)", link)
    if m:
        chat_id = "@" + m.group(1)
        message_id = int(m.group(2))
        return chat_id, message_id
    return None, None

async def randomString() -> str:
    size = random.randint(4, 8)
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVLXYZ') for _ in range(size))

async def randomAPP():
    with open('app.txt', 'r', encoding='utf-8') as file:
        apps = file.read().splitlines()
        app_id_val, app_hash_val = random.choice(apps).split()
    return app_id_val, app_hash_val

async def accountList():
    return [fname.split('.')[0] for fname in os.listdir('sessions') if os.path.isfile(os.path.join('sessions', fname))]

async def remainTime(TS):
    elapsed = time.time() - TS
    if elapsed < 60:
        return str(int(elapsed)) + ' ثانیه'
    mins = int(elapsed / 60)
    sec = elapsed % 60
    return str(int(mins)) + ' دقیقه و ' + str(int(sec)) + ' ثانیه'

# Global set to track subscription notifications so that each expired subscription is only notified once.
notified_subscriptions = set()

# Background task to periodically check subscriptions every 7 seconds.
async def subscription_checker():
    await asyncio.sleep(5)  # slight delay to let bot start
    while True:
        subs = db_get_all_subscriptions()
        now_ts = int(time.time())
        for sub in subs:
            # sub structure: (user, period, start_date, start_time, end_date, end_time, end_ts)
            user_id, period, s_date, s_time, e_date, e_time, e_ts = sub
            # If subscription is expired and not already notified:
            if now_ts >= e_ts and user_id not in notified_subscriptions:
                try:
                    await bot.send_message(user_id, "<b>اشتراک شما به اتمام رسید ❌</b>")
                except Exception as exc:
                    print(f"DEBUG subscription_checker error sending message to {user_id}: {exc}")
                notified_subscriptions.add(user_id)
        await asyncio.sleep(7)

# Mapping for English day names to Persian
DAY_MAPPING = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنج‌شنبه",
    "Friday": "جمعه"
}

bot = Client(
    "LampStack",
    bot_token=bot_token,
    api_id=api_id,
    api_hash=api_hash,
    ipv6=True
)

def get_group_report_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐬𝐜𝐚𝐦)', callback_data='group_report_scam')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐬𝐩𝐚𝐦)', callback_data='group_report_spam')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐩𝐨𝐫𝐧𝐨𝐠𝐫𝐚𝐩𝐡𝐲)', callback_data='group_report_pornography')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐕𝐢𝐨𝐥𝐞𝐧𝐜𝐞)', callback_data='group_report_violence')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐈𝐥𝐥𝐞𝐠𝐚𝐥)', callback_data='group_report_illegal')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐥𝐃𝐞𝐓𝐚𝐢𝐥𝐬)', callback_data='group_report_personal')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐂𝐨𝐩𝐲𝐫𝐢𝐠𝐡𝐭)', callback_data='group_report_copyright')],
        [InlineKeyboardButton('♛𝐑𝐄𝐏𝐎𝐑𝐓 (𝐂𝐡𝐢𝐥𝐝 𝐚𝐛𝐮𝐬𝐞)', callback_data='group_report_child_abuse')],
        [InlineKeyboardButton('🔙', callback_data='backToMenu')]
    ])

def get_main_menu_keyboard_owner():
    base_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('Aᴅᴅ ᴀᴄᴄᴏᴜɴᴛ ➕', callback_data='addAccount')],
        [InlineKeyboardButton('Aᴄᴄᴏᴜɴᴛ ʟɪsᴛ 📊', callback_data='accountsList')],
        [InlineKeyboardButton('✖️ Dᴇʟᴇᴛᴇ ᴀᴄᴄᴏᴜɴᴛ', callback_data='removeAccount')],
        [InlineKeyboardButton('Pᴏsᴛ Rᴇᴀᴄᴛɪᴏɴ Oᴘᴇʀᴀᴛɪᴏɴ ⚫️', callback_data='reActionEval')],
        [InlineKeyboardButton('🔴 Pᴏsᴛ Rᴇᴘᴏʀᴛ Oᴘᴇʀᴀᴛɪᴏɴ', callback_data='reportPostPublic')],
        [InlineKeyboardButton('♻️ Aᴄᴄᴏᴜɴᴛ Rᴇᴠɪᴇᴡ', callback_data='checkAccounts')],
        [InlineKeyboardButton('Sᴇᴛ Tɪᴍᴇ ⏱', callback_data='setTime')],
        [InlineKeyboardButton('📛 Cᴀɴᴄᴇʟ Aʟʟ Oᴘᴇʀᴀᴛɪᴏɴs', callback_data='endAllEvals')],
        [InlineKeyboardButton('☠ Rᴇᴘᴏʀᴛ', callback_data='groupReport')],
        [InlineKeyboardButton('⛔️ Bʟᴏᴄᴋ ᴜsᴇʀ', callback_data='blockUser')]
    ])
    kb = base_keyboard.inline_keyboard.copy()
    kb.append([InlineKeyboardButton('➕Aᴅᴅ ᴀᴅᴍɪɴ', callback_data='addAdmin')])
    kb.append([InlineKeyboardButton('➕Aᴅᴅ Sᴜʙsᴄʀɪʙᴇ', callback_data='addSubscribe')])
    # New subscription list button only shows active subscriptions
    kb.append([InlineKeyboardButton('📊 Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʟɪsᴛ ', callback_data='subscriptionList:page:0')])
    return InlineKeyboardMarkup(kb)

def get_main_menu_keyboard_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Aᴅᴅ ᴀᴄᴄᴏᴜɴᴛ ➕', callback_data='addAccount')],
        [InlineKeyboardButton('Pᴏsᴛ Rᴇᴀᴄᴛɪᴏɴ Oᴘᴇʀᴀᴛɪᴏɴ ⚫️', callback_data='reActionEval')],
        [InlineKeyboardButton('🔴 Pᴏsᴛ Rᴇᴘᴏʀᴛ Oᴘᴇʀᴀᴛɪᴏɴ', callback_data='reportPostPublic')],
        [InlineKeyboardButton('☠ Rᴇᴘᴏʀᴛ', callback_data='groupReport')],
        [InlineKeyboardButton('⛔️ Bʟᴏᴄᴋ ᴜsᴇʀ', callback_data='blockUser')]
    ])

print('Bot is Running ...')

@bot.on_message(filters.command(['start', 'cancel']) & filters.private)
async def StartResponse(client, message):
    global step, tempClient, isWorking
    try:
        tempClient.get('client') and await tempClient['client'].disconnect()
    except Exception:
        pass
    tempClient = {}
    step = None
    db_clear_active_for_admin(message.from_user.id)
    # update bot_admins dynamically
    bot_admins = get_bot_admins()
    user_id = message.from_user.id

    # For non-owner users, check subscription status
    if user_id != owner_id:
        sub = db_get_subscription(user_id)
        if not sub:
            await message.reply("<b>شما اشتراک ندارید ❌\n➖ جهت تهیه اشتراک : @taptrx</b>")
            return
        if time.time() > sub[6]:
            await message.reply("<b>اشتراک شما به پایان رسید ❌</b>")
            return

    # تغییر شرط: اگر کاربر مالک است یا اشتراک فعال دارد یا به عنوان ادمین ثبت شده، اجازه دسترسی داده شود.
    if user_id == owner_id:
        keyboard = get_main_menu_keyboard_owner()
    elif db_get_subscription(user_id) and time.time() <= db_get_subscription(user_id)[6]:
        keyboard = get_main_menu_keyboard_admin()  # منوی کاربر اشتراکی
    elif user_id in bot_admins:
        keyboard = get_main_menu_keyboard_admin()
    else:
        await message.reply("<b>❌ شما ادمین یا کاربر اشتراکی نیستید</b>")
        return
    await message.reply("<b>> به منوی اصلی خوش آمدید :</b>", reply_markup=keyboard, quote=True)

@bot.on_message(filters.regex('^/stop_\\w+') & filters.private)
async def StopEval(client, message):
    # تغییر نحوه بررسی دسترسی برای لغو عملیات:
    user_id = message.from_user.id
    bot_admins = get_bot_admins()
    sub = db_get_subscription(user_id)
    if user_id not in bot_admins and not (sub and time.time() <= sub[6]):
        await message.reply("<b>دسترسی ندارید!</b>")
        return
    global isWorking
    evalID = message.text.replace('/stop_', '')
    if evalID in isWorking:
        isWorking.remove(evalID)
        db_clear_active_for_admin(user_id)
        await message.reply(f"<b>عملیات با شناسه {evalID} با موفقیت خاتمه یافت ✅</b>")
    else:
        await message.reply("<b>عملیات موردنظر یافت نشد !</b>")

@bot.on_callback_query()
async def callbackQueries(client, query):
    global step, tempClient, isWorking
    chat_id = query.message.chat.id
    message_id = query.message.id
    data = query.data
    query_id = query.id

    # اگر یک ادمین دیگر در حال استفاده از ربات است، به صورت Alert نمایش داده شود.
    if db_get_active_operation_any(chat_id):
        await bot.answer_callback_query(query.id, "درحال حاضر ادمین دیگری درحال استفاده از ربات است ، لطفا تا اتمام عملیات صبر کنید ❤", show_alert=True)
        return

    # لیست دکمه‌هایی که باید محدودیت اعمال شود (برای کاربران اشتراکی و ادمین، به جز مالک)
    limited_operations = [
        'addAdmin', 'removeAdmin', 'addAccount', 'removeAccount', 'reportPostPublic',
        'reActionEval', 'voteEval', 'blockEval', 'blockUser',
        'group_report_spam', 'group_report_pornography', 'group_report_violence',
        'group_report_illegal', 'group_report_personal', 'group_report_copyright',
        'group_report_child_abuse', 'group_report_scam', 'addSubscribe'
    ]

    # بررسی محدودیت: فقط اگر کاربر مالک نیست، تعداد عملیات در 24 ساعت را چک کن
    if chat_id != owner_id and data in limited_operations:
        current_count = get_user_operation_count(chat_id)
        if current_count >= 2:
            await bot.answer_callback_query(query.id, "👤 کاربر گرامی حداکثر استفاده از ریپورتر در روز 2 عملیات است 📛", show_alert=True)
            return
        else:
            # ثبت عملیات در Limitation.db
            add_operation_limit(chat_id, data)

    if data in limited_operations:
        db_add_operation(chat_id, data)

    if chat_id == owner_id:
        if data == 'addAdmin':
            step = 'getAddAdminId'
            await bot.edit_message_text(chat_id, message_id, "<b>آیدی عددی کاربر را جهت ادمین شدن وارد کنید :</b>")
        elif data == 'removeAdmin':
            step = 'getRemoveAdminId'
            await bot.edit_message_text(chat_id, message_id, "<b>آیدی کاربر را جهت حذف شدن از ادمینی وارد کنید:</b>")
        elif data == 'addSubscribe':
            step = 'getSubUserId'
            await bot.edit_message_text(chat_id, message_id, "<b>آیدی عددی کاربر را جهت اضافه شدن اشتراک بفرستید :</b>")
    elif data == 'accountsList':
        await bot.edit_message_text(chat_id, message_id, "<b>شما دسترسی به این دکمه را ندارید!</b>")
        return

    if data == 'backToMenu':
        try:
            tempClient.get('client') and await tempClient['client'].disconnect()
        except Exception:
            pass
        tempClient = {}
        step = None
        db_clear_active_for_admin(chat_id)
        if chat_id == owner_id:
            keyboard = get_main_menu_keyboard_owner()
        else:
            keyboard = get_main_menu_keyboard_admin()
        await bot.edit_message_text(chat_id, message_id, "<b>> به منوی اصلی خوش آمدید :</b>", reply_markup=keyboard)
    elif data == 'endAllEvals':
        step = None
        evalsCount = len(isWorking)
        isWorking = list()
        await bot.invoke(functions.messages.SetBotCallbackAnswer(
            query_id=int(query_id),
            cache_time=1,
            alert=True,
            message=f"تمام {evalsCount} عملیات active با موفقیت متوقف شدند."
        ))
        db_clear_active_for_admin(chat_id)
    elif data == 'addAccount':
        step = 'getPhoneForLogin'
        await bot.edit_message_text(chat_id, message_id, "<b>- برای افزودن اکانت لطفا شماره مورد نظرتان را ارسال نمایید :</b>")
    elif data == 'removeAccount':
        step = 'removeAccount'
        await bot.edit_message_text(chat_id, message_id, "<b>- برای حذف اکانت لطفا شماره مورد نظرتان را ارسال نمایید :</b>")
    elif data == 'reportPostPublic':
        step = 'reportPostPublic'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پست کانال|گروه مورد نظر را ارسال نمایید :</b>")
    elif data == 'reActionEval':
        step = 'reActionEval'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفا اطلاعات مورد نیاز را به صورت:\nلینک پست در خط اول\nلیست ایموجی‌ها (جداشده با فاصله) در خط دوم\nتعداد کل واکنش‌ها در خط سوم وارد کنید.</b>")
    elif data == 'voteEval':
        step = 'voteEval'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفا در خط اول لینک پست و در خط دوم شماره گزینه موردنظر را وارد کنید :</b>")
    elif data == 'blockEval' or data == 'blockUser':
        step = 'blockEval'
        await bot.edit_message_text(chat_id, message_id, "<b>یوزرنیم کاربر مورد نظرتان را با @ وارد کنید :</b>")
    elif data == 'accountsList':
        if chat_id != owner_id:
            await bot.edit_message_text(chat_id, message_id, "<b>شما دسترسی به این دکمه را ندارید!</b>")
        else:
            accounts = await accountList()
            if accounts:
                text_to_reply = "<b>لیست اکانت‌ها:</b>\n" + "\n".join(accounts)
            else:
                text_to_reply = "<b>هیچ اکانتی موجود نیست.</b>"
            await bot.edit_message_text(chat_id, message_id, text_to_reply)
    elif data == 'checkAccounts':
        if len(await accountList()) == 0:
            await bot.invoke(functions.messages.SetBotCallbackAnswer(
                query_id=int(query_id),
                cache_time=1,
                alert=True,
                message="اکانتی یافت نشد ❗️"
            ))
        else:
            evalID = await randomString()
            isWorking.append(evalID)
            deleted = 0
            error = 0
            free = 0
            broken_accounts = []
            unknown_accounts = []
            cli = None
            TS = time.time()
            AllCount = len(await accountList())
            await bot.edit_message_text(chat_id, message_id, "<b>عملیات بررسی اکانت ها شروع شد ...</b>")
            for session in await accountList():
                if evalID not in isWorking:
                    break
                try:
                    await cli.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(sleeping)
                try:
                    api_id2, api_hash2 = await randomAPP()
                    cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                    await cli.connect()
                    await cli.resolve_peer("@durov")
                    await cli.disconnect()
                except (errors.SessionRevoked, errors.UserDeactivated, errors.AuthKeyUnregistered, errors.UserDeactivatedBan, errors.Unauthorized) as exc:
                    print(f"DEBUG checkAccounts exception in session {session}: {exc}")
                    try:
                        await cli.disconnect()
                    except Exception as ex:
                        print(f"DEBUG disconnect error in checkAccounts for session {session}: {ex}")
                    try:
                        os.unlink(f'sessions/{session}.session')
                    except Exception:
                        pass
                    deleted += 1
                    broken_accounts.append(session)
                except Exception as e:
                    print(f"DEBUG checkAccounts unknown error in session {session}: {e}")
                    try:
                        await cli.disconnect()
                    except Exception as ex:
                        print(f"DEBUG disconnect error in checkAccounts for session {session}: {ex}")
                    error += 1
                    unknown_accounts.append(session)
                else:
                    free += 1
                finally:
                    spendTime = await remainTime(TS)
                    allChecked = deleted + free + error
                    await bot.edit_message_text(
                        chat_id,
                        message_id,
                        f'''♻️ عملیات بررسی اکانت های ربات ...

• کل اکانت ها : {AllCount}
• اکانت های بررسی شده : {allChecked}
• اکانت های سالم : {free}
• سشن های خراب : {deleted}
• خطاهای ناشناخته : {error}
• زمان سپری شده : {spendTime}

برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.

📛 Bʀᴏᴋɴᴇᴅ ᴀᴄᴄᴏᴜɴᴛ : {" | ".join(broken_accounts) if broken_accounts else "هیچ"}
⚠️ Uɴᴋɴᴏʀν ᴀᴄᴄᴏᴜɴᴛ : {" | ".join(unknown_accounts) if unknown_accounts else "هیچ"}'''
                    )
            try:
                isWorking.remove(evalID)
            except Exception:
                pass
            allChecked = deleted + free + error
            spendTime = await remainTime(TS)
            db_clear_active_for_admin(chat_id)
            my_keyboard = [
                [InlineKeyboardButton('🔙', callback_data='backToMenu')],
            ]
            await bot.send_message(
                chat_id,
                f'''عملیات بررسی اکانت ها با موفقیت به اتمام رسید ✅

• کل اکانت ها : {AllCount}
• اکانت های بررسی شده : {allChecked}
• سالم : {free}
• سشن خراب : {deleted}
• خطاهای ناشناخته : {error}
• زمان سپری شده : {spendTime}

📛 Bʀᴏᴋɴᴇᴅ ᴀᴄᴄᴏᴜɴᴛ : {" | ".join(broken_accounts) if broken_accounts else "هیچ"}
⚠️ Uɴᴋɴᴏʀν ᴀᴄᴄᴏᴜɴᴛ : {" | ".join(unknown_accounts) if unknown_accounts else "هیچ"}''',
                reply_markup=InlineKeyboardMarkup(my_keyboard)
            )
    elif data == 'setTime':
        if chat_id == owner_id:
            step = 'setTime'
            await bot.edit_message_text(chat_id, message_id, "<b>لطفاً زمان (در ثانیه) جدید را وارد کنید:</b>")
        else:
            await bot.answer_callback_query(query.id, "دسترسی ندارید", show_alert=True)
    elif data == 'groupReport':
        await bot.edit_message_text(chat_id, message_id, "<b>> لطفاً یکی از گزینه‌های گزارش زیر را انتخاب کنید :</b>", reply_markup=get_group_report_keyboard())
    elif data == 'group_report_spam':
        step = 'group_report_spam_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_pornography':
        step = 'group_report_pornography_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_violence':
        step = 'group_report_violence_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_illegal':
        step = 'group_report_illegal_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_personal':
        step = 'group_report_personal_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_copyright':
        step = 'group_report_copyright_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_child_abuse':
        step = 'group_report_child_abuse_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")
    elif data == 'group_report_scam':
        step = 'group_report_scam_request_link'
        await bot.edit_message_text(chat_id, message_id, "<b>لطفاً لینک پیام ها را ارسال کنید : (هر خط یک لینک)</b>")

@bot.on_message(filters.text & filters.private)
async def TextResponse(client, message):
    global step, isWorking, tempClient, api_hash, api_id, sleeping, tempSubUser
    chat_id = message.chat.id
    text = message.text

    if db_get_active_operation(chat_id) is None and step is None:
        await message.reply("<b>هیچ عملی در جریان نمی‌باشد.</b>")
        return

    if step == 'getAddAdminId':
        if text.strip().isdigit():
            admin_id = int(text.strip())
            bot_admins = get_bot_admins()
            if admin_id not in bot_admins:
                bot_admins.append(admin_id)
                save_admin_ids([a for a in bot_admins if a != owner_id])
                now = datetime.datetime.now(ZoneInfo("Asia/Tehran"))
                jnow = jdatetime.datetime.fromgregorian(datetime=now)
                start_date = jnow.strftime("%Y/%m/%d")
                start_time = jnow.strftime("%H:%M:%S")
                lifetime_end_date = "9999/12/31"
                lifetime_end_time = "23:59:59"
                lifetime_end_ts = 253402300799
                db_add_subscription(admin_id, "مادام العمر", start_date, start_time, lifetime_end_date, lifetime_end_time, lifetime_end_ts)
                await message.reply("<b>اضافه شد ✅</b>")
                if admin_id != owner_id:
                    try:
                        await bot.send_message(admin_id, "<b>اشتراک مادام العمر به شما اضافه شد ✅</b>")
                    except Exception as exc:
                        print(f"DEBUG error sending admin subscription message: {exc}")
            else:
                await message.reply("<b>کاربر از قبل ادمین است.</b>")
        else:
            await message.reply("<b>ورودی معتبر نیست. لطفا یک آیدی عددی وارد کنید.</b>")
        step = None
        db_clear_active_for_admin(chat_id)
    elif step == 'getRemoveAdminId':
        if text.strip().isdigit():
            admin_id = int(text.strip())
            bot_admins = get_bot_admins()
            if admin_id in bot_admins and admin_id != owner_id:
                bot_admins.remove(admin_id)
                save_admin_ids([a for a in bot_admins if a != owner_id])
                await message.reply("<b>حذف شد ❌</b>")
            else:
                await message.reply("<b>آیدی وارد شده یافت نشد یا مالک قابل حذف نیست.</b>")
        else:
            await message.reply("<b>ورودی معتبر نیست. لطفا یک آیدی عددی وارد کنید.</b>")
        step = None
        db_clear_active_for_admin(chat_id)

    # --------------- Subscription adding steps ---------------
    elif step == 'getSubUserId':
        if text.strip().isdigit():
            tempSubUser = int(text.strip())
            step = 'getSubPeriod'
            await message.reply("<b>🎟 لطفا مقدار اشتراک را وارد کنید (مثلا 2 روز یا 1 ساعت یا 1 دقیقه) :</b>")
        else:
            await message.reply("<b>ورودی معتبر نیست. لطفا یک آیدی عددی وارد کنید.</b>")
    elif step == 'getSubPeriod':
        m = re.match(r"(\d+)\s*(روز|ساعت|دقیقه|ثانیه)", text.strip())
        if not m:
            await message.reply("<b>فرمت اشتراک نامعتبر است. لطفا به صورت (مثلا: 2 روز) وارد کنید.</b>")
            return
        number, unit = m.groups()
        number = int(number)
        if unit == "روز":
            delta = datetime.timedelta(days=number)
        elif unit == "ساعت":
            delta = datetime.timedelta(hours=number)
        elif unit == "دقیقه":
            delta = datetime.timedelta(minutes=number)
        elif unit == "ثانیه":
            delta = datetime.timedelta(seconds=number)
        else:
            await message.reply("<b>واحد زمان مشخص نشده است.</b>")
            return

        now = datetime.datetime.now(ZoneInfo("Asia/Tehran"))
        end = now + delta
        jstart = jdatetime.datetime.fromgregorian(datetime=now)
        jend = jdatetime.datetime.fromgregorian(datetime=end)
        start_date = jstart.strftime("%Y/%m/%d")
        start_time = jstart.strftime("%H:%M:%S")
        end_date = jend.strftime("%Y/%m/%d")
        end_time = jend.strftime("%H:%M:%S")
        end_day_eng = jend.strftime("%A")
        end_day = DAY_MAPPING.get(end_day_eng, end_day_eng)
        period_text = f"{number} {unit}"
        end_ts = int(end.timestamp())
        db_add_subscription(tempSubUser, period_text, start_date, start_time, end_date, end_time, end_ts)
        reply_owner = f"<b>اشتراک به مدت {period_text} به کاربر {tempSubUser} اضافه شد ✅\n📆تاریخ اتمام اشتراک : {end_day} مورخ {end_date} ساعت {end_time}</b>"
        await message.reply(reply_owner)
        try:
            await bot.send_message(
                tempSubUser,
                f"<b>اشتراک ربات ریپورتر برای شما به مدت {period_text} فعال شد ✅\n📆تاریخ اتمام اشتراک : {end_day} مورخ {end_date} ساعت {end_time}</b>"
            )
        except Exception as exc:
            print(f"DEBUG sending subscription message error: {exc}")
        step = None
        db_clear_active_for_admin(chat_id)
    # -----------------------------------------------------------

    # Phone login flow and other operations
    if step == 'getPhoneForLogin' and text.replace('+', '').replace(' ', '').replace('-', '').isdigit():

        phone_number = text.replace('+', '').replace(' ', '').replace('-', '')

        if os.path.isfile(f'sessions/{phone_number}.session'):
            await message.reply("<b>این شماره از قبل در پوشه sessions سرور موجود است !</b>")

        else:

            tempClient['number'] = phone_number

            tempClient['client'] = Client(
                f'sessions/{phone_number}',
                int(api_id),
                api_hash,
                ipv6=True
            )

            await tempClient['client'].connect()

            try:
                tempClient['response'] = await tempClient['client'].send_code(phone_number)

            except (
                errors.BadRequest,
                errors.PhoneNumberBanned,
                errors.PhoneNumberFlood,
                errors.PhoneNumberInvalid
            ) as exc:

                print(f"DEBUG send_code error for {phone_number}: {exc}")
                await message.reply("<b>خطایی رخ داد هنگام ارسال کد. لطفاً شماره را بررسی کنید.</b>")

            else:

                step = 'get5DigitsCode'

                await message.reply(
                    f"<b>کد 5 رقمی به شماره {phone_number} ارسال شد ✅</b>"
                )

    elif step == 'get5DigitsCode' and text.replace(' ', '').isdigit():

        telegram_code = text.replace(' ', '')

        try:
            await tempClient['client'].sign_in(
                tempClient['number'],
                tempClient['response'].phone_code_hash,
                telegram_code
            )

        except errors.PhoneCodeExpired as exc:
            print(f"DEBUG sign_in expired error: {exc}")
            try:
                await tempClient['client'].disconnect()
            except Exception:
                pass
            tempClient.clear()
            step = None
            await message.reply("<b>کد ارسال شده منقضی شده است, لطفا عملیات را /cancel کنید و مجدداً تلاش کنید.</b>")

        except (errors.PhoneCodeInvalid, errors.BadRequest) as exc:
            print(f"DEBUG sign_in invalid error: {exc}")
            await message.reply("<b>کد وارد شده اشتباه است یا منقضی شده, لطفا دوباره تلاش کنید.</b>")

        except errors.AuthKeyUnregistered as exc:
            # Requires sign_up (new account)
            print(f"DEBUG sign_up error: {exc}")
            try:
                name = await randomString()
                await tempClient['client'].sign_up(tempClient['number'], tempClient['response'].phone_code_hash, name)
            except Exception as exc2:
                print(f"DEBUG sign_up second error: {exc2}")
            try:
                await tempClient['client'].disconnect()
            except Exception:
                pass
            tempClient.clear()
            step = 'getPhoneForLogin'
            await message.reply("<b>اکانت با موفقیت ثبت شد ✅\nدرصورتیکه قصد افزودن شماره دارید, شماره موردنظر را ارسال کنید</b>")

        except errors.SessionPasswordNeeded:
            step = 'SessionPasswordNeeded'
            await message.reply("<b>لطفا رمز تایید دو مرحله ای را وارد نمایید :</b>")

        except Exception as exc:
            # Generic fallback
            print(f"DEBUG sign_in unexpected error: {exc}")
            try:
                await tempClient['client'].disconnect()
            except Exception:
                pass
            await message.reply("<b>کد وارد شده نامعتبر است یا خطای دیگری رخ داده است ❌</b>")

        else:
            # Successful sign-in
            try:
                await tempClient['client'].disconnect()
            except Exception:
                pass
            tempClient.clear()
            step = 'getPhoneForLogin'
            await message.reply(
                "<b>اکانت با موفقیت ثبت شد ✅\nدرصورتیکه قصد افزودن شماره دارید, شماره موردنظر را ارسال کنید</b>"
            )

    elif step == 'SessionPasswordNeeded':
        twoFaPass = text
        try:
            await tempClient['client'].check_password(twoFaPass)
        except errors.BadRequest as exc:
            print(f"DEBUG check_password error: {exc}")
            await message.reply("<b>رمز وارد شده اشتباه میباشد, لطفا مجدداً ارسال نمایید.</b>")
        except Exception as exc:
            print(f"DEBUG check_password unexpected error: {exc}")
            await message.reply("<b>خطا در بررسی رمز. لطفاً دوباره تلاش کنید.</b>")
        else:
            try:
                await tempClient['client'].disconnect()
            except Exception:
                pass
            tempClient.clear()
            step = 'getPhoneForLogin'
            await message.reply("<b>اکانت با موفقیت ثبت شد ✅\nدرصورتیکه قصد افزودن شماره دارید, شماره موردنظر را ارسال کنید</b>")

    if step == 'removeAccount':
        phone_number = text.replace('+', '').replace(' ', '').replace('-', '')
        if not os.path.isfile(f'sessions/{phone_number}.session'):
            await message.reply("<b>شماره مورد نظر در سرور یافت نشد !</b>")
        else:
            try:
                await bot.send_document(message.chat.id, f'sessions/{phone_number}.session', caption="<b>شماره مورد نظر با موفقیت حذف شد ✅\nسشن پایروگرام حذف شد.</b>")
            except Exception:
                # send_document may fail in some contexts; continue to delete file anyway
                pass
            try:
                os.unlink(f'sessions/{phone_number}.session')
            except Exception as exc:
                print(f"DEBUG removeAccount unlink error: {exc}")
            await message.reply("<b>شماره و سشن مورد نظر حذف شد ✅</b>")
        step = None
        db_clear_active_for_admin(chat_id)

    if step == 'setTime':
        try:
            sleeping = float(text)
            await message.reply("<b>زمان جدید با موفقیت تنظیم شد ✅</b>")
        except Exception as exc:
            print(f"DEBUG setTime error: {exc}")
            await message.reply("<b>ورودی نامعتبر است.</b>")
        step = None
        db_clear_active_for_admin(chat_id)

    if step == 'joinAccounts':
        evalID = await randomString()
        isWorking.append(evalID)
        link = text.split()[0].replace('@', '').replace('+', 'joinchat/')
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        msg = await message.reply("<b>عملیات عضویت شروع شد ...</b>")
        for session in await accountList():
            if evalID not in isWorking:
                break
            all += 1
            await asyncio.sleep(sleeping)
            try:
                api_id2, api_hash2 = await randomAPP()
                cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                await cli.connect()
                await asyncio.sleep(0.2)
                await cli.join_chat(link)
            except Exception as exc:
                print(f"DEBUG joinAccounts error in session {session}: {exc}")
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in joinAccounts for session {session}: {ex}")
                error += 1
            else:
                done += 1
            finally:
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in joinAccounts final for session {session}: {ex}")
                spendTime = await remainTime(TS)
                await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات عضویت اکانت های ربات ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.''')
        try:
            isWorking.remove(evalID)
        except Exception:
            pass
        spendTime = await remainTime(TS)
        await message.reply(f'''<b>عملیات عضویت با موفقیت به پایان رسید ✅
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}</b>''')
        db_clear_active_for_admin(chat_id)

    if step == 'leaveAccounts':
        evalID = await randomString()
        isWorking.append(evalID)
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        msg = await message.reply("<b>عملیات خروج شروع شد ...</b>")
        for session in await accountList():
            if evalID not in isWorking:
                break
            all += 1
            await asyncio.sleep(sleeping)
            try:
                api_id2, api_hash2 = await randomAPP()
                cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                await cli.connect()
                await asyncio.sleep(0.2)
                await cli.leave_chat(int(text), delete=True)
            except Exception as exc:
                print(f"DEBUG leaveAccounts error in session {session}: {exc}")
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in leaveAccounts for session {session}: {ex}")
                error += 1
            else:
                done += 1
            finally:
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in leaveAccounts final for session {session}: {ex}")
                spendTime = await remainTime(TS)
                await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات خروج اکانت های ربات ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.''')
        try:
            isWorking.remove(evalID)
        except Exception:
            pass
        spendTime = await remainTime(TS)
        await message.reply(f'''<b>عملیات خروج با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        db_clear_active_for_admin(chat_id)

    if step == 'sendViewToPost':
        evalID = await randomString()
        isWorking.append(evalID)
        try:
            username = text.split('/')[3]
            msg_id = int(text.split('/')[4])
        except Exception:
            await message.reply("<b>لینک نامعتبر است.</b>")
            step = None
            db_clear_active_for_admin(chat_id)
            return
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        msg = await message.reply("<b>عملیات ویو پست کانال شروع شد ...</b>")
        for session in await accountList():
            if evalID not in isWorking:
                break
            all += 1
            await asyncio.sleep(sleeping)
            try:
                api_id2, api_hash2 = await randomAPP()
                cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                await cli.connect()
                await asyncio.sleep(0.2)
                peer = await cli.resolve_peer("@" + username)
                await cli.get_messages("@" + username, [msg_id])
                await cli.invoke(functions.messages.GetMessagesViews(
                    peer=peer,
                    id=[msg_id],
                    increment=True))
            except Exception as exc:
                print(f"DEBUG sendViewToPost error in session {session}: {exc}")
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in sendViewToPost for session {session}: {ex}")
                error += 1
            else:
                done += 1
            finally:
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG disconnect error in sendViewToPost final for session {session}: {ex}")
                spendTime = await remainTime(TS)
                await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ارسال ویو اکانت های ربات ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.''')
        try:
            isWorking.remove(evalID)
        except Exception:
            pass
        spendTime = await remainTime(TS)
        await message.reply(f'''<b>عملیات بازدید پست کانال با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        db_clear_active_for_admin(chat_id)

    if step == 'reportPostPublic':
        evalID = await randomString()
        isWorking.append(evalID)
        parts = text.split('/')
        # try to parse link safely
        try:
            if parts[3] != 'c':
                peerID = '@' + parts[3]
                peerMessageID = int(parts[4])
            else:
                peerID = int('-100' + parts[4])
                peerMessageID = int(parts[5])
        except Exception:
            await message.reply("<b>لینک نامعتبر است. لطفا لینک درست ارسال کنید.</b>")
            step = None
            db_clear_active_for_admin(chat_id)
            return
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        if parts[3].isdigit():
            await message.reply("<b>لینکی که برام ارسال کردی مربوط به یک چت خصوصی است ❗️</b>")
        else:
            msg = await message.reply("<b>عملیات ریپورت پست کانال عمومی شروع شد ...</b>")
            for session in await accountList():
                if evalID not in isWorking:
                    break
                all += 1
                await asyncio.sleep(sleeping)
                try:
                    api_id2, api_hash2 = await randomAPP()
                    cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                    await cli.connect()
                    peer = await cli.resolve_peer(peerID)
                    msg_objs = await cli.get_messages(peerID, [peerMessageID])
                    if not msg_objs:
                        raise ValueError("Message does not exist")
                    # قبل از ریپورت پیام را ویو کن
                    try:
                        await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[peerMessageID], increment=True))
                        await asyncio.sleep(0.1)
                    except Exception as view_exception:
                        print(f"DEBUG view action error in session {session}: {view_exception}")
                    try:
                        res = await cli.invoke(functions.messages.Report(
                            peer=peer,
                            id=[peerMessageID],
                            reason=types.InputReportReasonPornography(),
                            message=''
                        ))
                    except Exception as e:
                        print(f"DEBUG reportPostPublic exception in session {session}: {e}")
                        error += 1
                    else:
                        done += 1
                except Exception as e:
                    print(f"DEBUG reportPostPublic exception in session {session}: {e}")
                    error += 1
                finally:
                    try:
                        await cli.disconnect()
                    except Exception as ex:
                        print(f"DEBUG reportPostPublic disconnect error in session {session}: {ex}")
                    spendTime = await remainTime(TS)
                    await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت پست کانال ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.''')
            try:
                isWorking.remove(evalID)
            except Exception:
                pass
            spendTime = await remainTime(TS)
            await message.reply(f'''<b>عملیات ریپورت پست با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        step = None
        db_clear_active_for_admin(chat_id)

    if step == 'reActionEval':
        evalID = await randomString()
        isWorking.append(evalID)
        try:
            peerID = '@' + text.split("\n")[0].split('/')[3]
            peerMessageID = int(text.split("\n")[0].split('/')[4])
            emojies = text.split("\n")[1].split()
            countOfWork = int(text.split("\n")[2])
        except Exception:
            await message.reply("<b>فرمت ورودی نامعتبر است. لطفا مطابق راهنما ارسال کنید.</b>")
            step = None
            db_clear_active_for_admin(chat_id)
            return
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        if text.split("\n")[0].split('/')[3].isdigit():
            await message.reply("<b>لینکی که برام ارسال کردی مربوط به یک چت خصوصی است ❗️</b>")
        else:
            msg = await message.reply("<b>عملیات ارسال ری اکشن شروع شد ...</b>")
            for session in await accountList():
                if all >= countOfWork:
                    break
                if evalID not in isWorking:
                    break
                all += 1
                await asyncio.sleep(sleeping)
                try:
                    api_id2, api_hash2 = await randomAPP()
                    cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                    await cli.connect()
                    await asyncio.sleep(0.2)
                    await cli.send_reaction(peerID, peerMessageID, random.choice(emojies))
                except Exception as e:
                    print(f"DEBUG reActionEval error in session {session}: {e}")
                    error += 1
                else:
                    done += 1
                finally:
                    try:
                        await cli.disconnect()
                    except Exception as ex:
                        print(f"DEBUG reActionEval disconnect error in session {session}: {ex}")
                    spendTime = await remainTime(TS)
                    await bot.edit_message_text(chat_id, msg.id,
                        f'''♻️ عملیات ارسال ری اکشن پست کانال ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور ( /stop_{evalID} ) استفاده نمایید.''')
            try:
                isWorking.remove(evalID)
            except Exception:
                pass
            spendTime = await remainTime(TS)
            await message.reply(f'''<b>عملیات ری اکشن پست با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        step = None
        db_clear_active_for_admin(chat_id)

    if step == 'voteEval':
        evalID = await randomString()
        isWorking.append(evalID)
        try:
            peerID = '@' + text.split("\n")[0].split('/')[3]
            peerMessageID = int(text.split("\n")[0].split('/')[4])
            opt = text.split("\n")[1]
        except Exception:
            await message.reply("<b>فرمت ورودی نامعتبر است.</b>")
            step = None
            db_clear_active_for_admin(chat_id)
            return
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        if not opt.isdigit():
            await message.reply("<b>گزینه وارد شده صحیح نمیباشد ❗️</b>")
        else:
            msg = await message.reply("<b>عملیات ارسال نظرسنجی شروع شد ...</b>")
            for session in await accountList():
                if evalID not in isWorking:
                    break
                all += 1
                await asyncio.sleep(sleeping)
                try:
                    api_id2, api_hash2 = await randomAPP()
                    cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                    await cli.connect()
                    await asyncio.sleep(0.2)
                    peer = await cli.resolve_peer(peerID)
                    await cli.vote_poll(peer, peerMessageID, int(opt))
                except Exception as e:
                    print(f"DEBUG voteEval error in session {session}: {e}")
                    error += 1
                else:
                    done += 1
                finally:
                    try:
                        await cli.disconnect()
                    except Exception as ex:
                        print(f"DEBUG voteEval disconnect error in session {session}: {ex}")
                    spendTime = await remainTime(TS)
                    await bot.edit_message_text(chat_id, msg.id,
                        f'''♻️ عملیات نظرسنجی ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
            try:
                isWorking.remove(evalID)
            except Exception:
                pass
            spendTime = await remainTime(TS)
            await message.reply(f'''<b>عملیات نظرسنجی با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        step = None
        db_clear_active_for_admin(chat_id)

    if step == 'blockEval':
        evalID = await randomString()
        isWorking.append(evalID)
        peerID = text.replace('@', '')
        allAcccounts = len(await accountList())
        all = 0
        error = 0
        done = 0
        TS = time.time()
        msg = await message.reply("<b>عملیات بلاک کاربر شروع شد ...</b>")
        for session in await accountList():
            if evalID not in isWorking:
                break
            all += 1
            await asyncio.sleep(sleeping)
            try:
                api_id2, api_hash2 = await randomAPP()
                cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                await cli.connect()
                await asyncio.sleep(0.2)
                await cli.block_user(peerID)
            except Exception as e:
                print(f"DEBUG blockEval error in session {session}: {e}")
                error += 1
            else:
                done += 1
            finally:
                try:
                    await cli.disconnect()
                except Exception as ex:
                    print(f"DEBUG blockEval disconnect error in session {session}: {ex}")
                spendTime = await remainTime(TS)
                await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات بلاک کاربر ...
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
        try:
            isWorking.remove(evalID)
        except Exception:
            pass
        spendTime = await remainTime(TS)
        await message.reply(f'''<b>عملیات بلاک کاربر با موفقیت به پایان رسید ✅</b>
• اکانت های بررسی شده : {all}/{allAcccounts}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
        step = None
        db_clear_active_for_admin(chat_id)

    # ----------------- Group report (other) -----------------
    elif step == 'group_report_other_request_link':
         global tempReportLink_group_other
         tempReportLink_group_other = text.strip()
         step = 'group_report_other'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_other':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 3:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_other parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_group_other.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (other) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     cli = None
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         print(f"[DEBUG] پیام دریافت شد: {msg_objs}")
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         try:
                             res = await cli.invoke(functions.messages.Report(
                                 peer=peer,
                                 id=[message_id_extracted],
                                 reason=types.InputReportReasonOther(),
                                 message=report_text
                             ))
                         except Exception as e:
                             print(f"DEBUG group_report_other exception in session {session}: {e}")
                             error += 1
                         else:
                             print(f"DEBUG group_report_other success in session {session}")
                             done += 1
                     except Exception as e:
                         print(f"[DEBUG] خطا در دریافت پیام یا اتصال: {e}")
                         error += 1
                     finally:
                         if cli:
                             try:
                                 await cli.disconnect()
                             except Exception as ex:
                                 print(f"DEBUG group_report_other disconnect error in session {session}: {ex}")
                 spendTime = await remainTime(TS)
                 await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (other)
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (other) با موفقیت به پایان رسید ✅</b>
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (spam) -----------------
    elif step == 'group_report_spam_request_link':
         global tempReportLink_group_spam
         tempReportLink_group_spam = text.strip()
         step = 'group_report_spam'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_spam':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 3:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_spam number parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_group_spam.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (spam) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonSpam(),
                             message=report_text
                         ))
                     except Exception as e:
                         print(f"DEBUG group_report_spam exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_spam disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (spam)
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (spam) با موفقیت به پایان رسید ✅</b>
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (pornography) -----------------
    elif step == 'group_report_pornography_request_link':
         global tempReportLink_group_pornography
         tempReportLink_group_pornography = text.strip()
         step = 'group_report_pornography_auto'
         await message.reply("<b>در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید :</b>")
    elif step == 'group_report_pornography_auto':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 2:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_pornography parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         links = [l.strip() for l in tempReportLink_group_pornography.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (pornography) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for idx, session in enumerate(chosen_accounts):
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     curr_text = porn_report_texts[idx % len(porn_report_texts)]
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonPornography(),
                             message=curr_text))
                     except Exception as e:
                         print(f"DEBUG group_report_pornography exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_pornography disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (pornography)
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (pornography) با موفقیت به پایان رسید ✅</b>
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (Violence) -----------------
    elif step == 'group_report_violence_request_link':
         global tempReportLink_group_violence
         tempReportLink_group_violence = text.strip()
         step = 'group_report_violence'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_violence':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 3:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_violence parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_group_violence.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (Violence) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonViolence(),
                             message=report_text))
                     except Exception as e:
                         print(f"DEBUG group_report_violence exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_violence disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (Violence)
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (Violence) با موفقیت به پایان رسید ✅</b>
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (Illegal) -----------------
    elif step == 'group_report_illegal_request_link':
         global tempReportLink_group_illegal
         tempReportLink_group_illegal = text.strip()
         step = 'group_report_illegal'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_illegal':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 3:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_illegal parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_group_illegal.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (Illegal) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonIllegalDrugs(),
                             message=report_text))
                     except Exception as e:
                         print(f"DEBUG group_report_illegal exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_illegal disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (Illegal)
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (Illegal) با موفقیت به پایان رسید ✅</b>
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (PersonalDetails) -----------------
    elif step == 'group_report_personal_request_link':
         global tempReportLink_group_personal
         tempReportLink_group_personal = text.strip()
         step = 'group_report_personal'
         await message.reply("<b>در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید :</b>")
    elif step == 'group_report_personal':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 2:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_personal parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:]) if len(parts) > 2 else ""
         links = [l.strip() for l in tempReportLink_group_personal.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (PersonalDetails) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonPersonalDetails(),
                             message=report_text))
                     except Exception as e:
                         print(f"DEBUG group_report_personal exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_personal disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (PersonalDetails)
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (PersonalDetails) با موفقیت به پایان رسید ✅</b>
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (Copyright) -----------------
    elif step == 'group_report_copyright_request_link':
         global tempReportLink_group_copyright
         tempReportLink_group_copyright = text.strip()
         step = 'group_report_copyright'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_copyright':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 2:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_copyright parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_group_copyright.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (Copyright) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonCopyright(),
                             message=report_text))
                     except Exception as e:
                         print(f"DEBUG group_report_copyright exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_copyright disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (Copyright)
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (Copyright) با موفقیت به پایان رسید ✅</b>
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (Child Abuse) -----------------
    elif step == 'group_report_child_abuse_request_link':
         global tempReportLink_child_abuse
         tempReportLink_child_abuse = text.strip()
         step = 'group_report_child_abuse'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و در خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_child_abuse':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 2:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت و در خط دوم تعداد گزارش را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_child_abuse parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_child_abuse.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (ChildAbuse) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         res = await cli.invoke(functions.messages.Report(
                             peer=peer,
                             id=[message_id_extracted],
                             reason=types.InputReportReasonChildAbuse(),
                             message=report_text))
                     except Exception as e:
                         print(f"DEBUG group_report_child_abuse exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_child_abuse disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (ChildAbuse)
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (ChildAbuse) با موفقیت به پایان رسید ✅</b>
• کل ریپورت ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)

    # ----------------- Group report (scam) -----------------
    elif step == 'group_report_scam_request_link':
         global tempReportLink_scam
         tempReportLink_scam = text.strip()
         step = 'group_report_scam_auto'
         await message.reply("<b>در خط اول تعداد اکانت، در خط دوم تعداد گزارش و از خط سوم به بعد متن ریپورت را وارد کنید :</b>")
    elif step == 'group_report_scam_auto':
         evalID = await randomString()
         isWorking.append(evalID)
         parts = text.split("\n")
         if len(parts) < 3:
             await message.reply("<b>ورودی نامعتبر! لطفاً در خط اول تعداد اکانت، در خط دوم تعداد گزارش و از خط سوم به بعد متن ریپورت را وارد کنید.</b>")
             return
         try:
             acc_count = int(parts[0].strip())
             rpt_count = int(parts[1].strip())
         except Exception as exc:
             print(f"DEBUG group_report_scam parse error: {exc}")
             await message.reply("<b>عدد وارد شده معتبر نیست!</b>")
             return
         report_text = "\n".join(parts[2:])
         links = [l.strip() for l in tempReportLink_scam.splitlines() if l.strip()]
         total_reports = len(links) * acc_count * rpt_count
         accounts = await accountList()
         chosen_accounts = accounts[:acc_count]
         all_reports = 0
         error = 0
         done = 0
         TS = time.time()
         msg = await message.reply("<b>♻️ عملیات ریپورت (scam) شروع شد ...</b>")
         for link in links:
             chat_id_extracted, message_id_extracted = parse_message_link(link)
             if chat_id_extracted is None or message_id_extracted is None:
                 await message.reply("<b>یکی از لینک‌های وارد شده معتبر نیست. لطفاً لینک درست را ارسال نمایید.</b>")
                 continue
             for i in range(rpt_count):
                 for session in chosen_accounts:
                     if evalID not in isWorking:
                         break
                     all_reports += 1
                     await asyncio.sleep(sleeping)
                     try:
                         api_id2, api_hash2 = await randomAPP()
                         cli = Client(f'sessions/{session}', api_id2, api_hash2, ipv6=True)
                         await cli.connect()
                         peer = await cli.resolve_peer(chat_id_extracted)
                         msg_objs = await cli.get_messages(chat_id_extracted, [message_id_extracted])
                         if not msg_objs:
                             raise ValueError("Message does not exist")
                         # ویو کردن پیام قبل از ریپورت
                         try:
                             await cli.invoke(functions.messages.GetMessagesViews(peer=peer, id=[message_id_extracted], increment=True))
                             await asyncio.sleep(0.1)
                         except Exception as view_exception:
                             print(f"DEBUG view action error in session {session}: {view_exception}")
                         await cli.invoke(
                             functions.messages.Report(
                                 peer=peer,
                                 id=[message_id_extracted],
                                 reason=types.InputReportReasonOther(),
                                 message=report_text
                             )
                         )
                     except Exception as e:
                         print(f"DEBUG group_report_scam exception in session {session}: {e}")
                         error += 1
                     else:
                         done += 1
                     finally:
                         try:
                             await cli.disconnect()
                         except Exception as ex:
                             print(f"DEBUG group_report_scam disconnect error in session {session}: {ex}")
                     spendTime = await remainTime(TS)
                     await bot.edit_message_text(chat_id, msg.id,
                    f'''♻️ عملیات ریپورت (scam)
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}
برای لغو این عملیات از دستور (/stop_{evalID}) استفاده نمایید.''')
         try:
             isWorking.remove(evalID)
         except Exception:
             pass
         spendTime = await remainTime(TS)
         await message.reply(f'''<b>♻️ عملیات ریپورت (scam) با موفقیت به پایان رسید ✅</b>
• کل ریپورت‌ها: {total_reports}
• موفق : {done}
• خطا : {error}
• زمان سپری شده : {spendTime}''')
         step = None
         db_clear_active_for_admin(chat_id)


async def main():
    await bot.start()
    bot.loop.create_task(subscription_checker())
    print("Bot started and subscription checker task scheduled.")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())