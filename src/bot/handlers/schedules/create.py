from datetime import datetime, timezone

import pytz
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.llm_service import LLMService
from src.services.schedule_service import ScheduleService
from src.utils.parsers import parse_prescription

from .router import router


class ScheduleStates(StatesGroup):
    waiting_drug_name = State()
    waiting_dose = State()
    waiting_frequency = State()
    waiting_duration = State()
    waiting_comment = State()
    waiting_confirmation = State()


def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Cancel")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_skip_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➡️ Skip")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_skip_or_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➡️ Skip")
    builder.button(text="❌ Cancel")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def is_skip(message: Message) -> bool:
    if not message.text:
        return False
    return message.text.lower() in ["skip", "➡️ skip"]


@router.message(
    StateFilter(ScheduleStates),
    F.text == "❌ Cancel",
)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Schedule creation canceled.", reply_markup=ReplyKeyboardRemove()
    )


async def send_confirmation(message: Message, state_data: dict):
    text = (
        "📝 Please confirm your medication schedule:\n\n"
        f"💊 Drug: {state_data['drug_name']}\n"
        f"📏 Dose: {state_data['dose']}\n"
        f"⏰ Frequency: {state_data['doses_per_day']} times/day\n"
        f"📅 Duration: {state_data['duration']} days\n"
        f"📝 Comment: {state_data.get('comment', 'None')}"
    )

    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Confirm")
    builder.button(text="❌ Cancel")
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(Command("schedule"))
async def start_schedule(message: Message, state: FSMContext, user: User):
    if not user.privacy_accepted:
        await message.answer(
            "👋 Welcome to MedGuard!\n\n" "Before we start, please register: /start",
        )
        return

    await message.answer(
        "💊 Let's create a new medication schedule.\n\n"
        "You can either:\n"
        "1. Enter details step by step, starting with the drug name\n"
        "2. Paste a prescription line (e.g. 'Take Aspirin 1 tablet 3 times daily for 7 days')",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_drug_name)


@router.message(ScheduleStates.waiting_drug_name, F.text)
async def process_drug_name(
    message: Message, state: FSMContext, llm_service: LLMService
):
    if not message.text:
        await message.answer("Please enter a valid drug name:")
        return

    # Try to parse natural language input
    if len(message.text.split()) > 3:
        parsed = await parse_prescription(llm_service, message.text)
        if parsed:
            await state.update_data(**parsed.model_dump())
            await send_confirmation(message, parsed.model_dump())
            await state.set_state(ScheduleStates.waiting_confirmation)
            return
        else:
            await message.answer(
                "I couldn't parse that as a prescription. Let's continue step by step."
            )

    await state.update_data(drug_name=message.text)
    await message.answer(
        "📏 Enter dosage (e.g. '1 tablet', '500mg'):",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_dose)


@router.message(ScheduleStates.waiting_dose, F.text)
async def process_dose(message: Message, state: FSMContext):
    await state.update_data(dose=message.text)
    await message.answer(
        "⏰ How many times per day? (Enter number):",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_frequency)


@router.message(ScheduleStates.waiting_frequency, F.text)
async def process_frequency(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Please enter a valid frequency:")
        return

    try:
        frequency = int(message.text)
        if frequency < 1:
            raise ValueError
        await state.update_data(doses_per_day=frequency)
        await message.answer(
            "📅 Duration in days? (Enter number):",
            reply_markup=get_skip_or_cancel_keyboard(),
        )
        await state.set_state(ScheduleStates.waiting_duration)
    except ValueError:
        await message.answer("Please enter a valid positive number:")


@router.message(ScheduleStates.waiting_duration, F.text)
async def process_duration(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Please enter a valid duration:")
        return

    try:
        duration = int(message.text)
        if duration < 1:
            raise ValueError
        if is_skip(message):
            await state.update_data(duration=None)
        else:
            await state.update_data(duration=duration)
        await message.answer(
            "📝 Any comments? (Optional, type 'skip' to omit):",
            reply_markup=get_skip_keyboard(),
        )
        await state.set_state(ScheduleStates.waiting_comment)
    except ValueError:
        await message.answer("Please enter a valid positive number:")


@router.message(ScheduleStates.waiting_comment, F.text)
async def process_comment(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Please enter a valid comment:")
        return

    if not is_skip(message):
        await state.update_data(comment=message.text)
    await send_confirmation(message, await state.get_data())
    await state.set_state(ScheduleStates.waiting_confirmation)


@router.message(ScheduleStates.waiting_confirmation, F.text == "✅ Confirm")
async def handle_confirmation(
    message: Message, state: FSMContext, session: AsyncSession, user: User
):
    state_data = await state.get_data()
    service = ScheduleService(session)

    try:
        schedule = await service.create_schedule(
            user_id=user.id,
            drug_name=state_data["drug_name"],
            dose=state_data["dose"],
            doses_per_day=state_data["doses_per_day"],
            duration=state_data["duration"],
            comment=state_data.get("comment"),
            start_datetime=datetime.now(
                timezone.utc
            ),  # Or allow user to specify start time
        )
        next_dose_time = await service.get_next_dose_time(user, schedule)
        await message.answer(
            "✅ Schedule created successfully!\n"
            f"Next dose: {next_dose_time.astimezone(pytz.timezone(user.timezone)).strftime('%d %b at %H:%M') if next_dose_time else 'No doses scheduled (schedule may be complete)'}\n"
            f"You'll receive reminders when it's time to take your medication.",
            reply_markup=ReplyKeyboardRemove(),
        )
    except ValueError as e:
        await message.answer(f"Error creating schedule: {str(e)}")

    await state.clear()
