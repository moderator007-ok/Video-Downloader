FROM python:3.9-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy requirements.txt and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run the application
CMD gunicorn app:app & python3 bot.py
