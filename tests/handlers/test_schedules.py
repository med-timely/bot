from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext

from src.bot.handlers.schedules import create
from src.models import User


@pytest.mark.asyncio
async def test_schedule_flow(dp, bot, session, user_data, event_loop):
    print("Starting test_schedule_flow")
    try:
        # Setup test user
        user = User(**user_data)
        session.add(user)
        await session.commit()
        print("Test user setup complete")

        # Start schedule command
        message = AsyncMock()
        message.chat = user_data["telegram_id"]
        message.text = "/schedule"

        await create.start_schedule(
            message, FSMContext(dp.storage, user_data["telegram_id"]), user
        )
        print("start_schedule completed")

        # Check state and message
        state = await dp.storage.get_state(user_data["telegram_id"])
        print(f"State after start_schedule: {state}")
        assert state == "ScheduleStates:waiting_drug_name"

        # Process drug name
        message.text = "Aspirin"
        await create.process_drug_name(
            message, FSMContext(dp.storage, user_data["telegram_id"]), session
        )
        print("process_drug_name completed")
        state = await dp.storage.get_state(user_data["telegram_id"])
        print(f"State after process_drug_name: {state}")
        assert state == "ScheduleStates:waiting_dose"
    except Exception as e:
        print(f"Error in test_schedule_flow: {e}")
        raise


# @pytest.mark.asyncio
# async def test_invalid_frequency_handling(dp, bot, session, user_data):
#     user = User(**user_data)
#     session.add(user)
#     await session.commit()

#     # Start flow until frequency step
#     state = FSMContext(dp.storage, user_data["telegram_id"], None)
#     await state.set_state(create.ScheduleStates.waiting_frequency)
#     await state.update_data(drug_name="Aspirin", dose="100mg")

#     # Send invalid frequency
#     message = Message(chat=user_data["telegram_id"], text="invalid")
#     await create.process_frequency(message, state)

#     # Should remain in same state
#     current_state = await state.get_state()
#     assert current_state == "ScheduleStates:waiting_frequency"
