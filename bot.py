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
async def cmd_start(message: Message):
  text = (
      "Привет! 👋 Этот бот создан для того, чтобы сделать нашу школу лучше.\n\n"
      "Здесь ты можешь **анонимно** поделиться своей идеей по улучшению школы"
      " или оставить обратную связь.\n\n"
      "Выбери, что именно ты хочешь сделать:"
  )
  await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


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


# Получение идеи от пользователя
@router.message(FeedbackState.waiting_for_idea)
async def receive_idea(message: Message, state: FSMContext, bot: Bot):
  idea_text = message.text

  # Пересылаем в чат администраторов
  admin_message = (
      f"💡 **НОВАЯ ИДЕЯ от ученика:**\n\n{idea_text}\n\n"
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


# Получение обратной связи от пользователя
@router.message(FeedbackState.waiting_for_feedback)
async def receive_feedback(message: Message, state: FSMContext, bot: Bot):
  feedback_text = message.text

  # Пересылаем в чат администраторов
  admin_message = (
      f"💬 **НОВОЕ ОБРАЩЕНИЕ / ЗАМЕЧАНИЕ:**\n\n{feedback_text}\n\n"
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
