import logging
import re
from datetime import time

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.bot.handlers import utils
from src.bot.keyboards import get_cancel_button
from src.models import User
from src.services.user_service import UserService

from .callbacks import ProfileCallbackData, ProfileOperation

_HOURS_RE = re.compile(r"\s*(\d{1,2})\s*[-–\s]\s*(\d{1,2})\s*$")

logger = logging.getLogger(__name__)
router = Router()


class ProfileState(StatesGroup):
    waiting_for_hours = State()


@router.callback_query(
    ProfileCallbackData.filter(F.operation == ProfileOperation.EDIT_HOURS)
)
async def edit_hours_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileState.waiting_for_hours)
    await callback.answer()

    answer = _(
        "Enter your new daylight hours (start and end) in 24-hour format:\n"
        "Example: 8 22"
    )

    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [get_cancel_button(ProfileCallbackData(operation=ProfileOperation.CANCEL))]
        ]
    )

    await utils.edit_or_answer(callback.message, answer, reply_markup=reply_markup)


@router.callback_query(
    ProfileCallbackData.filter(F.operation == ProfileOperation.CANCEL),
    ProfileState.waiting_for_hours,
)
async def cancel_edit_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()

    await utils.edit_or_answer(callback.message, _("❌ Edit cancelled"))


@router.message(ProfileState.waiting_for_hours)
async def set_hours_handler(
    message: types.Message,
    state: FSMContext,
    user: User,
    user_service: UserService,
):
    if not message.text:
        await message.reply(
            _("❌ Invalid input. Please enter your new daylight hours:")
        )
        return

    try:
        match = _HOURS_RE.fullmatch(message.text)
        if not match:
            raise ValueError(_("Please send two hour numbers, e.g. 8 22 or 08-22"))
        start_hour, end_hour = map(int, match.groups())

        # Validation
        if not (0 <= start_hour < 24 and 0 <= end_hour < 24):
            raise ValueError(_("Hours must be between 0-23"))
        if start_hour >= end_hour:
            raise ValueError(_("Start hour must be before end hour"))

        try:
            await user_service.update(
                user.id, day_start=time(start_hour, 0), day_end=time(end_hour, 0)
            )
        except Exception:
            logger.exception("Failed to update daylight hours for user %s", user.id)
            await message.reply(
                _("❌ Internal error while saving, please try again later.")
            )
            return  # keep state so the user can retry

        await state.clear()
        await message.reply(
            _("✅ Daylight hours updated to {start}:00 – {end}:00").format(
                start=f"{start_hour:02d}",
                end=f"{end_hour:02d}",
            )
        )

    except ValueError as e:
        logger.info(
            "Invalid daylight-hours input from user %s: %s", user.id, message.text
        )
        await message.reply(_("❌ Error: {err}. Please try again:").format(err=str(e)))
