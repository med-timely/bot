import json
import logging

from pydantic import BaseModel, ValidationError

from src.services.llm_service import LLMRequest, LLMService

logger = logging.getLogger(__name__)


class PrescriptionData(BaseModel):
    drug_name: str
    dose: str
    doses_per_day: int
    duration: int | None = None
    comment: str | None = None


async def parse_prescription(
    llm_service: LLMService, text: str
) -> PrescriptionData | None:
    try:
        prompt = f"""Extract medication details as JSON with keys: drug_name, dose, doses_per_day, duration, comment. For values use the same language as in the input. If some values absent - skip it in JSON.
        Example: {{"drug_name": "Aspirin", "dose": "1 tablet", "doses_per_day": 3, "duration": 7, "comment": "Take with food"}}
        DO NOT PROVIDE ANY EXPLANATION, JUST VALID JSON
        Input: "{text}" """

        response = await llm_service.complete(
            LLMRequest(prompt=prompt, temperature=0.1)
        )
        return PrescriptionData.model_validate_json(response)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM response as JSON: %s", e)
        return None
    except ValidationError as e:
        logger.warning("Failed to validate prescription data: %s", e)
        return None
    except ValueError as e:
        logger.warning("Invalid response from LLM service: %s", e)
        return None
    except Exception as e:
        logger.warning("Failed to parse prescription: %s", e)
        return None
