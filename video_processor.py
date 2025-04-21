# video_processor.py

import os
import tempfile
import shutil
import logging
import numpy as np
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from aiogram import types, Router
from config import TEMP_DIR, NOTE_SIZE, MAX_DURATION

router = Router()
user_files = {}

@router.message(lambda message: message.video or message.document or message.animation)
async def handle_media(message: types.Message, bot):
    try:
        logging.info(f"Тип {message.content_type} от {message.from_user.username}")
        await message.answer("🎬 Видео принято. Начинаю обработку...")

        user_id = message.from_user.id
        user_files[user_id] = user_files.get(user_id, 0) + 1
        file_index = user_files[user_id]

        file_id = None
        if message.video:
            file_id = message.video.file_id
        elif message.document:
            file_id = message.document.file_id
        elif message.animation:
            file_id = message.animation.file_id

        if not file_id:
            await message.answer("❌ Неподдерживаемый формат.")
            return

        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        user_folder = os.path.join(TEMP_DIR, str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        input_path = os.path.join(user_folder, f"input_{file_index}.mp4")
        output_path = os.path.join(user_folder, f"output_{file_index}.mp4")

        with open(input_path, 'wb') as f:
            f.write(downloaded_file.read())

        status = await message.answer("⏳ Обработка [▓         ] 10%")
        await asyncio.sleep(1)
        await status.edit_text("⏳ Обработка [▓▓▓       ] 40%")
        await asyncio.sleep(1)

        # Загрузка видео и обрезка
        video_clip = VideoFileClip(input_path)
        duration = min(video_clip.duration, MAX_DURATION)
        video_clip = video_clip.subclip(0, duration)
        audio_clip = video_clip.audio.subclip(0, duration) if video_clip.audio else None
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

        await status.edit_text("⏳ Обработка [▓▓▓▓▓     ] 60%")

        # Сборка и сохранение
        final_clip = ImageSequenceClip(processed_frames, fps=fps)
        if audio_clip:
            final_clip = final_clip.set_audio(audio_clip)
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

        await status.edit_text("✅ Готово! Отправляю кружочек!")
        with open(output_path, 'rb') as video_file:
            await message.answer_video_note(video_file)

        try:
            os.remove(input_path)
            os.remove(output_path)
        except Exception as e:
            logging.error(f"Ошибка при удалении файлов: {e}")

    except Exception as e:
        logging.error(f"Ошибка при обработке видео: {e}")
        await message.answer(f"❌ Ошибка при обработке видео: {e}")

