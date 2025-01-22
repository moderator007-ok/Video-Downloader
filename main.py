from pyrogram import Client, filters
import os
from yt_dlp import YoutubeDL

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
        await message.reply("Downloading your video... Please wait!")
        
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
        }
        
        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        downloaded_files = os.listdir(output_dir)
        downloaded_files = [os.path.join(output_dir, f) for f in downloaded_files if os.path.isfile(os.path.join(output_dir, f))]
        
        # Send the downloaded video to the user
        for file_path in downloaded_files:
            await message.reply_document(file_path)
        
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
