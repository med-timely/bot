import random
from datetime import datetime, timezone

import pytz
from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ContentType, KeyboardButton, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from timezonefinder import TimezoneFinder

timezone_finder_singleton = TimezoneFinder()

from src.models import User
from src.services.user_service import UserService

from .router import router
from .utils import calculate_timezone_from_time


class StartStates(StatesGroup):
    """FSM states for the start command flow."""

    waiting_privacy_acceptance = State()
    waiting_phone = State()
    waiting_timezone = State()


def get_privacy_keyboard():
    """Create a keyboard with privacy policy acceptance options."""

    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Accept")
    builder.button(text="❌ Decline")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_phone_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Share Phone", request_contact=True)
    builder.button(text="➡️ Skip")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_location_share_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🌍 Share Location", request_location=True)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, user: User):
    if user.privacy_accepted:
        await message.answer("Welcome back! Use /schedule to manage medications.")
        return

    await message.answer(
        "👋 Welcome to MedGuard!\n\n"
        "Before we start, please:\n"
        "1. Read our [Privacy Policy](https://example.com/privacy)\n"
        "2. Confirm you agree with data processing",
        reply_markup=get_privacy_keyboard(),
        parse_mode="Markdown",
    )
    await state.set_state(StartStates.waiting_privacy_acceptance)


@router.message(
    StartStates.waiting_privacy_acceptance, F.text.in_(["✅ Accept", "❌ Decline"])
)
async def handle_privacy_choice(
    message: Message, state: FSMContext, user: User, user_service: UserService
):
    if message.text == "❌ Decline":
        await message.answer(
            "❌ You must accept the privacy policy to use this service.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    await user_service.accept_privacy(user.id)

    await message.answer(
        "Thank you for accepting our privacy policy! 🎉\n\n"
        "Would you like to share your phone number for emergency contacts?",
        reply_markup=get_phone_keyboard(),
    )
    await state.set_state(StartStates.waiting_phone)


@router.message(StartStates.waiting_privacy_acceptance)
async def invalid_privacy_response(message: Message):
    await message.answer(
        "Please use the buttons to accept or decline the privacy policy."
    )


@router.message(
    StartStates.waiting_phone,
    F.content_type.in_({ContentType.CONTACT, ContentType.TEXT}),
)
async def handle_phone_input(
    message: Message, state: FSMContext, user: User, user_service: UserService
):
    if message.content_type == ContentType.CONTACT:
        if not message.contact:
            await message.answer("⚠️ Please share your phone number.")
            return

        if message.contact.user_id != message.from_user.id:
            await message.answer("⚠️ Please share your own phone number.")
            return

        await user_service.update(user.id, phone_number=message.contact.phone_number)

        await message.answer(
            "✅ Phone number saved!", reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "➡️ Skip":
        await message.answer(
            "You can add phone later in profile.", reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("Please use the buttons below to share phone or skip.")
        return

    await message.answer(
        "🌍 For accurate medication reminders, we need your timezone.\n\n"
        "Please either:\n"
        "1. Share your current location\n"
        "2. Send your local time (e.g. 14:30)",
        reply_markup=get_location_share_keyboard(),
    )
    await state.set_state(StartStates.waiting_timezone)


@router.message(StartStates.waiting_phone)
async def invalid_phone_input(message: Message):
    await message.answer("Please use the buttons to share phone number or skip.")


@router.message(StartStates.waiting_timezone)
async def handle_time_input(
    message: Message, state: FSMContext, user: User, user_service: UserService
):
    utc_now = datetime.now(timezone.utc)
    response = None

    # Handle location sharing
    if message.location:
        tz = timezone_finder_singleton.timezone_at(
            lat=message.location.latitude, lng=message.location.longitude
        )
        if tz:
            await user_service.update(user.id, timezone=tz)
            response = f"✅ Timezone detected: {tz}"

    # Handle time input
    elif message.text:
        if message.text in pytz.all_timezones_set:
            await user_service.update(user.id, timezone=message.text)
            response = f"✅ Timezone detected: {message.text}"
        else:
            timezones, offset = calculate_timezone_from_time(message.text, utc_now)
            if not timezones:
                pass
            elif len(timezones) == 1:
                await user_service.update(user.id, timezone=timezones[0])
                response = f"✅ Timezone set to {timezones[0]} (UTC{offset:+g})"
            else:
                builder = ReplyKeyboardBuilder()
                random.shuffle(timezones)
                for tz in sorted(timezones[:6]):  # Show top 6 matches
                    builder.button(text=tz)
                builder.adjust(2)
                builder.row(
                    KeyboardButton(text="🌍 Share Location", request_location=True)
                )
                response = "📍 Multiple matches found. Please choose the most suitable timezone:"
                await message.answer(response, reply_markup=builder.as_markup())
                return
    else:
        pass

    if response:
        response += (
            "\n\n"
            "💊 Now let's create your first medication schedule!\n\n"
            "Use /schedule command and follow the instructions.\n\n"
            "Type /help anytime for assistance."
        )

        await message.answer(response, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        # Continue to next onboarding step
    else:
        await message.answer(
            "❌ Couldn't detect timezone. Please try again.",
            reply_markup=get_location_share_keyboard(),
        )
