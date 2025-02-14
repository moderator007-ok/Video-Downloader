from pyrogram import Client, filters
import os
from yt_dlp import YoutubeDL
import importlib.util
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Initialize Pyrogram Client
app = Client("yt-dlp_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Command to download video
@app.on_message(filters.command("download") & filters.private)
async def download_video(client, message):
    try:
        # Extract URL from the message
        url = message.text.split(" ", 1)[1]
        chat_id = str(message.chat.id)  # Use chat ID as directory name
        logger.info(f"Received download request from chat ID: {chat_id} for URL: {url}")
        await message.reply("Downloading your video... Please wait!")
        
        # Directory specific to the user (based on chat ID)
        output_dir = os.path.join("downloads", chat_id)
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        
        # Check if pycryptodomex is available
        crypto_installed = importlib.util.find_spec("Cryptodome") is not None
        logger.info(f"Pycryptodomex installed: {crypto_installed}")

        # YoutubeDL options
        ydl_opts = {
            "format": "best",
            "outtmpl": output_template,
            "restrictfilenames": True,
            "nocheckcertificate": True,
            "extractor-args": "generic:impersonate",
            "hls_use_mpegts": True if crypto_installed else False,
        }
        
        # Progress bar for downloading
        class DownloadProgressHook:
            def __init__(self):
                self.pbar = None

            def __call__(self, d):
                if d['status'] == 'downloading':
                    if self.pbar is None and 'total_bytes' in d:
                        self.pbar = tqdm(total=d['total_bytes'], unit='B', unit_scale=True)
                    if 'downloaded_bytes' in d and self.pbar is not None:
                        self.pbar.update(d['downloaded_bytes'] - self.pbar.n)
                    logger.info(f"Downloading: {d.get('filename', 'unknown')} {d.get('downloaded_bytes', 0)}/{d.get('total_bytes', 0)}")
                elif d['status'] == 'finished' and self.pbar is not None:
                    logger.info(f"Download finished: {d.get('filename', 'unknown')}")
                    self.pbar.close()
                    self.pbar = None

        # Add the progress hook to ydl_opts
        ydl_opts['progress_hooks'] = [DownloadProgressHook()]
        
        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        downloaded_files = os.listdir(output_dir)
        downloaded_files = [os.path.join(output_dir, f) for f in downloaded_files if os.path.isfile(os.path.join(output_dir, f))]
        
        # Progress bar for uploading
        for file_path in downloaded_files:
            file_size = os.path.getsize(file_path)
            logger.info(f"Uploading file: {file_path} (size: {file_size})")
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                async with client.send_document(chat_id, file_path, progress=pbar.update):
                    pass
        
        # Cleanup downloaded files
        for file_path in downloaded_files:
            os.remove(file_path)
        os.rmdir(output_dir)  # Remove user-specific directory after sending files
        logger.info(f"Cleanup completed for chat ID: {chat_id}")
    except IndexError:
        await message.reply("Please provide a valid URL. Usage: `/download <URL>`")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        await message.reply(f"An error occurred: {e}")

# Start the bot
if __name__ == "__main__":
    logger.info("Bot is running...")
    app.run()
