from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

TOKEN = "9283167555:AAEeuL_Q7y1wTvYvjh3siUY5UaobvxPL6X4"
bot = Bot(token=TOKEN)

ADMIN_CHAT_ID = -5595096634

router = Router()
dp = Dispatcher()
dp.include_router(router)

# Множество для хранения уникальных ID пользователей, запустивших бота (для рассылки)
active_users = set()

# Состояния для Машины Состояний (FSM)
class FeedbackState(StatesGroup):
    waiting_for_idea = State()
    waiting_for_feedback = State()


# Главное меню с кнопками
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💡 Предложить идею", callback_data="btn_idea"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Обратная связь / Замечание", callback_data="btn_feedback"
                )
            ],
        ]
    )


# Команда /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Сохраняем ID пользователя для будущей массовой рассылки
    active_users.add(message.from_user.id)
    
    text = (
        "Привет! 👋 Этот бот создан для того, чтобы сделать нашу школу лучше.\n\n"
        "Здесь ты можешь **анонимно** поделиться своей идеей по улучшению школы"
        " или оставить обратную связь.\n\n"
        "Выбери, что именно ты хочешь сделать:"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


# Команда для массовой рассылки (доступна только администратору)
@router.message(F.text.startswith("/send_all"))
async def broadcast_message(message: Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("У тебя нет прав для выполнения этой команды.")
        return

    text_to_send = message.text.replace("/send_all", "").strip()
    
    if not text_to_send:
        await message.answer("Напиши текст для рассылки после команды, например:\n`/send_all Всем привет!`", parse_mode="Markdown")
        return

    success_count = 0
    fail_count = 0

    for user_id in active_users:
        try:
            await bot.send_message(user_id, f"📢 **Объявление от администрации:**\n\n{text_to_send}", parse_mode="Markdown")
            success_count += 1
            await asyncio.sleep(0.1)  # Небольшая пауза, чтобы Telegram не блокировал за спам
        except Exception:
            fail_count += 1

    await message.answer(f"✅ Рассылка завершена!\nУспешно отправлено: {success_count}\nНе удалось отправить: {fail_count}")


# Функция ответа администратора ученику через Reply (ответ на сообщение в админ-чате)
@router.message(F.reply_to_message)
async def admin_reply(message: Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    replied_msg = message.reply_to_message.text
    if not replied_msg:
        return

    try:
        if "ID:" in replied_msg:
            parts = replied_msg.split("ID:")
            user_id = int(parts[1].split()[0])
            
            await bot.send_message(
                user_id,
                f"💬 **Ответ от администрации:**\n\n{message.text}",
                parse_mode="Markdown"
            )
            await message.answer("✅ Ответ успешно отправлен ученику!")
        else:
            await message.answer("⚠️ Не удалось найти ID ученика. Отвечай именно на пересланное из бота сообщение.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке ответа: {e}")


# Обработка нажатия на кнопку "Идея"
@router.callback_query(F.data == "btn_idea")
async def process_idea_btn(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💡 Отлично! Напиши свою идею одним сообщением. Расскажи подробно, что"
        " именно ты хочешь предложить и как это реализовать."
    )
    await state.set_state(FeedbackState.waiting_for_idea)
    await callback.answer()


# Обработка нажатия на кнопку "Обратная связь"
@router.callback_query(F.data == "btn_feedback")
async def process_feedback_btn(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 Напиши свое замечание или обратную связь одним сообщением. Старайся"
        " писать конструктивно, чтобы мы могли оперативно во всем разобраться."
    )
    await state.set_state(FeedbackState.waiting_for_feedback)
    await callback.answer()


# Получение идеи от пользователя (с добавлением скрытого ID для возможности ответа)
@router.message(FeedbackState.waiting_for_idea)
async def receive_idea(message: Message, state: FSMContext, bot: Bot):
  idea_text = message.text
  user_id = message.from_user.id

  # Пересылаем в чат администраторов вместе с ID пользователя
  admin_message = (
      f"💡 **НОВАЯ ИДЕЯ от ученика:**\n\n{idea_text}\n\n"
      f"🆔 ID: `{user_id}`\n"
      f"_(Отправлено анонимно через школьного бота)_"
  )
  await bot.send_message(
      ADMIN_CHAT_ID, admin_message, parse_mode="Markdown"
  )

  await message.answer(
      "✅ Спасибо! Твоя идея успешно отправлена администраторам школы.",
      reply_markup=get_main_keyboard(),
  )
  await state.clear()


# Получение обратной связи от пользователя (с добавлением скрытого ID для возможности ответа)
@router.message(FeedbackState.waiting_for_feedback)
async def receive_feedback(message: Message, state: FSMContext, bot: Bot):
  feedback_text = message.text
  user_id = message.from_user.id

  # Пересылаем в чат администраторов вместе с ID пользователя
  admin_message = (
      f"💬 **НОВОЕ ОБРАЩЕНИЕ / ЗАМЕЧАНИЕ:**\n\n{feedback_text}\n\n"
      f"🆔 ID: `{user_id}`\n"
      f"_(Отправлено анонимно через школьного бота)_"
  )
  await bot.send_message(
      ADMIN_CHAT_ID, admin_message, parse_mode="Markdown"
  )

  await message.answer(
      "✅ Спасибо за обратную связь. Твое сообщение передано администрации.",
      reply_markup=get_main_keyboard(),
  )
  await state.clear()

async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

async def web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def main():
    await asyncio.gather(web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
    # Команда для ответа ученику по его ID: /answer ID текст_ответа
@router.message(F.text.startswith("/answer"))
async def answer_user(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("У тебя нет прав для выполнения этой команды.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ Неправильный формат!\nИспользуй так:\n`/answer [ID] [текст ответа]`",
            parse_mode="Markdown"
        )
        return

    try:
        user_id = int(parts[1])
        reply_text = parts[2]

        await bot.send_message(
            user_id,
            f"💬 **Ответ от администрации:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ответ успешно отправлен ученику!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")
