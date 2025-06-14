from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.markdown import hbold
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.schedule_service import ScheduleService

router = Router()


async def format_adherence_report(stats: dict) -> str:
    report = [hbold(_("📅 Medication Adherence Report:"))]

    for drug, data in stats.items():
        report.append(
            _(
                "💊 {drug} ({dose}):\n"
                "   ✅ Taken: {taken}/{total} ({percentage}%)\n"
                "   ⏰ On Time: {on_time}\n"
                "   🕒 Late: {late}\n"
                "   ❌ Missed: {missed}"
            ).format(
                drug=hbold(drug),
                dose=data["dose"],
                taken=data["taken"],
                total=data["total"],
                percentage=data["percentage"],
                on_time=data["on_time"],
                late=data["late"],
                missed=data["missed"],
            )
        )

    return "\n\n".join(report)


@router.message(Command("history"))
async def handle_history(
    message: Message, command: CommandObject, session: AsyncSession, user: User
):
    # Parse days argument
    try:
        days = int(command.args) if command.args else 7
    except ValueError:
        await message.answer(_("Invalid input. Please provide a valid number of days."))
        return
    if days <= 0:
        await message.answer(_("Please specify a positive number of days"))
        return
    if days > 365:
        await message.answer(_("Maximum history period is 1 year (365 days)"))
        return

    service = ScheduleService(session)
    stats = await service.get_adherence_stats(user.id, days)

    if not stats:
        await message.answer(
            _(
                "No medication history found for the last {days} day",
                "No medication history found for the last {days} days",
                days,
            ).format(days=days)
        )
        return

    response = await format_adherence_report(stats)
    await message.answer(response, parse_mode=ParseMode.HTML)
