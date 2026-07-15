# FinSight Agent — Future Plan

> Roadmap for upgrading this project into **FinSight Agent** — an autonomous regulatory & market intelligence agent for Indian fintech (RBI circulars, NPCI/UPI data, payments market).
>
> Demo query to build toward: *"What are RBI's latest guidelines for payment aggregators, and how do they affect UPI-first companies?"*

---

## Plan A — 1–2 Weeks

### A1. Core correctness & restructure (Days 1–3)
- [ ] Split `research_agent.py` into a package: `src/finsight/` (`schemas.py`, `state.py`, `config.py`, `nodes.py`, `graph.py`, `tools.py`, `prompts.py`, `cli.py`)
- [ ] Replace all manual JSON parsing (` ```json ` fence splitting, `response.content[-1]['text']`) with Pydantic models + `llm.with_structured_output()`
- [ ] Fix state-duplication bugs:
  - [ ] Nodes return only the keys they change — never `{**state, ...}` (currently re-appends all notes through the `operator.add` reducer on every node pass)
  - [ ] Add `pending_questions` to state — planner writes only new questions, researcher consumes & clears it (stops re-searching answered questions; ~50–70% API cost cut per run)
- [ ] Add try/except + graceful fallbacks in critic/writer nodes (parse failure → default "complete", not crash)
- [ ] Config via `pydantic-settings` + `.env`; validate API keys at startup
- [ ] Typer CLI: `finsight research "query" --domain regulatory --max-iterations 3 -o report.md` with `rich` progress output
- [ ] Housekeeping: `.env.example`, pinned `requirements.txt` (add missing `python-dotenv`, plus `pydantic-settings`, `typer`, `rich`), `pyproject.toml`

### A2. Tests + CI (Days 3–4)
- [ ] pytest: schema validation tests; node tests with mocked LLM/Tavily
- [ ] Named regression test for the duplication bug (2 loop iterations → assert note count, no re-searched questions)
- [ ] Graph routing + iteration-cap tests
- [ ] GitHub Actions: ruff + pytest matrix (Python 3.11/3.12), CI badge in README

### A3. Fintech specialization (Days 5–6) — the differentiator
- [ ] Domain profiles: `regulatory` / `market` / `general`, selected by CLI flag or cheap classifier
- [ ] Curated Tavily `include_domains`:
  - Regulatory → rbi.org.in, npci.org.in, sebi.gov.in, pib.gov.in
  - Market → livemint.com, economictimes.indiatimes.com, moneycontrol.com, medianama.com, inc42.com, entrackr.com
- [ ] Fintech prompt templates: regulatory planner covers circular text / effective dates / affected entities (PA/PG/PPI) / compliance timelines; writer adds "Regulatory Implications" + "Compliance Timeline" sections and cites circular number + date
- [ ] Commit 2–3 example reports in `examples/` (e.g., RBI PA guidelines impact; UPI market-share trends)
- [ ] Rebrand repo: tagline + README hero section

### A4. Observability + cost tracking (Day 7)
- [ ] Replace prints with structured `logging` (node, iteration, question context)
- [ ] LangSmith tracing (env-var opt-in) + traced-run screenshot in README
- [ ] Token/cost tracking from `usage_metadata` per node → end-of-run summary table + cost footer in every report

### A5. Minimal eval harness (Days 8–9)
- [ ] `evals/questions.yaml` — 6–8 fintech research questions with expected-coverage keywords
- [ ] `evals/run_evals.py` — LLM-as-judge (gemini-flash) scores coverage, citation presence, citation faithfulness, structure → `results.json` + Markdown score table in README

### A6. API, Docker, README polish (Days 9–10)
- [ ] FastAPI `POST /research` with SSE streaming of LangGraph node events via `graph.astream()`
- [ ] Slim non-root `Dockerfile`; `docker run` one-liner works with `.env`
- [ ] README overhaul: Mermaid diagram (with `pending_questions` flow), terminal-recording GIF, "Engineering highlights" section naming the bugs fixed and why, eval + cost tables, sample-report links

**Deliberately cut from Plan A:** Streamlit UI, RAG, checkpointing, multi-model — deferred to Plan B.

---

## Plan B — 3+ Weeks (superset of Plan A)

### B1. RAG over RBI documents (Week 3, ~4 days) — highest-value differentiator
- [ ] `finsight ingest ./docs/` — load RBI circular/master-direction PDFs (pypdf), chunk with metadata (circular no., date, title), embed, store in Chroma (persisted)
- [ ] Hybrid researcher: structured-output router picks web search vs. document retrieval vs. both per sub-question; notes tagged `web` / `document:circular-no`
- [ ] Ship 8–10 pre-ingested RBI PDFs (PA guidelines, digital lending, PPI master directions, tokenization) so the demo works instantly
- [ ] Writer cites circulars by number/date/paragraph

### B2. Parallel research + fact-checker (Weeks 3–4, ~4 days)
- [ ] Parallel researcher fan-out with LangGraph `Send` API (one researcher per sub-question concurrently) — benchmark 3–5× latency win, before/after in README
- [ ] Fact-checker node before writer: extract claims (structured output), verify each against stored source snippets, flag unsupported claims; writer drops/hedges them; report gets a "N/M claims grounded" badge

### B3. Persistence, human-in-the-loop, resilience (Week 4, ~3 days)
- [ ] `SqliteSaver` checkpointer + `thread_id`; `finsight resume <thread-id>`
- [ ] `interrupt()` before researcher (flag-gated `--interactive`) — human reviews/edits the plan
- [ ] `tenacity` retry/backoff on LLM + Tavily calls; `diskcache` search cache keyed on (query, profile) with TTL

### B4. Eval suite v2 + benchmarks (Week 5, ~2–3 days)
- [ ] Expand to 15–20 questions across domain profiles
- [ ] Computed grounding-precision metric from the B2 fact-checker (claims-supported ratio)
- [ ] Cost/latency/quality benchmark: gemini-pro vs gemini-flash, sequential vs parallel — table + chart in README
- [ ] Optional: nightly 3-question smoke eval in GitHub Actions

### B5. Deployment + demo UI (Week 5, ~2–3 days)
- [ ] Minimal Streamlit front-end (query box, domain selector, live node progress, rendered report + cost footer)
- [ ] Deploy to Hugging Face Spaces (Docker Space); live demo link atop README; per-session rate limiting / API budget cap
- [ ] Optional flourish (strictly last): NPCI UPI monthly-stats parser tool for the market profile

**Cut from Plan B:** multi-provider abstraction layers, K8s/Terraform, auth systems, equity-data tools, framework migrations.

---

## Resume pitch lines

**Plan B version:**
> Built **FinSight**, an autonomous multi-agent research system (LangGraph, Gemini) for Indian fintech regulatory & market intelligence — hybrid RAG over RBI circulars + curated web search, parallel researcher fan-out, claim-level citation verification, LLM-as-judge eval suite, and per-run cost tracking; shipped with CI, Docker, streaming FastAPI, and a live demo.

**Plan A version:**
> Built an autonomous LangGraph research agent specialized for Indian fintech regulation (RBI/NPCI sources) — structured LLM outputs, iterative plan-critique loops, eval harness with citation-faithfulness scoring, cost tracking, tests + CI, Docker, and a streaming FastAPI endpoint.

**README tagline:** *FinSight Agent — an autonomous research analyst for Indian fintech. Ask it about RBI regulation or the payments market; get back a verified, cited report — with the exact cost of producing it.*

---

## Sequencing rationale
1. **A1 first** — every later phase touches nodes/state; the fintech skin on top of the duplication bug means slow, expensive demos with bloated reports
2. **Tests before fintech prompts** — locks in bug fixes so prompt iteration can't silently regress them
3. **Evals after fintech** — eval questions should be domain questions (write them once)
4. **B1 (RAG) first in Plan B** — biggest differentiator per day; also gives B2's fact-checker primary sources to ground against