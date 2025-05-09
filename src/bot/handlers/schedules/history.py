from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.schedule_service import ScheduleService

router = Router()


async def format_adherence_report(stats: dict) -> str:
    report = [hbold("📅 Medication Adherence Report:")]

    for drug, data in stats.items():
        report.append(
            f"💊 {hbold(drug)} ({data['dose']}):\n"
            f"   ✅ Taken: {data['taken']}/{data['total']} ({data['percentage']}%)\n"
            f"   ⏰ On Time: {data['on_time']}\n"
            f"   🕒 Late: {data['late']}\n"
            f"   ❌ Missed: {data['missed']}"
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
        await message.answer("Invalid input. Please provide a valid number of days.")
        return
    if days <= 0:
        await message.answer("Please specify a positive number of days")
        return
    if days > 365:
        await message.answer("Maximum history period is 1 year (365 days)")
        return

    service = ScheduleService(session)
    stats = await service.get_adherence_stats(user.id, days)

    if not stats:
        await message.answer(f"No medication history found for the last {days} days")
        return

    response = await format_adherence_report(stats)
    await message.answer(response, parse_mode="HTML")
