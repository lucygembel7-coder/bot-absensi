import json
import os
import re
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# KONFIGURASI
# ==========================================

TOKEN = "8783166826:AAGrJuT5ErFNEg_DEmFe6QtnEkgGTj3JSH8"
DATA_FILE = "data.json"

WIB = pytz.timezone('Asia/Jakarta')

members = {
    "rizzera999": "RIZZ",
    "risyaiklee": "SERA",
    "rizalhahaha": "RIZAL",
    "cibahahaha": "CIBA",
    "citraamalia06": "CITRA",
    "mhadpleasure28": "MHAD",
    "jexxxlikemagnum": "JEXY",
    "mizzylarch": "MIZY",
    "juragantempek99": "SANZ",
    "ibasyek": "IBAS"
}

authorized_users = {"lucyfermorningstr"}

lists = {}
preserved_pins = set()

# ==========================================
# FUNGSI BANTUAN
# ==========================================

def get_now_wib():
    return datetime.now(WIB)

def format_rupiah(amount):
    return f"Rp{amount:,.0f}".replace(",", ".")

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(lists, f, ensure_ascii=False, indent=4)

def load_data():
    global lists
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                lists = json.load(f)
        except:
            lists = {}

def is_authorized(user):
    if not user or not user.username:
        return False
    return user.username.lower() in authorized_users

def get_keyboard(is_admin=False):
    buttons = [
        [
            InlineKeyboardButton("✅ Sudah", callback_data="hadir"),
            InlineKeyboardButton("❌ Batal", callback_data="batal")
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🔄 Clear", callback_data="clear"),
            InlineKeyboardButton("🗑 Hapus List", callback_data="hapus")
        ])
        buttons.append([
            InlineKeyboardButton("⏰ Set Deadline", callback_data="set_deadline"),
            InlineKeyboardButton("💰 Set Denda", callback_data="set_denda")
        ])
    return InlineKeyboardMarkup(buttons)

def build_text(data):
    text = f"📋 {data['judul']}\n\n"
    text += f"📝 Keterangan:\n{data['ket']}\n\n"
    text += f"🗒 Note:\n{data['note']}\n\n"
    
    if 'deadline' in data:
        deadline_dt = datetime.fromisoformat(data['deadline'])
        if deadline_dt.tzinfo is None:
            deadline_dt = WIB.localize(deadline_dt)
        
        if deadline_dt > get_now_wib():
            text += f"⏰ Deadline: {deadline_dt.strftime('%d %b %Y %H.%M')} WIB\n"
            denda = data.get('denda_per_orang', 10000)
            mode = data.get('mode_denda', 'per_orang')
            if mode == "total":
                text += f"💰 Denda: TOTAL {format_rupiah(denda)}\n"
            else:
                text += f"💰 Denda: {format_rupiah(denda)}/orang\n"
            text += "\n"
        else:
            text += f"⏰ *DEADLINE SUDAH LEWAT!*\n\n"
    
    text += "✅ Sudah:\n"
    if data["hadir"]:
        for i, nama in enumerate(data["hadir"], 1):
            text += f"{i}. {nama}\n"
    else:
        text += "-\n"
    
    text += "\n❌ Belum:\n"
    belum = [nama for nama in members.values() if nama not in data["hadir"]]
    
    if belum:
        for i, nama in enumerate(belum, 1):
            text += f"{i}. {nama}\n"
    else:
        text += "Semua sudah absen ✅"
    
    return text

def parse_deadline(deadline_str):
    deadline_str = deadline_str.strip()
    
    pattern = r'(\d{1,2})\.(\d{2})\s+WIB\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})'
    match = re.search(pattern, deadline_str, re.IGNORECASE)
    if match:
        hour, minute, day, month_str, year = match.groups()
        month_map = {
            'JAN': 1, 'JANUARI': 1, 'FEB': 2, 'FEBRUARI': 2,
            'MAR': 3, 'MARET': 3, 'APR': 4, 'APRIL': 4,
            'MEI': 5, 'MEI': 5, 'JUN': 6, 'JUNI': 6,
            'JUL': 7, 'JULI': 7, 'AGU': 8, 'AGUSTUS': 8,
            'SEP': 9, 'SEPTEMBER': 9, 'OKT': 10, 'OKTOBER': 10,
            'NOV': 11, 'NOVEMBER': 11, 'DES': 12, 'DESEMBER': 12
        }
        month = month_map.get(month_str.upper(), 1)
        naive_dt = datetime(int(year), month, int(day), int(hour), int(minute))
        return WIB.localize(naive_dt)
    return None

def parse_denda(denda_str):
    denda_str = denda_str.lower().strip()
    mode = "per_orang"
    if "total" in denda_str:
        mode = "total"
        denda_str = denda_str.replace("total", "").strip()
    denda_str = denda_str.replace("k/orang", "k").replace("rb/orang", "rb")
    denda_str = denda_str.replace("per orang", "").replace("/orang", "")
    angka = 0
    if "k" in denda_str or "rb" in denda_str:
        denda_str = denda_str.replace("k", "").replace("rb", "")
        try:
            angka = float(denda_str) * 1000
        except:
            return None, None
    else:
        denda_str = denda_str.replace(".", "").replace(",", "")
        try:
            angka = float(denda_str)
        except:
            return None, None
    return int(angka), mode

async def send_rekap_and_denda(context, msg_id):
    if msg_id not in lists:
        return
    data = lists[msg_id]
    belum_nama = [nama for nama in members.values() if nama not in data["hadir"]]
    if not belum_nama:
        await context.bot.send_message(
            chat_id=data['chat_id'],
            text=f"🎉 *SELAMAT!* 🎉\n\n📋 {data['judul']}\n✅ Semua anggota sudah absen tepat waktu!",
            parse_mode='Markdown'
        )
        return
    denda_per_orang = data.get('denda_per_orang', 10000)
    mode_denda = data.get('mode_denda', 'per_orang')
    if mode_denda == "total" and len(belum_nama) > 0:
        denda_per_orang = denda_per_orang // len(belum_nama)
    total_denda = denda_per_orang * len(belum_nama)
    belum_with_mention = []
    for nama in belum_nama:
        username = None
        for uname, n in members.items():
            if n == nama:
                username = uname
                break
        mention = f"@{username}" if username else nama
        belum_with_mention.append((nama, mention))
    text = f"⚠️ *PERINGATAN ABSENSI* ⚠️\n\n"
    text += f"📋 {data['judul']}\n\n"
    text += f"⏰ Waktu terakhir: {data.get('deadline_str', 'Tidak ditentukan')}\n\n"
    text += f"❌ *YANG BELUM ABSEN:*\n"
    for i, (nama, mention) in enumerate(belum_with_mention, 1):
        text += f"{i}. {mention} → *DENDA {format_rupiah(denda_per_orang)}* 💸\n"
    text += f"\n❗ Total: {len(belum_nama)} orang\n"
    text += f"💰 Total denda: *{format_rupiah(total_denda)}*\n\n"
    text += f"📌 Segera lunasi denda ke bendahara!"
    await context.bot.send_message(chat_id=data['chat_id'], text=text, parse_mode='Markdown')
    lists[msg_id]['rekap_sent'] = True
    save_data()

async def check_deadlines_periodic(context):
    now_wib = get_now_wib()
    for msg_id, data in lists.items():
        if 'deadline' in data:
            deadline_dt = datetime.fromisoformat(data['deadline'])
            if deadline_dt.tzinfo is None:
                deadline_dt = WIB.localize(deadline_dt)
            if deadline_dt <= now_wib and not data.get('rekap_sent', False):
                await send_rekap_and_denda(context, msg_id)

async def recreate_message(query, context, data, old_message_id, is_admin):
    new_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=build_text(data),
        reply_markup=get_keyboard(is_admin)
    )
    lists[str(new_msg.message_id)] = {"chat_id": query.message.chat_id, **data}
    if str(old_message_id) in lists:
        old_data = lists[str(old_message_id)]
        if 'deadline' in old_data:
            lists[str(new_msg.message_id)]['deadline'] = old_data['deadline']
            lists[str(new_msg.message_id)]['deadline_str'] = old_data['deadline_str']
        if 'denda_per_orang' in old_data:
            lists[str(new_msg.message_id)]['denda_per_orang'] = old_data['denda_per_orang']
        if 'mode_denda' in old_data:
            lists[str(new_msg.message_id)]['mode_denda'] = old_data['mode_denda']
        del lists[str(old_message_id)]
    save_data()
    try:
        await context.bot.delete_message(query.message.chat_id, old_message_id)
    except:
        pass

def load_admins_from_file():
    global authorized_users
    if os.path.exists("authorized_users.txt"):
        try:
            with open("authorized_users.txt", "r") as f:
                users = {line.strip().lower() for line in f if line.strip()}
                if users:
                    authorized_users.update(users)
        except:
            pass

# ==========================================
# COMMAND HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = is_authorized(user)
    status_admin = "✅ Admin" if is_admin else "❌ User Biasa"
    await update.message.reply_text(
        f"🤖 *Bot Absensi Aktif*\n\n"
        f"👋 Halo @{user.username}! {status_admin}\n\n"
        f"📌 Ketik `/help` untuk melihat semua fitur.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = is_authorized(update.effective_user)
    help_text = f"""
🤖 *BOT ABSENSI & DENDA*
━━━━━━━━━━━━━━━━━━━━━

📌 *PERINTAH DASAR*
• `/start` - Mulai bot
• `/help` - Bantuan ini

━━━━━━━━━━━━━━━━━━━━━

📋 *MEMBUAT ABSENSI*
`/createlist JUDUL | KET | NOTE`

Contoh: `/createlist PIK 1 JUN | S1 | MABAR`

━━━━━━━━━━━━━━━━━━━━━

✅ *CARA ABSEN*
• Tekan **✅ Sudah** untuk absen
• Tekan **❌ Batal** untuk membatalkan absen

━━━━━━━━━━━━━━━━━━━━━

⏰ *SET DEADLINE* {'(Admin Only)' if not is_admin else '✅ Kamu Admin'}
`/setdeadline WAKTU` (reply ke list)

Format: `22.00 WIB 1 JUN 2026`

━━━━━━━━━━━━━━━━━━━━━

💰 *SET DENDA* {'(Admin Only)' if not is_admin else '✅ Kamu Admin'}
`/denda NILAI` (reply ke list)

Contoh: `/denda 25k` atau `/denda total 100k`

━━━━━━━━━━━━━━━━━━━━━

📊 *INFORMASI*
• `/deadline` - Lihat deadline aktif
• `/forcerekap` - Kirim rekap manual

━━━━━━━━━━━━━━━━━━━━━

👑 *MANAJEMEN ADMIN* {'(Admin Only)' if not is_admin else '✅ Kamu Admin'}
• `/addadmin USERNAME` - Tambah admin
• `/deladmin USERNAME` - Hapus admin
• `/listadmin` - Lihat daftar admin
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def createlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /createlist PIK 1 JUN | S1 | MABAR")
        return
    raw = " ".join(context.args)
    parts = raw.split("|")
    judul = parts[0].strip() if len(parts) > 0 else "-"
    ket = parts[1].strip() if len(parts) > 1 else "-"
    note = parts[2].strip() if len(parts) > 2 else "-"
    data = {"judul": judul, "ket": ket, "note": note, "hadir": [], "chat_id": update.effective_chat.id}
    is_admin = is_authorized(update.effective_user)
    msg = await update.message.reply_text(build_text(data), reply_markup=get_keyboard(is_admin))
    try:
        await context.bot.pin_chat_message(msg.chat_id, msg.message_id, disable_notification=True)
    except:
        pass
    lists[str(msg.message_id)] = {"chat_id": msg.chat_id, **data}
    save_data()

async def set_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply ke pesan list, lalu ketik: /setdeadline 22.00 WIB 1 JUN 2026")
        return
    reply_msg_id = str(update.message.reply_to_message.message_id)
    if reply_msg_id not in lists:
        await update.message.reply_text("❌ Bukan list absensi!")
        return
    if not is_authorized(update.effective_user):
        await update.message.reply_text("❌ Hanya admin!")
        return
    deadline_str = " ".join(context.args)
    deadline_dt = parse_deadline(deadline_str)
    if not deadline_dt:
        await update.message.reply_text("❌ Format waktu salah! Contoh: 22.00 WIB 1 JUN 2026")
        return
    lists[reply_msg_id]['deadline'] = deadline_dt.isoformat()
    lists[reply_msg_id]['deadline_str'] = deadline_str
    lists[reply_msg_id]['denda_per_orang'] = 10000
    lists[reply_msg_id]['mode_denda'] = 'per_orang'
    lists[reply_msg_id]['rekap_sent'] = False
    save_data()
    await update.message.reply_text(f"✅ Deadline: {deadline_dt.strftime('%d %b %Y %H.%M')} WIB\n💸 Denda default: Rp10.000/orang")

async def set_denda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply ke pesan list, lalu ketik: /denda 25k")
        return
    reply_msg_id = str(update.message.reply_to_message.message_id)
    if reply_msg_id not in lists or 'deadline' not in lists[reply_msg_id]:
        await update.message.reply_text("❌ Atur deadline dulu!")
        return
    if not is_authorized(update.effective_user):
        await update.message.reply_text("❌ Hanya admin!")
        return
    denda_str = " ".join(context.args)
    denda_value, mode = parse_denda(denda_str)
    if denda_value is None:
        await update.message.reply_text("❌ Format salah! Contoh: /denda 25k atau /denda total 100k")
        return
    lists[reply_msg_id]['denda_per_orang'] = denda_value
    lists[reply_msg_id]['mode_denda'] = mode
    save_data()
    await update.message.reply_text(f"✅ Denda: {format_rupiah(denda_value)}/{'TOTAL' if mode == 'total' else 'orang'}")

async def view_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = []
    now_wib = get_now_wib()
    for msg_id, data in lists.items():
        if 'deadline' in data:
            dt = datetime.fromisoformat(data['deadline'])
            if dt.tzinfo is None:
                dt = WIB.localize(dt)
            if dt > now_wib:
                sisa = dt - now_wib
                jam = int(sisa.total_seconds() // 3600)
                menit = int((sisa.total_seconds() % 3600) // 60)
                active.append((data['judul'], dt, jam, menit))
    if not active:
        await update.message.reply_text("📭 Tidak ada deadline aktif saat ini.")
        return
    text = "⏰ *Deadline Aktif:*\n\n"
    for judul, dt, jam, menit in active:
        text += f"📋 {judul}\n"
        text += f"   ⏰ {dt.strftime('%d %b %Y %H.%M')} WIB\n"
        text += f"   ⏳ Sisa: {jam} jam {menit} menit\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def force_rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply ke pesan list!")
        return
    reply_msg_id = str(update.message.reply_to_message.message_id)
    if reply_msg_id not in lists:
        await update.message.reply_text("❌ Bukan list absensi!")
        return
    if not is_authorized(update.effective_user):
        await update.message.reply_text("❌ Hanya admin!")
        return
    await update.message.reply_text("📤 Mengirim rekap...")
    await send_rekap_and_denda(context, reply_msg_id)

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user):
        await update.message.reply_text("❌ Bukan admin!")
        return
    if not context.args:
        await update.message.reply_text("Contoh: /addadmin username")
        return
    new_admin = context.args[0].lower()
    if new_admin in authorized_users:
        await update.message.reply_text(f"⚠️ {new_admin} sudah admin!")
        return
    authorized_users.add(new_admin)
    with open("authorized_users.txt", "w") as f:
        for u in authorized_users:
            f.write(f"{u}\n")
    await update.message.reply_text(f"✅ @{new_admin} jadi admin!")

async def deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user):
        await update.message.reply_text("❌ Bukan admin!")
        return
    if not context.args:
        await update.message.reply_text("Contoh: /deladmin username")
        return
    admin_to_remove = context.args[0].lower()
    if admin_to_remove == "--self":
        username = update.effective_user.username.lower()
        if username in authorized_users:
            authorized_users.remove(username)
            with open("authorized_users.txt", "w") as f:
                for u in authorized_users:
                    f.write(f"{u}\n")
            await update.message.reply_text(f"✅ @{username} dihapus dari admin!")
        return
    if admin_to_remove not in authorized_users:
        await update.message.reply_text("❌ Admin tidak ditemukan!")
        return
    if admin_to_remove == update.effective_user.username.lower():
        await update.message.reply_text("⚠️ Gunakan /deladmin --self untuk hapus diri sendiri")
        return
    authorized_users.remove(admin_to_remove)
    with open("authorized_users.txt", "w") as f:
        for u in authorized_users:
            f.write(f"{u}\n")
    await update.message.reply_text(f"✅ @{admin_to_remove} dihapus dari admin!")

async def listadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized_users:
        await update.message.reply_text("📋 Belum ada admin.")
        return
    text = "👑 *Daftar Admin:*\n\n" + "\n".join([f"• @{a}" for a in authorized_users])
    await update.message.reply_text(text, parse_mode='Markdown')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_id = str(query.message.message_id)
    if msg_id not in lists:
        await query.answer("❌ List sudah tidak aktif", show_alert=True)
        return
    data = lists[msg_id]
    user_is_admin = is_authorized(query.from_user)
    username = query.from_user.username.lower() if query.from_user.username else None
    if query.data == "hadir":
        if not username or username not in members:
            await query.answer("❌ Tidak terdaftar!", show_alert=True)
            return
        nama = members[username]
        if nama in data["hadir"]:
            await query.answer("✅ Kamu sudah absen!", show_alert=True)
            return
        data["hadir"].append(nama)
        await recreate_message(query, context, data, int(msg_id), user_is_admin)
    elif query.data == "batal":
        if not username or username not in members:
            await query.answer("❌ Tidak terdaftar!", show_alert=True)
            return
        nama = members[username]
        if nama not in data["hadir"]:
            await query.answer("❌ Kamu belum absen!", show_alert=True)
            return
        data["hadir"].remove(nama)
        await recreate_message(query, context, data, int(msg_id), user_is_admin)
        await query.answer("✅ Absen dibatalkan!")
    elif query.data == "clear":
        if not user_is_admin:
            await query.answer("❌ Hanya admin!", show_alert=True)
            return
        data["hadir"] = []
        await recreate_message(query, context, data, int(msg_id), user_is_admin)
    elif query.data == "hapus":
        if not user_is_admin:
            await query.answer("❌ Hanya admin!", show_alert=True)
            return
        if msg_id in lists:
            del lists[msg_id]
        save_data()
        try:
            await query.message.delete()
        except:
            pass
    elif query.data == "set_deadline":
        if not user_is_admin:
            await query.answer("❌ Hanya admin!", show_alert=True)
            return
        await query.answer("Kirim: /setdeadline 22.00 WIB 1 JUN 2026", show_alert=True)
    elif query.data == "set_denda":
        if not user_is_admin:
            await query.answer("❌ Hanya admin!", show_alert=True)
            return
        await query.answer("Kirim: /denda 25k", show_alert=True)

# ==========================================
# MAIN
# ==========================================

def main():
    load_data()
    load_admins_from_file()
    
    app = Application.builder().token(TOKEN).build()
    
    if app.job_queue:
        app.job_queue.run_repeating(check_deadlines_periodic, interval=60, first=10)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("createlist", createlist))
    app.add_handler(CommandHandler("setdeadline", set_deadline))
    app.add_handler(CommandHandler("denda", set_denda))
    app.add_handler(CommandHandler("deadline", view_deadline))
    app.add_handler(CommandHandler("forcerekap", force_rekap))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("deladmin", deladmin))
    app.add_handler(CommandHandler("listadmin", listadmin))
    app.add_handler(CallbackQueryHandler(button))
    
    print("=" * 50)
    print("✅ BOT ABSENSI AKTIF!")
    print(f"📋 Daftar Admin: {', '.join(authorized_users) if authorized_users else 'Belum ada'}")
    print(f"🕐 Waktu server: {get_now_wib().strftime('%H:%M:%S WIB, %d %b %Y')}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
