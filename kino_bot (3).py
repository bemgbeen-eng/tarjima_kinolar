import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ===================== SOZLAMALAR =====================
TOKEN = "BU_YERGA_TOKENINGIZNI_QOYING"
ADMIN_ID = 123456789  # @userinfobot dan o'z ID'ingizni oling
DB_FILE = "kinolar.json"
# ======================================================

logging.basicConfig(level=logging.INFO)

# ───────── Ma'lumotlar bazasi (JSON fayl) ─────────

def db_yukla():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def db_saqla(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────── /start ─────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Kino Botga Xush Kelibsiz!*\n\n"
        "🔍 Kino nomini yozing — men topib beraman!\n\n"
        "Misol: `Titanic` yoki `O'g'ri`",
        parse_mode="Markdown"
    )

# ───────── Kino qidirish ─────────

async def qidir(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sorov = update.message.text.strip().lower()
    kinolar = db_yukla()

    topildi = [
        (nom, info) for nom, info in kinolar.items()
        if sorov in nom.lower()
    ]

    if not topildi:
        await update.message.reply_text(
            "❌ Kino topilmadi!\n\n"
            "🔍 Boshqa nom bilan urinib ko'ring.\n"
            "📝 To'g'ri yozganingizni tekshiring."
        )
        return

    if len(topildi) == 1:
        nom, info = topildi[0]
        await update.message.reply_video(
            video=info["file_id"],
            caption=f"🎬 *{nom}*\n\n{info.get('tavsif', '')}",
            parse_mode="Markdown"
        )
    else:
        # Bir nechta kino topilsa — tugmalar ko'rsat
        tugmalar = [
            [InlineKeyboardButton(nom, callback_data=f"kino:{nom}")]
            for nom, _ in topildi[:10]
        ]
        markup = InlineKeyboardMarkup(tugmalar)
        await update.message.reply_text(
            f"🎬 *{len(topildi)} ta kino topildi:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )

# ───────── Tugma bosilganda ─────────

async def tugma(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    nom = query.data.replace("kino:", "")
    kinolar = db_yukla()

    if nom in kinolar:
        info = kinolar[nom]
        await query.message.reply_video(
            video=info["file_id"],
            caption=f"🎬 *{nom}*\n\n{info.get('tavsif', '')}",
            parse_mode="Markdown"
        )

# ───────── Admin: kino qo'shish ─────────
# Ishlatish:
# 1. Kanalga video yuklang
# 2. Botga forward qiling
# 3. Bot "Qaysi nom?" deydi
# 4. Nomini yozing → saqlandi!

async def forward_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return  # Faqat admin

    video = update.message.video or update.message.document
    if not video:
        return

    ctx.user_data["yangi_file_id"] = video.file_id
    await update.message.reply_text(
        "✅ Video qabul qilindi!\n\n"
        "📝 Kino nomini yozing (masalan: Titanic 1997):"
    )
    ctx.user_data["holat"] = "nom_kutish"

async def nom_saqlash(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    if ctx.user_data.get("holat") != "nom_kutish":
        return

    nom = update.message.text.strip()
    file_id = ctx.user_data.get("yangi_file_id")

    if not file_id:
        await update.message.reply_text("❌ Avval video yuboring!")
        return

    kinolar = db_yukla()
    kinolar[nom] = {
        "file_id": file_id,
        "tavsif": ""
    }
    db_saqla(kinolar)

    ctx.user_data["holat"] = None
    ctx.user_data["yangi_file_id"] = None

    await update.message.reply_text(
        f"✅ *{nom}* muvaffaqiyatli qo'shildi!\n\n"
        f"📊 Jami kinolar: {len(kinolar)} ta",
        parse_mode="Markdown"
    )

# ───────── /kinolar - admin uchun ro'yxat ─────────

async def kinolar_royxat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    kinolar = db_yukla()
    if not kinolar:
        await update.message.reply_text("📭 Hozircha kino yo'q.")
        return

    matn = "🎬 *Barcha kinolar:*\n\n"
    for i, nom in enumerate(kinolar.keys(), 1):
        matn += f"{i}. {nom}\n"

    await update.message.reply_text(matn, parse_mode="Markdown")

# ───────── /ochir - kino o'chirish ─────────

async def ochir(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    args = ctx.args
    if not args:
        await update.message.reply_text("❌ Ishlatish: /ochir Kino nomi")
        return

    nom = " ".join(args)
    kinolar = db_yukla()

    if nom in kinolar:
        del kinolar[nom]
        db_saqla(kinolar)
        await update.message.reply_text(f"✅ *{nom}* o'chirildi.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ *{nom}* topilmadi.", parse_mode="Markdown")

# ───────── Asosiy ─────────

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kinolar", kinolar_royxat))
    app.add_handler(CommandHandler("ochir", ochir))
    app.add_handler(CallbackQueryHandler(tugma, pattern="^kino:"))

    # Admin: video forward qilganda
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.VIDEO, forward_video
    ))

    # Admin: nom yozganda YOKI foydalanuvchi qidirish
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda u, c: nom_saqlash(u, c) if u.message.from_user.id == ADMIN_ID 
                     and c.user_data.get("holat") == "nom_kutish" 
                     else qidir(u, c)
    ))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
