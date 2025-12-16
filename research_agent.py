from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_tavily import TavilySearch
from langchain_community.document_loaders import WebBaseLoader
import json
import operator
import os
from dotenv import load_dotenv

load_dotenv()


class ResearchState(TypedDict):
    """The shared state that flows through all nodes"""
    query: str                                          # Original user query
    plan: List[str]                                     # List of sub-questions
    notes: Annotated[List[dict], operator.add]         # Research findings (accumulates)
    iteration: int                                      # Loop counter
    critique: str                                       # Feedback from critic
    final_report: str                                   # Final output
    should_continue: bool                               # Control flag


llm = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")
search_tool = TavilySearch(max_results=3)


# ==================== NODE 1: THE PLANNER ====================
def planner_node(state: ResearchState) -> ResearchState:
    """
    Breaks down the user query into specific sub-questions.
    If there's critique feedback, creates additional questions.
    """
    print("\n🧠 [PLANNER] Creating research plan...")
    
    query = state["query"]
    critique = state.get("critique", "")
    iteration = state.get("iteration", 0)
    
    if critique:
        # Iterative planning based on feedback
        prompt = f"""You are a research planner. The previous research was incomplete.
        
Original Query: {query}
Critique: {critique}

Create 2-3 additional specific sub-questions to address the gaps.
Return ONLY a JSON array of strings. Example: ["question 1", "question 2"]"""
    else:
        # Initial planning
        prompt = f"""You are a research planner. Break down this query into 3-5 specific, 
researchable sub-questions. Make them concrete and answerable.

Query: {query}

Return ONLY a JSON array of strings. Example: ["question 1", "question 2"]"""
    
    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)

    try:
        content = response.content[-1]['text'].strip() 
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        new_plan = json.loads(content)
        
        # Append to existing plan if iterating
        existing_plan = state.get("plan", [])
        full_plan = existing_plan + new_plan if critique else new_plan
        
        print(f"📋 Plan created: {len(new_plan)} new sub-questions")
        for i, q in enumerate(new_plan, 1):
            print(f"   {i}. {q}")
        
        return {
            **state,
            "plan": full_plan,
            "iteration": iteration + 1
        }
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return {**state, "plan": state.get("plan", [])}


def researcher_node(state: ResearchState) -> ResearchState:
    """
    Executes searches for each sub-question.
    Optionally scrapes websites if results are vague.
    """
    print("\n🔍 [RESEARCHER] Gathering information...")
    
    plan = state["plan"]
    gathered_notes = []
    
    for idx, sub_question in enumerate(plan, 1):
        print(f"\n📌 Researching ({idx}/{len(plan)}): {sub_question}")
        
        try:
            # Step 1: Search
            search_results = search_tool.invoke(sub_question)
            
            # Analyze search results
            analysis_prompt = f"""Analyze these search results for the question: "{sub_question}"

Search Results:
{json.dumps(search_results, indent=2)}

Respond with JSON:
{{
    "sufficient": true/false,
    "summary": "brief summary of findings",
    "needs_scraping": true/false,
    "url_to_scrape": "url if needs scraping, else null"
}}"""
            
            analysis_response = llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis_content = analysis_response.content[-1]['text'].strip()
            
            # Clean JSON
            if "```json" in analysis_content:
                analysis_content = analysis_content.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_content:
                analysis_content = analysis_content.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(analysis_content)
            
            note = {
                "question": sub_question,
                "search_results": search_results,
                "summary": analysis["summary"],
                "sufficient": analysis["sufficient"]
            }
            
            # Step 2: Scrape if needed
            if analysis.get("needs_scraping") and analysis.get("url_to_scrape"):
                url = analysis["url_to_scrape"]
                print(f"   🌐 Scraping: {url}")
                
                try:
                    loader = WebBaseLoader(url)
                    docs = loader.load()
                    note["scraped_content"] = docs[0].page_content[:2000]  # First 2000 chars
                    print("   ✓ Scraping successful")
                except Exception as e:
                    print(f"   ⚠️ Scraping failed: {e}")
                    note["scraped_content"] = None
            
            gathered_notes.append(note)
            print(f"   ✓ Summary: {analysis['summary'][:100]}...")
            
        except Exception as e:
            print(f"   ❌ Research error: {e}")
            gathered_notes.append({
                "question": sub_question,
                "error": str(e),
                "sufficient": False
            })
    
    return {
        **state,
        "notes": gathered_notes
    }


# ==================== NODE 3: THE CRITIC ====================
def critic_node(state: ResearchState) -> ResearchState:
    """
    Quality control: Checks if research is complete.
    Provides feedback if information is missing.
    """
    print("\n🎯 [CRITIC] Evaluating research quality...")
    
    query = state["query"]
    notes = state["notes"]
    iteration = state["iteration"]
    
    # Format notes for analysis
    notes_summary = "\n\n".join([
        f"Question: {note['question']}\nSummary: {note.get('summary', 'No summary')}\nSufficient: {note.get('sufficient', False)}"
        for note in notes
    ])
    
    critique_prompt = f"""You are a research quality critic. Evaluate if the gathered research adequately answers the original query.

Original Query: {query}
Iteration: {iteration}

Research Gathered:
{notes_summary}

Respond with JSON:
{{
    "is_complete": true/false,
    "feedback": "specific gaps or 'Research is complete'",
    "missing_aspects": ["aspect 1", "aspect 2"] or []
}}

Be strict but fair. After 3 iterations, be more lenient."""
    
    response = llm.invoke([HumanMessage(content=critique_prompt)])
    content = response.content[-1]['text'].strip()
    
    # Clean JSON
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    critique = json.loads(content)
    
    is_complete = critique["is_complete"] or iteration >= 3  # Max 3 iterations
    
    if is_complete:
        print("✅ Research quality approved!")
    else:
        print(f"⚠️ Research incomplete. Feedback: {critique['feedback']}")
    
    return {
        **state,
        "critique": critique["feedback"],
        "should_continue": not is_complete
    }


def writer_node(state: ResearchState) -> ResearchState:
    """
    Synthesizes research into a final Markdown report with citations.
    """
    print("\n📝 [WRITER] Composing final report...")
    
    query = state["query"]
    notes = state["notes"]
    
    # Format notes for the writer
    research_content = ""
    for i, note in enumerate(notes, 1):
        research_content += f"\n## Research Point {i}\n"
        research_content += f"**Question:** {note['question']}\n"
        research_content += f"**Summary:** {note.get('summary', 'N/A')}\n"
        
        if note.get('search_results'):
            research_content += f"**Sources:** {json.dumps(note['search_results'], indent=2)}\n"
        
        if note.get('scraped_content'):
            research_content += f"**Additional Details:** {note['scraped_content'][:500]}...\n"
    
    writer_prompt = f"""You are a research writer. Create a comprehensive, well-structured Markdown report.

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
    
    response = llm.invoke([HumanMessage(content=writer_prompt)])
    final_report = response.content[-1]['text'].strip()
    
    print("✅ Report completed!")
    
    return {
        **state,
        "final_report": final_report,
        "should_continue": False
    }


# ==================== CONDITIONAL EDGE ====================
def should_continue_research(state: ResearchState) -> str:
    """
    Decides whether to loop back to planner or proceed to writer.
    """
    if state.get("should_continue", False):
        print("\n🔄 Looping back to planner for additional research...")
        return "planner"
    else:
        print("\n➡️ Proceeding to writer...")
        return "writer"


# ==================== BUILD THE GRAPH ====================
def create_research_graph():
    """
    Constructs the LangGraph state machine.
    """
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("writer", writer_node)
    
    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "critic")
    
    # Conditional edge: critic decides to loop or finish
    workflow.add_conditional_edges(
        "critic",
        should_continue_research,
        {
            "planner": "planner",  # Loop back
            "writer": "writer"     # Finish
        }
    )
    
    workflow.add_edge("writer", END)
    
    return workflow.compile()


# ==================== MAIN EXECUTION ====================
def run_research(query: str):
    """
    Execute the research agent.
    """
    print("=" * 60)
    print("🚀 CYCLIC RESEARCH AGENT STARTED")
    print("=" * 60)
    
    graph = create_research_graph()
    
    initial_state = {
        "query": query,
        "plan": [],
        "notes": [],
        "iteration": 0,
        "critique": "",
        "final_report": "",
        "should_continue": True
    }
    
    # Execute the graph
    final_state = graph.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("✅ RESEARCH COMPLETED")
    print("=" * 60)
    print("\n📄 FINAL REPORT:\n")
    print(final_state["final_report"])
    
    return final_state["final_report"]


if __name__ == "__main__":
    # Example query
    query = "Latest advancements in solid-state batteries in 2024"
    
    # Run the research agent
    report = run_research(query)
    
    # Optionally save to file
    with open("research_report.md", "w") as f:
        f.write(report)
    
    print("\n💾 Report saved to research_report.md")