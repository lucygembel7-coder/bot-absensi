import json
import os
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8783166826:AAGrJuT5ErFNEg_DEmFe6QtnEkgGTj3JSH8"
DATA_FILE = "data.json"
WIB = pytz.timezone('Asia/Jakarta')

members = {
    "rizzera999": "RIZZ", "risyaiklee": "SERA", "rizalhahaha": "RIZAL",
    "cibahahaha": "CIBA", "citraamalia06": "CITRA", "mhadpleasure28": "MHAD",
    "jexxxlikemagnum": "JEXY", "mizzylarch": "MIZY", "juragantempek99": "SANZ", "ibasyek": "IBAS"
}
authorized_users = {"lucyfermorningstr"}
lists = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(lists, f)

def load_data():
    global lists
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                lists = json.load(f)
        except:
            lists = {}

def is_authorized(user):
    if not user or not user.username:
        return False
    return user.username.lower() in authorized_users

def get_keyboard(is_admin=False):
    buttons = [[
        InlineKeyboardButton("✅ Sudah", callback_data="hadir"),
        InlineKeyboardButton("❌ Batal", callback_data="batal")
    ]]
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🔄 Clear", callback_data="clear"),
            InlineKeyboardButton("🗑 Hapus", callback_data="hapus")
        ])
    return InlineKeyboardMarkup(buttons)

def build_text(data):
    text = f"📋 {data['judul']}\n\n📝 {data['ket']}\n\n🗒 {data['note']}\n\n✅ Sudah:\n"
    for nama in data['hadir']:
        text += f"• {nama}\n"
    text += "\n❌ Belum:\n"
    for nama in members.values():
        if nama not in data['hadir']:
            text += f"• {nama}\n"
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Absensi Aktif!\nKetik /help")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""📋 BOT ABSENSI

/createlist JUDUL | KET | NOTE - Buat list
/addadmin username - Tambah admin
/deladmin username - Hapus admin
/listadmin - Lihat admin

✅ Tekan tombol untuk absen/batal""")

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
    lists[str(msg.message_id)] = data
    save_data()

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_id = str(query.message.message_id)
    if msg_id not in lists:
        await query.answer("List tidak aktif", show_alert=True)
        return
    data = lists[msg_id]
    user_is_admin = is_authorized(query.from_user)
    username = query.from_user.username.lower() if query.from_user.username else None
    if query.data == "hadir":
        if not username or username not in members:
            await query.answer("Tidak terdaftar!", show_alert=True)
            return
        nama = members[username]
        if nama not in data["hadir"]:
            data["hadir"].append(nama)
            save_data()
        await query.edit_message_text(build_text(data), reply_markup=get_keyboard(user_is_admin))
    elif query.data == "batal":
        if not username or username not in members:
            await query.answer("Tidak terdaftar!", show_alert=True)
            return
        nama = members[username]
        if nama in data["hadir"]:
            data["hadir"].remove(nama)
            save_data()
        await query.edit_message_text(build_text(data), reply_markup=get_keyboard(user_is_admin))
    elif query.data == "clear" and user_is_admin:
        data["hadir"] = []
        save_data()
        await query.edit_message_text(build_text(data), reply_markup=get_keyboard(user_is_admin))
    elif query.data == "hapus" and user_is_admin:
        del lists[msg_id]
        save_data()
        await query.message.delete()

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user):
        await update.message.reply_text("Bukan admin!")
        return
    if not context.args:
        await update.message.reply_text("Contoh: /addadmin username")
        return
    new_admin = context.args[0].lower()
    authorized_users.add(new_admin)
    with open("authorized_users.txt", "w") as f:
        for u in authorized_users:
            f.write(f"{u}\n")
    await update.message.reply_text(f"✅ @{new_admin} jadi admin!")

async def deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user):
        await update.message.reply_text("Bukan admin!")
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
        await update.message.reply_text("Admin tidak ditemukan!")
        return
    authorized_users.remove(admin_to_remove)
    with open("authorized_users.txt", "w") as f:
        for u in authorized_users:
            f.write(f"{u}\n")
    await update.message.reply_text(f"✅ @{admin_to_remove} dihapus dari admin!")

async def listadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized_users:
        await update.message.reply_text("Belum ada admin.")
        return
    text = "👑 Admin:\n" + "\n".join([f"• @{a}" for a in authorized_users])
    await update.message.reply_text(text)

def load_admins():
    global authorized_users
    if os.path.exists("authorized_users.txt"):
        try:
            with open("authorized_users.txt", "r") as f:
                users = {line.strip().lower() for line in f if line.strip()}
                if users:
                    authorized_users.update(users)
        except:
            pass

def main():
    load_data()
    load_admins()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("createlist", createlist))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("deladmin", deladmin))
    app.add_handler(CommandHandler("listadmin", listadmin))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Bot Aktif di Railway!")
    app.run_polling()

if __name__ == "__main__":
    main()
