"""Stateless brief parsing endpoint."""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.ai.brief_parser import BriefParseResponse, parse_brief

router = APIRouter(prefix="/briefs", tags=["briefs"])


class ParseBriefRequest(BaseModel):
    raw_text: str = Field(..., min_length=3, description="Unstructured celebration brief")


@router.post("/parse", response_model=BriefParseResponse, status_code=status.HTTP_200_OK)
def parse_brief_endpoint(payload: ParseBriefRequest) -> BriefParseResponse:
    """Parse unstructured celebration brief into structured EventBrief and clarifying questions."""
    return parse_brief(raw_text=payload.raw_text)
