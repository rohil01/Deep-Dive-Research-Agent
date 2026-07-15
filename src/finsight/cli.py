"""Typer CLI for the FinSight research agent."""
import logging
import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer(
    name="finsight",
    help="Autonomous cyclic research agent (LangGraph + Gemini + Tavily).",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
    )
    # Quiet noisy third-party loggers unless verbose
    if not verbose:
        for name in ("httpx", "urllib3", "langchain", "google"):
            logging.getLogger(name).setLevel(logging.WARNING)


@app.command()
def research(
    query: str = typer.Argument(..., help="The research question to investigate"),
    output: Path = typer.Option(
        Path("research_report.md"), "--output", "-o", help="Path for the Markdown report"
    ),
    max_iterations: Optional[int] = typer.Option(
        None, "--max-iterations", help="Max plan→research→critique loops (default from config)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Gemini model id (default from config)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logging"),
) -> None:
    """Run the research agent on QUERY and save a cited Markdown report."""
    load_dotenv()
    _setup_logging(verbose)

    # CLI flags override environment/config values
    if max_iterations is not None:
        os.environ["MAX_ITERATIONS"] = str(max_iterations)
    if model is not None:
        os.environ["MODEL_NAME"] = model

    # Import after env overrides so cached Settings pick them up
    from .config import get_settings
    from .graph import run_research

    try:
        get_settings().validate_keys()
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold]FinSight Research Agent[/bold]\n[dim]{query}[/dim]",
            border_style="cyan",
        )
    )

    with console.status("[cyan]Researching...", spinner="dots"):
        report = run_research(query)

    console.print("\n[bold green]Research completed[/bold green]\n")
    console.print(Markdown(report))

    output.write_text(report, encoding="utf-8")
    console.print(f"\n[dim]Report saved to[/dim] [bold]{output}[/bold]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
