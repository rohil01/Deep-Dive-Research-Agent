"""Pydantic models for structured LLM outputs.

Every LLM call in the agent goes through `llm.with_structured_output(Model)`
with one of these schemas — no manual JSON-fence parsing anywhere.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Output of the planner node: a list of researchable sub-questions."""

    sub_questions: List[str] = Field(
        description="Specific, concrete, researchable sub-questions",
        min_length=1,
    )


class SearchAnalysis(BaseModel):
    """Output of the researcher's analysis step for one sub-question."""

    sufficient: bool = Field(
        description="Whether the search results adequately answer the sub-question"
    )
    summary: str = Field(description="Brief summary of the findings")
    needs_scraping: bool = Field(
        default=False,
        description="Whether a page should be scraped for more detail",
    )
    url_to_scrape: Optional[str] = Field(
        default=None,
        description="URL to scrape if needs_scraping is true, else null",
    )


class Critique(BaseModel):
    """Output of the critic node: completeness verdict plus gap feedback."""

    is_complete: bool = Field(
        description="Whether the research adequately answers the original query"
    )
    feedback: str = Field(
        description="Specific gaps to address, or 'Research is complete'"
    )
    missing_aspects: List[str] = Field(
        default_factory=list,
        description="Aspects of the query not yet covered",
    )
