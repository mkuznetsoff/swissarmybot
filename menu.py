from aiogram import types, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

router = Router()

# Создание клавиатуры меню
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎥 Создать кружок")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Выберите опцию из меню:", reply_markup=menu_keyboard)

@router.message(lambda message: message.text == "🎥 Создать кружок")
async def create_circle_prompt(message: types.Message):
    await message.answer("Пожалуйста, отправьте видео (mp4, avi, gif), и я превращу его в круглую видеозаметку.")

@router.message(lambda message: message.text == "❓ Помощь")
async def help_command(message: types.Message):
    await message.answer("Это бот с меню. Выберите опцию для продолжения.")
