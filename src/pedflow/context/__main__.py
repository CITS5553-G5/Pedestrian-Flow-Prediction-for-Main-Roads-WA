"""Command-line entry point for the integrated context-feature workflow.

Python executes this module when a user runs ``python -m
pedflow.context``. It handles command-line arguments and delegates all
workflow behaviour to the package modules; it contains no source calculations.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from pedflow.context.sources.registry import build_default_registry
from pedflow.exceptions import PedflowError


def parse_arguments() -> argparse.Namespace:
    """Define and parse the supported Stage 2 command-line options."""

    parser = argparse.ArgumentParser(
        prog="pedflow-context",
        description=(
            "Build a validated context-feature table through registered source adapters."
        )
    )
    parser.add_argument(
        "--config",
        default="configs/context_features_v1.json",
        help="JSON configuration path, relative to the project root by default.",
    )
    parser.add_argument(
        "--sources",
        help=(
            "Development-only comma-separated source override. A released model must use "
            "the frozen source set recorded in its manifest."
        ),
    )
    parser.add_argument(
        "--input",
        help="Batch input workbook, CSV or Parquet file; overrides input.path in the config.",
    )
    parser.add_argument(
        "--output-directory",
        help="Generated-output directory; overrides output.directory in the config.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Explicit 03_Project root; normally discovered automatically.",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List registered sources and their implementation status, then exit.",
    )
    return parser.parse_args()


def list_registered_sources() -> None:
    """Print the registered source catalogue without loading heavy dependencies."""

    registry = build_default_registry()
    for definition in registry.values():
        print(definition.name)
        print(f"  {definition.description}")


def run_workflow(arguments: argparse.Namespace) -> int:
    """Load configuration and run the integrated workflow once."""

    # Heavy data libraries are imported only for a real workflow run. This keeps
    # commands such as --help and --list-sources fast and dependency-light.
    from pedflow.context.config import load_context_config, select_sources
    from pedflow.context.io import read_batch_input, write_context_outputs
    from pedflow.context.workflow import build_context_features
    from pedflow.paths import find_project_root, resolve_project_path

    registry = build_default_registry()
    project_root = (
        arguments.project_root.resolve()
        if arguments.project_root is not None
        else find_project_root(Path(__file__).resolve())
    )
    config_path = resolve_project_path(project_root, arguments.config)
    config = load_context_config(config_path)
    if arguments.input:
        config = replace(config, input_path=arguments.input)
    if arguments.output_directory:
        config = replace(config, output_directory=arguments.output_directory)
    if arguments.sources:
        config = select_sources(config, arguments.sources.split(","))

    sites = read_batch_input(project_root, config)
    result = build_context_features(
        sites=sites,
        config=config,
        project_root=project_root,
        registry=registry,
    )
    written = write_context_outputs(project_root, config, result)

    print(
        f"Stage 2 completed: {len(result.features)} sites, "
        f"{len(result.source_results)} sources, version {result.feature_set_version}."
    )
    for output_type, path in written.items():
        print(f"  {output_type}: {path}")
    return 0


def main() -> int:
    """Execute the requested command and return a process exit code."""

    arguments = parse_arguments()
    if arguments.list_sources:
        list_registered_sources()
        return 0

    try:
        return run_workflow(arguments)
    except PedflowError as exc:
        print(f"Stage 2 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
