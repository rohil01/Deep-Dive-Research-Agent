"""Shared LangGraph state for the research agent."""
import operator
from typing import Annotated, List, TypedDict


class ResearchState(TypedDict):
    """The shared state that flows through all nodes.

    Reducer semantics matter here:
    - `notes` and `plan` use `operator.add`, so nodes must return ONLY the
      new items to append — never the full accumulated list.
    - All other keys are plain overwrites; nodes return only the keys they
      actually change (never `{**state, ...}`).
    """

    query: str                                       # Original user query
    plan: Annotated[List[str], operator.add]         # All sub-questions so far (accumulates)
    pending_questions: List[str]                     # Work queue: questions not yet researched
    notes: Annotated[List[dict], operator.add]       # Research findings (accumulates)
    iteration: int                                   # Loop counter
    critique: str                                    # Feedback from critic
    final_report: str                                # Final output
    should_continue: bool                            # Control flag
