 

import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
 
import re
from git import Repo

from dotenv import load_dotenv
import os

load_dotenv()

# Obtener secretos desde variables de entorno
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")
SITE_ID = os.getenv("SITE_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
TOKEN = os.getenv("TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

# Estado del usuario para guardar datos
user_data = {}

def upload_to_netlify(file_path, title):
    url = "https://api.netlify.com/api/v1/sites"
    headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Crear un nuevo sitio si no tienes uno
        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()  # Lanza una excepción si la solicitud falla
        site_info = response.json()  # Intenta analizar la respuesta como JSON
        site_id = site_info["site_id"]

        # Formatear el título para usar en la URL
        formatted_title = re.sub(r'[^a-zA-Z0-9]', '-', title.lower())

        # Subir archivo HTML
        deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        with open(file_path, "rb") as file:
            files = {'file': file}
            response = requests.post(deploy_url, headers=headers, files=files)
            response.raise_for_status()  # Lanza una excepción si la solicitud falla

        if response.status_code == 200:
            return f"Page uploaded! URL: {site_info['url']}/{formatted_title}"
        else:
            return f"Upload failed: {response.text}"

    except requests.exceptions.RequestException as e:
        return f"Error uploading to Netlify: {str(e)}"
    except ValueError as e:
        return f"Invalid JSON response from Netlify: {str(e)}"
    
    
# Crear una nueva rama en el repositorio de GitHub y hacer el push
def create_new_branch_and_push(file_name, title):
    # Clonamos el repositorio
    repo_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
    repo_dir = f"/tmp/{REPO_NAME}"
    
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)
    
    repo = Repo.clone_from(repo_url, repo_dir)

    # Formateamos el nombre de la rama basado en el título
    branch_name = re.sub(r'[^a-zA-Z0-9]', '-', title.lower())  # Asegura que el nombre sea válido
    new_branch = repo.create_head(branch_name)

    # Cambiar a la nueva rama
    new_branch.checkout()

    # Copiar el archivo HTML generado al repositorio
    html_file_path = os.path.join(repo_dir, file_name)
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write("Aquí va el contenido HTML generado")  # El contenido será reemplazado más adelante

    # Agregar y hacer commit de los cambios
    repo.git.add(html_file_path)
    repo.index.commit(f"Add new HTML page: {title}")

    # Empujar los cambios a la nueva rama
    origin = repo.remote(name='origin')
    origin.push(branch_name)

    return f"File pushed to the new branch: {branch_name}"

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

        # Subir el archivo a Netlify
        netlify_url = upload_to_netlify(file_name, title)  # Pasa el argumento 'title'
        if "Error" in netlify_url or "failed" in netlify_url:
            raise Exception(netlify_url)

        # Crear una nueva branch y subir el archivo al repositorio de GitHub
        github_message = create_new_branch_and_push(file_name, title)

        # Envía el mensaje con la URL de Netlify
        await update.message.reply_text(f"HTML generated! Here is the Netlify URL: {netlify_url}")
        await update.message.reply_text(github_message)

        # Limpieza de archivos
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