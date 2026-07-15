"""Graph nodes: planner, researcher, critic, writer.

Node contract: each node returns ONLY the state keys it changes. Keys with
an `operator.add` reducer (`plan`, `notes`) receive just the NEW items to
append — returning `{**state, ...}` would duplicate accumulated values.
"""
import json
import logging

from langchain_core.messages import HumanMessage

from . import prompts
from .config import get_settings
from .schemas import Critique, ResearchPlan, SearchAnalysis
from .state import ResearchState
from .tools import get_llm, get_search_tool, scrape_url

logger = logging.getLogger(__name__)


def _response_text(response) -> str:
    """Extract plain text from an LLM response, whatever shape content takes."""
    content = response.content
    if isinstance(content, str):
        return content.strip()
    # List of content blocks (dicts or strings)
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("text"):
            parts.append(block["text"])
    return "\n".join(parts).strip()


# ==================== NODE 1: THE PLANNER ====================
def planner_node(state: ResearchState) -> dict:
    """Breaks the query into sub-questions; on re-entry, plans only the gaps."""
    logger.info("[PLANNER] Creating research plan (iteration %d)", state.get("iteration", 0) + 1)

    query = state["query"]
    critique = state.get("critique", "")
    existing_plan = state.get("plan", [])

    if critique and existing_plan:
        prompt = prompts.REPLAN_PROMPT.format(
            query=query,
            critique=critique,
            existing_questions="\n".join(f"- {q}" for q in existing_plan),
        )
    else:
        prompt = prompts.INITIAL_PLAN_PROMPT.format(query=query)

    planner_llm = get_llm().with_structured_output(ResearchPlan)

    try:
        plan: ResearchPlan = planner_llm.invoke([HumanMessage(content=prompt)])
        # Guard against the model repeating already-researched questions
        seen = set(existing_plan)
        new_questions = [q for q in plan.sub_questions if q not in seen]
    except Exception as e:
        logger.error("[PLANNER] Failed to generate plan: %s", e)
        new_questions = []

    logger.info("[PLANNER] %d new sub-questions", len(new_questions))
    for i, q in enumerate(new_questions, 1):
        logger.info("  %d. %s", i, q)

    return {
        "plan": new_questions,               # appended to plan via reducer
        "pending_questions": new_questions,  # work queue for the researcher
        "iteration": state.get("iteration", 0) + 1,
    }


# ==================== NODE 2: THE RESEARCHER ====================
def researcher_node(state: ResearchState) -> dict:
    """Researches ONLY the pending questions (not previously answered ones)."""
    pending = state.get("pending_questions", [])
    logger.info("[RESEARCHER] Gathering information for %d question(s)", len(pending))

    llm = get_llm()
    analysis_llm = llm.with_structured_output(SearchAnalysis)
    search_tool = get_search_tool()
    gathered_notes = []

    for idx, sub_question in enumerate(pending, 1):
        logger.info("[RESEARCHER] (%d/%d) %s", idx, len(pending), sub_question)

        try:
            # Step 1: Search
            search_results = search_tool.invoke(sub_question)

            # Step 2: Analyze sufficiency + scraping need (structured output)
            analysis: SearchAnalysis = analysis_llm.invoke(
                [
                    HumanMessage(
                        content=prompts.SEARCH_ANALYSIS_PROMPT.format(
                            sub_question=sub_question,
                            search_results=json.dumps(search_results, indent=2, default=str),
                        )
                    )
                ]
            )

            note = {
                "question": sub_question,
                "search_results": search_results,
                "summary": analysis.summary,
                "sufficient": analysis.sufficient,
            }

            # Step 3: Scrape if the analysis asked for it
            if analysis.needs_scraping and analysis.url_to_scrape:
                logger.info("[RESEARCHER] Scraping: %s", analysis.url_to_scrape)
                note["scraped_content"] = scrape_url(analysis.url_to_scrape)

            gathered_notes.append(note)
            logger.info("[RESEARCHER] Summary: %.100s...", analysis.summary)

        except Exception as e:
            logger.error("[RESEARCHER] Error on %r: %s", sub_question, e)
            gathered_notes.append(
                {"question": sub_question, "error": str(e), "sufficient": False}
            )

    return {
        "notes": gathered_notes,   # appended via reducer
        "pending_questions": [],   # queue consumed
    }


# ==================== NODE 3: THE CRITIC ====================
def critic_node(state: ResearchState) -> dict:
    """Checks completeness; loops back with feedback or approves."""
    logger.info("[CRITIC] Evaluating research quality...")

    query = state["query"]
    notes = state["notes"]
    iteration = state["iteration"]
    max_iterations = get_settings().max_iterations

    notes_summary = "\n\n".join(
        f"Question: {note['question']}\n"
        f"Summary: {note.get('summary', 'No summary')}\n"
        f"Sufficient: {note.get('sufficient', False)}"
        for note in notes
    )

    critic_llm = get_llm().with_structured_output(Critique)

    try:
        critique: Critique = critic_llm.invoke(
            [
                HumanMessage(
                    content=prompts.CRITIQUE_PROMPT.format(
                        query=query, iteration=iteration, notes_summary=notes_summary
                    )
                )
            ]
        )
        feedback = critique.feedback
        is_complete = critique.is_complete
    except Exception as e:
        # Fail open: a broken critique should end the run with a report,
        # not crash it.
        logger.error("[CRITIC] Critique failed (%s); treating research as complete", e)
        feedback = "Critique unavailable — proceeding with gathered research."
        is_complete = True

    is_complete = is_complete or iteration >= max_iterations

    if is_complete:
        logger.info("[CRITIC] Research quality approved")
    else:
        logger.info("[CRITIC] Incomplete. Feedback: %s", feedback)

    return {
        "critique": feedback,
        "should_continue": not is_complete,
    }


# ==================== NODE 4: THE WRITER ====================
def writer_node(state: ResearchState) -> dict:
    """Synthesizes all notes into a cited Markdown report."""
    logger.info("[WRITER] Composing final report...")

    query = state["query"]
    notes = state["notes"]

    research_content = ""
    for i, note in enumerate(notes, 1):
        research_content += f"\n## Research Point {i}\n"
        research_content += f"**Question:** {note['question']}\n"
        research_content += f"**Summary:** {note.get('summary', 'N/A')}\n"
        if note.get("search_results"):
            research_content += (
                f"**Sources:** {json.dumps(note['search_results'], indent=2, default=str)}\n"
            )
        if note.get("scraped_content"):
            research_content += f"**Additional Details:** {note['scraped_content'][:500]}...\n"

    try:
        response = get_llm().invoke(
            [
                HumanMessage(
                    content=prompts.WRITER_PROMPT.format(
                        query=query, research_content=research_content
                    )
                )
            ]
        )
        final_report = _response_text(response)
    except Exception as e:
        logger.error("[WRITER] Report generation failed: %s", e)
        final_report = (
            f"# Research Report (generation failed)\n\n"
            f"**Query:** {query}\n\n"
            f"Report synthesis failed ({e}). Raw research summaries:\n"
            + "\n".join(f"- **{n['question']}**: {n.get('summary', 'N/A')}" for n in notes)
        )

    logger.info("[WRITER] Report completed")

    return {
        "final_report": final_report,
        "should_continue": False,
    }
