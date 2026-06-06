"""
ChaosProbe CLI commands.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import httpx

from chaosProbe.engine.experiment import Experiment
from chaosProbe.engine.orchestrator import Orchestrator
from chaosProbe.monitoring.prometheus_client import PrometheusClient
from chaosProbe.monitoring.slo_monitor import SLOMonitor
from chaosProbe.utils.config import settings
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(
    name="chaosctl",
    help="ChaosProbe — Chaos Engineering Framework",
    add_completion=False,
)


def _verdict_color(verdict: str) -> str:
    colors = {
        "passed": "green",
        "failed": "red",
        "aborted": "yellow",
        "running": "blue",
        "pending": "white",
    }
    return colors.get(verdict.lower(), "white")


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", help="Path to experiment YAML"),
    api: bool = typer.Option(False, "--api", help="Run via API instead of directly"),
    api_url: str = typer.Option("http://localhost:8080", "--api-url", help="API base URL"),
):
    """Run a chaos experiment from a YAML config file."""
    if not config.exists():
        console.print(f"[red]Config file not found: {config}[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold cyan]ChaosProbe[/bold cyan] — Loading experiment\n[dim]{config}[/dim]",
        box=box.ROUNDED,
    ))

    if api:
        _run_via_api(config, api_url)
    else:
        _run_direct(config)


def _run_direct(config: Path) -> None:
    """Run experiment directly without API."""
    try:
        experiment = Experiment.from_yaml(str(config))
        console.print(f"[bold]Experiment:[/bold] {experiment.name}")
        console.print(f"[bold]Fault:[/bold] {experiment.fault.fault_type} → {experiment.fault.target}")
        console.print(f"[bold]Duration:[/bold] {experiment.fault.duration_seconds}s\n")

        prom = PrometheusClient(base_url=settings.prometheus_url)
        slo_monitor = SLOMonitor(prometheus_client=prom)
        orchestrator = Orchestrator(slo_monitor=slo_monitor)

        with console.status("[bold green]Running experiment...[/bold green]"):
            run_result = orchestrator.run(experiment)

        _print_result(run_result.to_dict())

    except Exception as exc:
        console.print(f"[red]Experiment failed: {exc}[/red]")
        raise typer.Exit(1)


def _run_via_api(config: Path, api_url: str) -> None:
    """Run experiment via REST API."""
    import yaml
    with open(config) as f:
        data = yaml.safe_load(f)

    try:
        with httpx.Client(timeout=300) as client:
            resp = client.post(f"{api_url}/api/v1/experiments/run", json=data)
            resp.raise_for_status()
            _print_result(resp.json())
    except Exception as exc:
        console.print(f"[red]API request failed: {exc}[/red]")
        raise typer.Exit(1)


def _print_result(result: dict) -> None:
    verdict = result.get("verdict", "unknown")
    color = _verdict_color(verdict)
    duration = result.get("duration_seconds")
    duration_str = f"{duration:.1f}s" if duration else "N/A"

    console.print(Panel(
        f"[bold {color}]VERDICT: {verdict.upper()}[/bold {color}]\n"
        f"ID: [dim]{result.get('experiment_id', 'N/A')}[/dim]\n"
        f"Duration: {duration_str}\n"
        f"SLO Breached: {result.get('slo_breached', False)}",
        title="Experiment Result",
        box=box.ROUNDED,
        border_style=color,
    ))

    # Timeline
    timeline = result.get("timeline", [])
    if timeline:
        console.print("\n[bold]Timeline:[/bold]")
        for event in timeline:
            console.print(f"  [dim]{event.get('event', '')}[/dim]")


@app.command()
def list(
    api_url: str = typer.Option("http://localhost:8080", "--api-url", help="API base URL"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
):
    """List past experiment runs."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{api_url}/api/v1/experiments?limit={limit}")
            resp.raise_for_status()
            runs = resp.json()
    except Exception as exc:
        console.print(f"[red]Failed to fetch experiments: {exc}[/red]")
        raise typer.Exit(1)

    if not runs:
        console.print("[yellow]No experiments found.[/yellow]")
        return

    table = Table(title="Experiment Runs", box=box.ROUNDED)
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name")
    table.add_column("Verdict")
    table.add_column("Duration")
    table.add_column("SLO Breached")

    for r in runs:
        verdict = r.get("verdict", "unknown")
        color = _verdict_color(verdict)
        duration = r.get("duration_seconds")
        duration_str = f"{duration:.1f}s" if duration else "N/A"
        table.add_row(
            r.get("experiment_id", "")[:8] + "...",
            r.get("experiment_name", ""),
            f"[{color}]{verdict.upper()}[/{color}]",
            duration_str,
            "Yes" if r.get("slo_breached") else "No",
        )

    console.print(table)


@app.command()
def report(
    id: str = typer.Option(..., "--id", help="Experiment ID"),
    api_url: str = typer.Option("http://localhost:8080", "--api-url", help="API base URL"),
):
    """Get detailed report for an experiment."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{api_url}/api/v1/experiments/{id}")
            resp.raise_for_status()
            result = resp.json()
    except Exception as exc:
        console.print(f"[red]Failed to fetch experiment: {exc}[/red]")
        raise typer.Exit(1)

    _print_result(result)

    # Pre checks
    console.print("\n[bold]Pre-experiment checks:[/bold]")
    for check in result.get("pre_checks", []):
        icon = "✓" if check.get("passed") else "✗"
        color = "green" if check.get("passed") else "red"
        console.print(f"  [{color}]{icon}[/{color}] {check.get('name')} — {check.get('detail')}")

    # Post checks
    console.print("\n[bold]Post-experiment checks:[/bold]")
    for check in result.get("post_checks", []):
        icon = "✓" if check.get("passed") else "✗"
        color = "green" if check.get("passed") else "red"
        console.print(f"  [{color}]{icon}[/{color}] {check.get('name')} — {check.get('detail')}")


@app.command()
def status(
    api_url: str = typer.Option("http://localhost:8080", "--api-url", help="API base URL"),
):
    """Check ChaosProbe API status."""
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{api_url}/health")
            resp.raise_for_status()
            data = resp.json()
        console.print(f"[green]✓ ChaosProbe API is healthy[/green]")
        console.print(f"  Version: {data.get('version')}")
        console.print(f"  Environment: {data.get('environment')}")
    except Exception:
        console.print(f"[red]✗ ChaosProbe API is not reachable at {api_url}[/red]")
        raise typer.Exit(1)