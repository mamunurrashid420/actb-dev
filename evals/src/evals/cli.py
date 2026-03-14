"""CLI entry point for agent evaluations."""

import asyncio
from typing import Annotated

import typer

app = typer.Typer(
    name="eval",
    help="Agent evaluation framework CLI",
    no_args_is_help=True,
)


@app.command()
def run(
    config_name: Annotated[str, typer.Argument(help="Config name (without .yaml)")],
    sample: Annotated[
        int | None, typer.Option("--sample", "-s", help="Sample N cases from dataset")
    ] = None,
    model: Annotated[
        str | None, typer.Option("--model", "-m", help="Override model")
    ] = None,
    no_save: Annotated[
        bool, typer.Option("--no-save", help="Don't save results to storage")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Verbose output")
    ] = False,
):
    """Run an evaluation from a config file."""
    from evals.framework.config import (
        config_to_experiment_set,
        get_config_path,
        load_config,
    )

    config_path = get_config_path(config_name)
    config = load_config(config_path)

    if verbose:
        typer.echo(f"Loading config: {config_path}")
        typer.echo(f"Agent: {config.agent.__name__}")
        typer.echo(f"Models: {config.models}")
        typer.echo(f"Prompts: {len(config.prompts)}")

    # Sample dataset if requested
    if sample and sample < len(config.dataset):
        import random

        config.dataset = random.sample(config.dataset, sample)
        typer.echo(f"Sampled {sample} cases from dataset")

    # Override models if specified
    if model:
        config.models = [model]

    # Create experiment set
    exp_set = config_to_experiment_set(config)
    typer.echo(f"Running {len(exp_set.experiments)} experiments...")

    # Run
    result = asyncio.run(exp_set.run(save=not no_save))

    # Print results
    result.print_comparison()


@app.command("list")
def list_experiments(
    agent: Annotated[
        str | None, typer.Option("--agent", "-a", help="Filter by agent type")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 20,
):
    """List stored experiments."""
    from evals.framework.store import LocalStore

    store = LocalStore()
    results = store.list_experiments(agent_type=agent, limit=limit)

    if not results:
        typer.echo("No experiments found")
        return

    typer.echo(f"\n{'ID':<36} {'Name':<20} {'Model':<15} {'Success':<8} {'Created'}")
    typer.echo("-" * 100)

    for r in results:
        model_short = r.model.split(":")[-1][:15] if ":" in r.model else r.model[:15]
        typer.echo(
            f"{str(r.id):<36} {r.name[:20]:<20} {model_short:<15} "
            f"{r.success_rate:>6.1%}  {r.created_at.strftime('%Y-%m-%d %H:%M')}"
        )


@app.command()
def show(
    experiment_id: Annotated[str, typer.Argument(help="Experiment ID")],
):
    """Show details of a specific experiment."""
    from evals.framework.store import LocalStore

    store = LocalStore()
    result = store.load(experiment_id)

    if result is None:
        typer.echo(f"Experiment not found: {experiment_id}")
        raise typer.Exit(1)

    typer.echo(f"\n{'=' * 60}")
    typer.echo(f"Experiment: {result.name}")
    typer.echo(f"{'=' * 60}")
    typer.echo(f"ID:           {result.id}")
    typer.echo(f"Agent:        {result.agent_type}")
    typer.echo(f"Model:        {result.model}")
    typer.echo(f"Created:      {result.created_at}")
    typer.echo("\nProvenance:")
    typer.echo(f"  Git commit: {result.provenance.git_commit[:12]}")
    typer.echo(f"  Git branch: {result.provenance.git_branch}")
    typer.echo(f"  Git dirty:  {result.provenance.git_dirty}")
    typer.echo(
        f"  Prompt:     {result.provenance.prompt.source}://{result.provenance.prompt.ref or 'inline'}"
    )
    typer.echo(f"  Prompt hash:{result.provenance.prompt.hash}")
    typer.echo(
        f"  Dataset:    {result.provenance.dataset_name} ({result.provenance.case_count} cases)"
    )
    typer.echo(f"  Dataset hash: {result.provenance.dataset_hash}")
    typer.echo("\nResults:")
    typer.echo(f"  Total cases:  {result.total_cases}")
    typer.echo(f"  Failed cases: {result.failed_cases}")
    typer.echo(f"  Success rate: {result.success_rate:.1%}")
    typer.echo(f"  Duration:     {result.duration_seconds:.1f}s")
    typer.echo("\nMetrics:")
    for metric, value in sorted(result.summary.items()):
        if isinstance(value, float):
            typer.echo(f"  {metric}: {value:.1%}")
        else:
            typer.echo(f"  {metric}: {value}")
    if result.results_path:
        typer.echo(f"\nResults file: {result.results_path}")


@app.command()
def compare(
    id1: Annotated[str, typer.Argument(help="Baseline experiment ID")],
    id2: Annotated[str, typer.Argument(help="Candidate experiment ID")],
    show_disagreements: Annotated[
        bool, typer.Option("--disagreements", "-d", help="Show disagreeing cases")
    ] = False,
):
    """Compare two experiments."""
    from evals.framework.compare import (
        compare_experiments,
        find_disagreements,
        print_disagreements,
    )
    from evals.framework.store import LocalStore

    store = LocalStore()

    result1 = store.load(id1)
    result2 = store.load(id2)

    if result1 is None:
        typer.echo(f"Experiment not found: {id1}")
        raise typer.Exit(1)
    if result2 is None:
        typer.echo(f"Experiment not found: {id2}")
        raise typer.Exit(1)

    comparison = compare_experiments(result1, result2)
    comparison.print_comparison()

    if show_disagreements:
        try:
            disagreements = find_disagreements(result1, result2, store)
            print_disagreements(disagreements)
        except (ImportError, ValueError) as e:
            typer.echo(f"\nCouldn't compute disagreements: {e}")


@app.command("configs")
def list_configs():
    """List available config files."""
    from evals.framework.config import list_configs as _list_configs

    configs = _list_configs()
    if not configs:
        typer.echo("No configs found")
        return

    typer.echo("\nAvailable configs:")
    for path in configs:
        typer.echo(f"  {path.stem}")


@app.command()
def delete(
    experiment_id: Annotated[str, typer.Argument(help="Experiment ID to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
):
    """Delete an experiment."""
    from evals.framework.store import LocalStore

    store = LocalStore()
    result = store.load(experiment_id)

    if result is None:
        typer.echo(f"Experiment not found: {experiment_id}")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete experiment '{result.name}' ({experiment_id})?")
        if not confirm:
            raise typer.Abort()

    store.delete(experiment_id)
    typer.echo(f"Deleted experiment: {experiment_id}")


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
