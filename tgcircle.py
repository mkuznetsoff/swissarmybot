import telebot
import cv2
import numpy as np
import os
import time
import logging
from moviepy.editor import VideoFileClip, AudioFileClip

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot_log.txt"), logging.StreamHandler()]
)

TOKEN = '7370489438:AAGL0PyF58JTVdl5YSlHxS3BO33-ca9JgQo'
bot = telebot.TeleBot(TOKEN)

# Папка для временных файлов
temp_dir = r"C:\Users\ndbya\Documents\kodd\tts\cir"
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)
    logging.info(f"Создана папка для файлов: {temp_dir}")

# Константы видео note
NOTE_SIZE = 512  # видео note должно быть квадратным
OUT_FPS = 60
MAX_DURATION = 60  # секунд

# Словарь для хранения файлов пользователей и их индексов
user_files = {}

# /start сообщение
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Я БОТ ДЕЛАЮ КРУЖКИ 🎥✨\nПришли мне видео (mp4, avi, gif) — и я превращу его в встроенное видео сообщение!")
    logging.info(f"Получено сообщение /start от {message.from_user.username}")

# Обработка медиа (video, document, animation)
@bot.message_handler(content_types=['video', 'document', 'animation'])
def handle_media(message):
    logging.info(f"Получено сообщение с типом {message.content_type} от {message.from_user.username}")
    bot.send_message(message.chat.id, "🎬 Видео принято. Начинаю обработку...")

    # Получаем уникальный идентификатор пользователя
    user_id = message.from_user.id

    # Увеличиваем индекс для каждого пользователя
    if user_id not in user_files:
        user_files[user_id] = 0  # Начинаем с первого файла
    user_files[user_id] += 1
    file_index = user_files[user_id]

    # Определяем file_id для разных типов медиа
    if message.content_type == 'video':
        file_id = message.video.file_id
    elif message.content_type == 'document':
        file_id = message.document.file_id
    elif message.content_type == 'animation':
        file_id = message.animation.file_id
    else:
        bot.send_message(message.chat.id, "❌ Неподдерживаемый формат.")
        logging.error(f"Неподдерживаемый формат: {message.content_type}")
        return

    # Скачивание файла
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Создаем папку для каждого пользователя (если еще не существует)
    user_folder = os.path.join(temp_dir, str(user_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
        logging.info(f"Создана папка для пользователя {user_id}: {user_folder}")

    # Сохранение файла с индексом
    input_path = os.path.join(user_folder, f"input_video_{file_index}.mp4")
    output_path = os.path.join(user_folder, f"output_video_{file_index}.mp4")

    with open(input_path, 'wb') as f:
        f.write(downloaded_file)
    logging.info(f"Файл скачан и сохранён как {input_path}")

    # Имитация прогресса обработки
    status = bot.send_message(message.chat.id, "⏳ Обработка [▓         ] 10%")
    time.sleep(1)
    bot.edit_message_text("⏳ Обработка [▓▓▓       ] 40%", chat_id=message.chat.id, message_id=status.message_id)
    time.sleep(1)
    bot.edit_message_text("⏳ Обработка [▓▓▓▓▓     ] 60%", chat_id=message.chat.id, message_id=status.message_id)
    time.sleep(1)

    # Открываем входящее видео с помощью moviepy для обработки аудио
    video_clip = VideoFileClip(input_path)
    audio_clip = video_clip.audio  # Извлекаем аудио из видео

    # Если видео длится больше MAX_DURATION, обрезаем его
    if video_clip.duration > MAX_DURATION:
        video_clip = video_clip.subclip(0, MAX_DURATION)
        logging.info(f"Видео обрезано до {MAX_DURATION} секунд")

    # Имитация маски и изменения видео
    video_fps = video_clip.fps
    logging.info(f"Исходное видео: {video_clip.duration} сек, {video_fps} FPS")

    # Создаём круговую маску
    mask = np.zeros((NOTE_SIZE, NOTE_SIZE), dtype=np.uint8)
    cv2.circle(mask, (NOTE_SIZE // 2, NOTE_SIZE // 2), NOTE_SIZE // 2, 255, -1)

    # Настроим выходной файл
    out_path = os.path.join(user_folder, f"output_video_{file_index}.mp4")
    video_writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), OUT_FPS, (NOTE_SIZE, NOTE_SIZE))

    for frame in video_clip.iter_frames(fps=video_fps, dtype="uint8"):
        frame_resized = cv2.resize(frame, (NOTE_SIZE, NOTE_SIZE))

        # Преобразуем формат цветов (OpenCV использует BGR, а MoviePy — RGB)
        frame_resized = cv2.cvtColor(frame_resized, cv2.COLOR_RGB2BGR)

        circular_frame = cv2.bitwise_and(frame_resized, frame_resized, mask=mask)
        video_writer.write(circular_frame)

    video_writer.release()

    # Объединяем обработанное видео с исходным звуком
    final_video = VideoFileClip(out_path)
    final_audio = audio_clip.subclip(0, final_video.duration)
    final_video = final_video.set_audio(final_audio)
    final_video.write_videofile(out_path, codec="libx264", audio_codec="aac")

    logging.info(f"Обработка видео завершена. Выходной файл: {out_path}")

    bot.edit_message_text("✅ Обработка завершена!", chat_id=message.chat.id, message_id=status.message_id)

    # Отправка встроенного видео сообщения (video note)
    with open(out_path, 'rb') as video_file:
        bot.send_video_note(message.chat.id, video_file)
    logging.info(f"Видео сообщение отправлено пользователю {message.from_user.username}")

    # Очистка временных файлов
    try:
        os.remove(input_path)
        os.remove(out_path)
        logging.info("Временные файлы удалены")
    except PermissionError:
        logging.error(f"Ошибка при удалении файлов, файл занят: {input_path} или {out_path}")
        time.sleep(1)  # Добавляем небольшую задержку перед повторной попыткой удалить файлы
        try:
            os.remove(input_path)
            os.remove(out_path)
        except Exception as e:
            logging.error(f"Ошибка повторной попытки удаления файлов: {e}")

bot.polling()
