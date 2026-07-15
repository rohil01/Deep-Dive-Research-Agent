"""All prompt templates for the research agent, in one place."""

INITIAL_PLAN_PROMPT = """You are a research planner. Break down this query into 3-5 specific, \
researchable sub-questions. Make them concrete and answerable.

Query: {query}"""

REPLAN_PROMPT = """You are a research planner. The previous research was incomplete.

Original Query: {query}
Critique: {critique}

Questions already researched (do NOT repeat these):
{existing_questions}

Create 2-3 additional specific sub-questions to address the gaps."""

SEARCH_ANALYSIS_PROMPT = """Analyze these search results for the question: "{sub_question}"

Search Results:
{search_results}

Assess whether the results sufficiently answer the question, summarize the findings, \
and decide whether one of the result URLs should be scraped for more detail."""

CRITIQUE_PROMPT = """You are a research quality critic. Evaluate if the gathered research \
adequately answers the original query.

Original Query: {query}
Iteration: {iteration}

Research Gathered:
{notes_summary}

Be strict but fair. Identify specific gaps if the research is incomplete."""

WRITER_PROMPT = """You are a research writer. Create a comprehensive, well-structured Markdown report.

Original Query: {query}

Research Gathered:
{research_content}

Write a professional report with:
1. Executive Summary
2. Key Findings (organized by theme)
3. Detailed Analysis
4. Citations (include URLs from sources)
5. Conclusion

Use proper Markdown formatting."""
