import os
import asyncio
import logging
import cloudscraper
import m3u8
from yt_dlp import YoutubeDL
from pyrogram import Client, filters
import ffmpeg

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Bot credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Initialize Pyrogram client
app = Client("yt-dlp_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Progress handlers
async def download_progress_hook(d, progress_message):
    if d["status"] == "downloading":
        total_bytes = d.get("total_bytes", d.get("total_bytes_estimate", 0))
        downloaded_bytes = d.get("downloaded_bytes", 0)
        percentage = (downloaded_bytes / total_bytes * 100) if total_bytes else 0
        await progress_message.edit_text(f"Downloading: {percentage:.2f}%")

async def upload_progress(current, total, progress_message):
    percentage = current / total * 100
    await progress_message.edit_text(f"Uploading: {percentage:.2f}%")

# Check for m3u8 format
def is_m3u8_format(url):
    return ".m3u8" in url

# Handle m3u8 download
def download_m3u8_with_python(url, output_file):
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = scraper.get(url, headers=headers)
    response.raise_for_status()
    m3u8_obj = m3u8.loads(response.text)
    base_url = url.rsplit("/", 1)[0]

    ts_files = [segment.uri for segment in m3u8_obj.segments]
    with open(output_file, "wb") as outfile:
        for ts_file in ts_files:
            ts_url = f"{base_url}/{ts_file}"
            ts_data = scraper.get(ts_url, headers=headers).content
            if not ts_data:
                raise ValueError(f"Failed to download segment: {ts_url}")
            outfile.write(ts_data)

# Convert to mp4
def convert_to_mp4(input_file, output_file):
    try:
        ffmpeg.input(input_file).output(output_file, codec="copy").run(overwrite_output=True)
        logging.info(f"Converted {input_file} to {output_file}")
    except ffmpeg.Error as e:
        logging.error(f"Error converting file: {e}")
        raise

@app.on_message(filters.command("download") & filters.private)
async def download_video(client, message):
    try:
        url = message.text.split(" ", 1)[1]
        chat_id = str(message.chat.id)
        progress_message = await message.reply("Downloading your video... Please wait!")

        output_dir = os.path.join("downloads", chat_id)
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

        if is_m3u8_format(url):
            output_file = os.path.join(output_dir, "video.ts")
            download_m3u8_with_python(url, output_file)
        else:
            ydl_opts = {
                "format": "best",
                "outtmpl": output_template,
                "restrictfilenames": True,
                "nocheckcertificate": True,
                "extractor-args": {"generic": {"impersonate": "cloudflare"}},
                "progress_hooks": [lambda d: asyncio.create_task(download_progress_hook(d, progress_message))],
                "external_downloader_args": [
                    "--header", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                ]
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        downloaded_files = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if os.path.isfile(os.path.join(output_dir, f))
        ]

        for file_path in downloaded_files:
            if not file_path.endswith(".mp4"):
                mp4_file_path = os.path.splitext(file_path)[0] + ".mp4"
                try:
                    convert_to_mp4(file_path, mp4_file_path)
                except ffmpeg.Error as e:
                    await message.reply(f"Error converting file: {e}")
                file_path = mp4_file_path

            await client.send_document(chat_id, file_path, progress=upload_progress, progress_args=(progress_message,))

        await progress_message.edit_text("Download and upload completed successfully!")

        for file_path in downloaded_files:
            os.remove(file_path)
        os.rmdir(output_dir)

    except IndexError:
        await message.reply("Please provide a valid URL. Usage: `/download <URL>`")
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        await message.reply(f"An error occurred: {e}")

if __name__ == "__main__":
    logging.info("Bot is running...")
    app.run()
