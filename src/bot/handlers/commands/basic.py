from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand

router = Router()
commands = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="Show help"),
]


@router.message(CommandStart())
async def handle_start(message: Message):
    """
    Handle the /start command.
    Sends a welcome message to the user introducing the bot.
    """
    await message.answer(
        "💊 Welcome to MedGuard!\nUse /schedule to create a new medication schedule."
    )


@router.message(Command("help"))
async def handle_help(message: Message):
    """
    Handle the /help command.
    Sends a message listing all available commands and their descriptions.
    """
    await message.answer(
        "🆘 Help:\n"
        "/schedule - Create medication schedule\n"
        "/list - Show active medications\n"
        "/taken - Confirm dose taken"
    )
