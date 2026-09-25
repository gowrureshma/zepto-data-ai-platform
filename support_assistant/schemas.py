from pydantic import BaseModel, Field
from typing import List


class AnswerResponse(BaseModel):
    """Validated structured answer returned by the Support Assistant."""

    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
