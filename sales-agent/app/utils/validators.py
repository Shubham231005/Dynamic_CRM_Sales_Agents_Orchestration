from typing import Dict, Any
from app.schemas.lead import LeadCreate
from pydantic import ValidationError
import logging
logger = logging.getLogger(__name__)

def validate_lead_data(data: Dict[str, Any]) -> LeadCreate | None:
    """
    Validates a raw dictionary using the LeadCreate Pydantic schema.
    Returns the validated LeadCreate object, or None if validation fails.
    """
    try:
        validated_lead = LeadCreate(**data)
        return validated_lead
    except ValidationError as e:
        # We could log the validation error here
        # logger.warning(f"Validation failed for lead {data.get('company_name')}: {e}")
        return None
