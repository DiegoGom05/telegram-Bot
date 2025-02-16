 

import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
  
# Token del bot
TOKEN  = 'REMOVED'
BOT_USERNAME  = '@webCraft456bot'

# Clave de API de Imgur (obtener de https://api.imgur.com/oauth2/addclient)
IMGUR_CLIENT_ID = "REMOVED"
 
# Estado del usuario para guardar datos
user_data = {}

# Configura tus credenciales de Imgur y Telegram
 

def upload_to_imgur(image_path):
    url = "https://api.imgur.com/3/upload"
    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(url, headers=headers, files={"image": image_file})
        response.raise_for_status()
        return response.json()["data"]["link"]
    except requests.exceptions.RequestException as e:
        print(f"Error uploading to Imgur: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Type /create to start creating your website.")

async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    user_data[user_id] = {}
    await update.message.reply_text("Let's start: What will be the title?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    text = update.message.text.lower()

    if user_id not in user_data:
        await update.message.reply_text("First use /create to start.")
        return

    if "title" not in user_data[user_id]:
        user_data[user_id]["title"] = text
        await update.message.reply_text("Title saved! Now, write a description for the page.")
        return

    if "description" not in user_data[user_id]:
        user_data[user_id]["description"] = text
        await update.message.reply_text("Description saved! Now, send your logo image (or type 'skip' to skip this step).")
        return

    if "logo" not in user_data[user_id]:
        if text == "skip":
            user_data[user_id]["logo"] = None  # Skip logo step
            await update.message.reply_text("Logo skipped! Now, send a related image (or type 'skip' to skip this step).")
        else:
            await update.message.reply_text("Please send a valid logo image (or type 'skip' to skip).")
        return

    if "related_image" not in user_data[user_id]:
        if text == "skip":
            user_data[user_id]["related_image"] = None  # Skip related image step
            await update.message.reply_text("Related image skipped! Now, send your Twitter/X link.")
        else:
            await update.message.reply_text("Please send a related image (or type 'skip' to skip).")
        return

    if "x_link" not in user_data[user_id]:
        if text.startswith("http"):
            user_data[user_id]["x_link"] = text
            await update.message.reply_text("Now, send your Telegram link:")
        else:
            await update.message.reply_text("Please send a valid Twitter/X link.")
        return

    if "telegram_link" not in user_data[user_id]:
        if text.startswith("http"):
            user_data[user_id]["telegram_link"] = text
            await generate_html(update, user_id)
        else:
            await update.message.reply_text("Please send a valid Telegram link.")
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"{user_id}_image.jpg"
    await file.download_to_drive(file_path)

    imgur_url = upload_to_imgur(file_path)
    os.remove(file_path)

    if not imgur_url:
        await update.message.reply_text("Failed to upload image. Try again.")
        return

    if "logo" not in user_data[user_id]:
        user_data[user_id]["logo"] = imgur_url
        await update.message.reply_text("Logo saved! Now, send a related image.")
    elif "related_image" not in user_data[user_id]:
        user_data[user_id]["related_image"] = imgur_url
        await update.message.reply_text("Image saved! Now, send your Twitter/X link.")

async def generate_html(update: Update, user_id: int):
    title = user_data[user_id]["title"]
    description = user_data[user_id]["description"]
    logo = user_data[user_id]["logo"] if user_data[user_id].get("logo") else "default_logo_url"
    related_image = user_data[user_id]["related_image"] if user_data[user_id].get("related_image") else "default_related_image_url"
    x_link = user_data[user_id]["x_link"]
    telegram_link = user_data[user_id]["telegram_link"]

    # Lee el archivo template.html
    try:
        with open("template.html", "r", encoding="utf-8") as template_file:
            template_content = template_file.read()

        # Reemplaza los marcadores de posición con los datos del usuario
        html_content = template_content.replace("{{title}}", title) \
                                       .replace("{{description}}", description) \
                                       .replace("{{logo}}", logo) \
                                       .replace("{{related_image}}", related_image) \
                                       .replace("{{x_link}}", x_link) \
                                       .replace("{{telegram_link}}", telegram_link)

        # Guarda el archivo HTML final
        file_name = f"{user_id}_page.html"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(html_content)

        # Envía el archivo HTML generado
        await update.message.reply_document(document=open(file_name, "rb"))
        await update.message.reply_text("Here is your HTML page!")

        # Limpieza del archivo y datos del usuario
        os.remove(file_name)
        user_data.pop(user_id)
    
    except Exception as e:
        await update.message.reply_text(f"Error generating HTML: {str(e)}")

def main():
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('create', create_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot is running...")
    app.run_polling(poll_interval=3)

if __name__ == '__main__':
    main()