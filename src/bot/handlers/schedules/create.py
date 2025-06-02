from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.llm_service import LLMService
from src.services.schedule_service import ScheduleService
from src.utils.parsers import parse_prescription

router = Router()


class ScheduleStates(StatesGroup):
    waiting_drug_name = State()
    waiting_dose = State()
    waiting_frequency = State()
    waiting_duration = State()
    waiting_comment = State()
    waiting_confirmation = State()


def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text=_("❌ Cancel"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_skip_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text=_("➡️ Skip"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_skip_or_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text=_("➡️ Skip"))
    builder.button(text=_("❌ Cancel"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def is_skip(message: Message) -> bool:
    if not message.text:
        return False
    return message.text.lower() in [_("skip"), _("➡️ skip")]


async def process_prescription_line(
    message: Message, line: str | None, state: FSMContext, llm_service: LLMService
):
    if not line:
        return None

    parsed = await parse_prescription(llm_service, line)
    if not parsed:
        return False

    await state.update_data(**parsed.model_dump())
    await send_confirmation(message, parsed.model_dump())
    await state.set_state(ScheduleStates.waiting_confirmation)

    return True


@router.message(
    StateFilter(ScheduleStates),
    F.text == __("❌ Cancel"),
)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        _("Schedule creation canceled."), reply_markup=ReplyKeyboardRemove()
    )


async def send_confirmation(message: Message, state_data: dict):
    duration = (
        _("{duration} day", "{duration} days", state_data["duration"]).format(
            duration=state_data["duration"]
        )
        if state_data.get("duration")
        else _("not specified")
    )
    text = _(
        "📝 Please confirm your medication schedule:\n\n"
        "   💊 Drug: {drug_name}\n"
        "   📏 Dose: {dose}\n"
        "   ⏰ Frequency: {frequency} time/day\n"
        "   📅 Duration: {duration}\n"
        "   📝 Note: {comment}",
        "📝 Please confirm your medication schedule:\n\n"
        "   💊 Drug: {drug_name}\n"
        "   📏 Dose: {dose}\n"
        "   ⏰ Frequency: {frequency} times/day\n"
        "   📅 Duration: {duration}\n"
        "   📝 Note: {comment}",
        state_data["doses_per_day"],
    ).format(
        drug_name=state_data["drug_name"],
        dose=state_data["dose"],
        frequency=state_data["doses_per_day"],
        duration=duration,
        comment=state_data.get("comment", _("None")),
    )

    builder = ReplyKeyboardBuilder()
    builder.button(text=_("✅ Confirm"))
    builder.button(text=_("❌ Cancel"))
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(Command("schedule"))
async def start_schedule(
    message: Message,
    state: FSMContext,
    user: User,
    llm_service: LLMService,
    command: CommandObject,
):
    if not user.privacy_accepted:
        await message.answer(
            _("👋 Welcome to MedTimely!\n\nBefore we start, please register: /start"),
        )
        return

    args = command.args
    parsed = await process_prescription_line(message, args, state, llm_service)
    if parsed:
        return
    if args:
        message.answer(
            _("I couldn't parse that as a prescription. Let's continue step by step.")
        )

    await message.answer(
        _(
            "💊 Let's create a new medication schedule.\n\n"
            "You can either:\n"
            "1. Enter details step by step, starting with the drug name\n"
            "2. Paste a prescription line (e.g. 'Take Aspirin 1 tablet 3 times daily for 7 days')"
        ),
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_drug_name)


@router.message(ScheduleStates.waiting_drug_name, F.text)
async def process_drug_name(
    message: Message, state: FSMContext, llm_service: LLMService
):
    if not message.text:
        await message.answer(_("Please enter a valid drug name:"))
        return

    # Try to parse natural language input
    if len(message.text.split()) > 3:
        parsed = await process_prescription_line(
            message, message.text, state, llm_service
        )
        if parsed:
            return

        await message.answer(
            _("I couldn't parse that as a prescription. Let's continue step by step.")
        )

    await state.update_data(drug_name=message.text)
    await message.answer(
        _("📏 Enter dosage (e.g. '1 tablet', '500mg'):"),
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_dose)


@router.message(ScheduleStates.waiting_dose, F.text)
async def process_dose(message: Message, state: FSMContext):
    await state.update_data(dose=message.text)
    await message.answer(
        _("⏰ How many times per day? (Enter number):"),
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_frequency)


@router.message(ScheduleStates.waiting_frequency, F.text)
async def process_frequency(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(_("Please enter a valid frequency:"))
        return

    try:
        frequency = int(message.text)
        if frequency < 1:
            raise ValueError
        await state.update_data(doses_per_day=frequency)
        await message.answer(
            _("📅 Duration in days? (Enter number):"),
            reply_markup=get_skip_or_cancel_keyboard(),
        )
        await state.set_state(ScheduleStates.waiting_duration)
    except ValueError:
        await message.answer(_("Please enter a valid positive number:"))


@router.message(ScheduleStates.waiting_duration, F.text)
async def process_duration(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(_("Please enter a valid duration:"))
        return

    if is_skip(message):
        await state.update_data(duration=None)
    else:
        try:
            duration = int(message.text)
            if duration < 1:
                raise ValueError

            await state.update_data(duration=duration)

        except ValueError:
            await message.answer(_("Please enter a valid positive number:"))
            return

    await message.answer(
        _("📝 Any comments? (Optional, type 'skip' to omit):"),
        reply_markup=get_skip_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_comment)


@router.message(ScheduleStates.waiting_comment, F.text)
async def process_comment(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(_("Please enter a valid comment:"))
        return

    if not is_skip(message):
        await state.update_data(comment=message.text)
    await send_confirmation(message, await state.get_data())
    await state.set_state(ScheduleStates.waiting_confirmation)


@router.message(ScheduleStates.waiting_confirmation, F.text == __("✅ Confirm"))
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
            _(
                "✅ Schedule created successfully!\n"
                "Next dose: {next_dose}\n"
                "You'll receive reminders when it's time to take your medication."
            ).format(
                next_dose=(
                    user.in_local_time(next_dose_time).strftime("%d %b at %H:%M")
                    if next_dose_time
                    else _("No doses scheduled (schedule may be complete)")
                )
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
    except ValueError as e:
        await message.answer(_("Error creating schedule: {error}").format(error=str(e)))

    await state.clear()
