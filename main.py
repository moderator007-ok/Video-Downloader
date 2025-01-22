from pyrogram import Client, filters
import os
from yt_dlp import YoutubeDL
import asyncio

# Bot credentials
BOT_TOKEN = ""
API_ID = 29754529
API_HASH = "dd54732e78650479ac4fb0e173fe4759"

# Initialize Pyrogram Client
app = Client("yt-dlp_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

async def download_progress_hook(d, progress_message):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes', d.get('total_bytes_estimate', 0))
        downloaded_bytes = d.get('downloaded_bytes', 0)
        percentage = downloaded_bytes / total_bytes * 100 if total_bytes else 0
        await progress_message.edit_text(f"Downloading: {percentage:.2f}%")

async def upload_progress(current, total, progress_message):
    percentage = current / total * 100
    await progress_message.edit_text(f"Uploading: {percentage:.2f}%")

# Command to download video
@app.on_message(filters.command("download") & filters.private)
async def download_video(client, message):
    try:
        # Extract URL from the message
        url = message.text.split(" ", 1)[1]
        chat_id = str(message.chat.id)  # Use chat ID as directory name
        progress_message = await message.reply("Downloading your video... Please wait!")
        
        # Directory specific to the user (based on chat ID)
        output_dir = os.path.join("downloads", chat_id)
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        
        # YoutubeDL options
        ydl_opts = {
            "format": "best",
            "outtmpl": output_template,
            "restrictfilenames": True,
            "nocheckcertificate": True,
            "extractor-args": "generic:impersonate",
            "progress_hooks": [lambda d: asyncio.create_task(download_progress_hook(d, progress_message))],
        }
        
        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        downloaded_files = os.listdir(output_dir)
        downloaded_files = [os.path.join(output_dir, f) for f in downloaded_files if os.path.isfile(os.path.join(output_dir, f))]
        
        # Send the downloaded video to the user
        for file_path in downloaded_files:
            await client.send_document(chat_id, file_path, progress=upload_progress, progress_args=(progress_message,))
        
        await progress_message.edit_text("Download and upload completed successfully!")

        # Cleanup downloaded files
        for file_path in downloaded_files:
            os.remove(file_path)
        os.rmdir(output_dir)  # Remove user-specific directory after sending files
    except IndexError:
        await message.reply("Please provide a valid URL. Usage: `/download <URL>`")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
