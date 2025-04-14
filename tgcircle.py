import telebot
import os
import time
import logging
import numpy as np
from moviepy import VideoFileClip, AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
import cv2
import tempfile
import shutil

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot_log.txt"), logging.StreamHandler()]
)

TOKEN = '7370489438:AAGL0PyF58JTVdl5YSlHxS3BO33-ca9JgQo'  # ← ВСТАВЬ СВОЙ ТОКЕН ЗДЕСЬ
bot = telebot.TeleBot(TOKEN)

# Временная директория
temp_dir = tempfile.mkdtemp()
logging.info(f"Создана временная директория: {temp_dir}")

NOTE_SIZE = 512
MAX_DURATION = 60
user_files = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🎥 Привет! Пришли мне видео (mp4, avi, gif), и я превращу его в круглую видеозаметку!"
    )
    logging.info(f"/start от {message.from_user.username}")

@bot.message_handler(content_types=['video', 'document', 'animation'])
def handle_media(message):
    try:
        logging.info(f"Тип {message.content_type} от {message.from_user.username}")
        bot.send_message(message.chat.id, "🎬 Видео принято. Начинаю обработку...")

        user_id = message.from_user.id
        user_files[user_id] = user_files.get(user_id, 0) + 1
        file_index = user_files[user_id]

        file_id = None
        if message.content_type == 'video':
            file_id = message.video.file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id
        elif message.content_type == 'animation':
            file_id = message.animation.file_id

        if not file_id:
            bot.send_message(message.chat.id, "❌ Неподдерживаемый формат.")
            return

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        user_folder = os.path.join(temp_dir, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        input_path = os.path.join(user_folder, f"input_{file_index}.mp4")
        output_path = os.path.join(user_folder, f"output_{file_index}.mp4")

        with open(input_path, 'wb') as f:
            f.write(downloaded_file)

        status = bot.send_message(message.chat.id, "⏳ Обработка [▓         ] 10%")
        time.sleep(1)
        bot.edit_message_text("⏳ Обработка [▓▓▓       ] 40%", chat_id=message.chat.id, message_id=status.message_id)
        time.sleep(1)

        # Загрузка видео и обрезка
        video_clip = VideoFileClip(input_path)
        duration = min(video_clip.duration, MAX_DURATION)
        video_clip = video_clip.subclipped(0, duration)
        audio_clip = video_clip.audio.subclipped(0, duration) if video_clip.audio else None

        fps = min(int(video_clip.fps), 60)
        logging.info(f"FPS: оригинал={video_clip.fps}, используем={fps}")

        # Круглая маска
        mask = np.zeros((NOTE_SIZE, NOTE_SIZE), dtype=np.uint8)
        cv2.circle(mask, (NOTE_SIZE // 2, NOTE_SIZE // 2), NOTE_SIZE // 2, 255, -1)

        # Обработка кадров
        processed_frames = []
        for frame in video_clip.iter_frames(fps=fps, dtype="uint8"):
            h, w, _ = frame.shape
            min_dim = min(h, w)
            top = (h - min_dim) // 2
            left = (w - min_dim) // 2
            cropped = frame[top:top+min_dim, left:left+min_dim]
            resized = cv2.resize(cropped, (NOTE_SIZE, NOTE_SIZE))
            bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR)
            circled = cv2.bitwise_and(bgr, bgr, mask=mask)
            processed_frames.append(cv2.cvtColor(circled, cv2.COLOR_BGR2RGB))

        bot.edit_message_text("⏳ Обработка [▓▓▓▓▓     ] 60%", chat_id=message.chat.id, message_id=status.message_id)

        # Сборка и сохранение
        final_clip = ImageSequenceClip(processed_frames, fps=fps)
        if audio_clip:
            final_clip = final_clip.with_audio(audio_clip)

        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=fps,
            preset='ultrafast',
            threads=4,
            logger=None
        )

        video_clip.close()
        if audio_clip:
            audio_clip.close()
        final_clip.close()

        bot.edit_message_text("✅ Готово! Отправляю кружочек!", chat_id=message.chat.id, message_id=status.message_id)

        with open(output_path, 'rb') as video_file:
            bot.send_video_note(message.chat.id, video_file)

        try:
            os.remove(input_path)
            os.remove(output_path)
        except Exception as e:
            logging.error(f"Ошибка при удалении файлов: {e}")

    except Exception as e:
        logging.error(f"Ошибка при обработке видео: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка при обработке видео: {e}")

try:
    bot.polling()
finally:
    # Очистка всей временной директории
    shutil.rmtree(temp_dir)
    logging.info(f"Удалена временная директория: {temp_dir}")
