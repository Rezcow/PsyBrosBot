
import os
import subprocess
import asyncio
import re
import httpx
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8194406693:AAHgUSR31UV7qrUCZZOhbAJibi2XrxYmads"
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def extraer_url(text: str) -> str:
    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else None

def contiene_enlace_valido(text: str) -> bool:
    return extraer_url(text) is not None

def limpiar_url_soundcloud(url: str) -> str:
    return re.sub(r"\?.*", "", url)

async def manejar_eliminacion_segura(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error al eliminar {path}: {e}")

async def obtener_teclado_odesli(original_url: str):
    api_url = f"https://api.song.link/v1-alpha.1/links?url={original_url}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=10)
            if response.status_code != 200:
                return None
            data = response.json()
            links = data.get("linksByPlatform", {})

            botones, fila = [], []
            for i, (nombre, info) in enumerate(links.items()):
                url = info.get("url")
                if url:
                    fila.append(InlineKeyboardButton(text=nombre.capitalize(), url=url))
                    if len(fila) == 3:
                        botones.append(fila)
                        fila = []
            if fila:
                botones.append(fila)
            return InlineKeyboardMarkup(botones)
    except Exception as e:
        print(f"Odesli error: {e}")
        return None

async def buscar_y_descargar(query: str, chat_id, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DOWNLOADS_DIR, f"{query}.mp3")
    try:
        subprocess.run(["yt-dlp", f"ytsearch1:{query}", "--extract-audio", "--audio-format", "mp3", "-o", filename], check=True)
        with open(filename, 'rb') as audio_file:
            await context.bot.send_audio(chat_id=chat_id, audio=audio_file, title=query)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ No se pudo descargar: {query}")
    finally:
        await manejar_eliminacion_segura(filename)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if not contiene_enlace_valido(text):
        return

    url = extraer_url(text)
    await update.message.reply_text("🔎 Procesando...")

    # Botones equivalentes
    teclado = await obtener_teclado_odesli(url)
    if teclado:
        await update.message.reply_text("🎶 Disponible en:", reply_markup=teclado)

    if "spotify.com/track" in url:
        try:
            await update.message.reply_text("🎧 Buscandoando...")
            result = subprocess.run(["yt-dlp", "-j", url], capture_output=True, text=True)
            data = json.loads(result.stdout)
            title = data.get("title")
            if title:
                await buscar_y_descargar(title, chat_id, context)
            else:
                await update.message.reply_text("❌ No se pudo.")
        except Exception as e:
            await update.message.reply_text(f"❌ No se pudo procesar URL Spotify.
{str(e)}")

    elif "youtu" in url:
        filename = os.path.join(DOWNLOADS_DIR, "youtube.mp4")
        try:
            subprocess.run(["yt-dlp", "-f", "mp4", "-o", filename, url], check=True)
            with open(filename, 'rb') as f:
                await context.bot.send_video(chat_id=chat_id, video=f)
        except Exception as e:
            await update.message.reply_text(f"❌ YouTube error: {e}")
        finally:
            await manejar_eliminacion_segura(filename)

    elif "soundcloud.com" in url:
        try:
            subprocess.run(["scdl", "-l", limpiar_url_soundcloud(url), "-o", DOWNLOADS_DIR, "-f", "--onlymp3"], check=True)
            for file in os.listdir(DOWNLOADS_DIR):
                if file.endswith(".mp3"):
                    path = os.path.join(DOWNLOADS_DIR, file)
                    with open(path, 'rb') as audio_file:
                        await context.bot.send_audio(chat_id=chat_id, audio=audio_file)
                    await manejar_eliminacion_segura(path)
        except Exception as e:
            await update.message.reply_text(f"❌ SoundCloud error: {e}")

    elif "instagram.com" in url:
        filename = os.path.join(DOWNLOADS_DIR, "insta.mp4")
        try:
            subprocess.run(["yt-dlp", "-f", "mp4", "-o", filename, url], check=True)
            with open(filename, 'rb') as f:
                await context.bot.send_video(chat_id=chat_id, video=f)
        except Exception as e:
            await update.message.reply_text(f"❌ Instagram error: {e}")
        finally:
            await manejar_eliminacion_segura(filename)

    elif "twitter.com" in url or "x.com" in url:
        filename = os.path.join(DOWNLOADS_DIR, "x.mp4")
        try:
            subprocess.run(["yt-dlp", "-f", "mp4", "-o", filename, url], check=True)
            with open(filename, 'rb') as f:
                await context.bot.send_video(chat_id=chat_id, video=f)
        except Exception as e:
            await update.message.reply_text(f"❌ Twitter error: {e}")
        finally:
            await manejar_eliminacion_segura(filename)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot listo. Esperando mensajes...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot detenido.")
