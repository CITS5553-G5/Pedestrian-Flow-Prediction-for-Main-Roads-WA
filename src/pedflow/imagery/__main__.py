"""Batch command calling the same imagery implementation as notebooks and services."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from pedflow.exceptions import PedflowError


def main() -> int:
    """Load local credentials and adapt batch files to the shared imagery service."""
    parser = argparse.ArgumentParser(
        description="Extract imagery features with bounded site concurrency."
    )
    parser.add_argument(
        "--input", required=True, help="Excel, CSV or Parquet with site_id, latitude, longitude."
    )
    parser.add_argument("--sheet", default="Batch_Input")
    parser.add_argument("--config", default="configs/prediction/imagery_v1.json")
    parser.add_argument(
        "--workers", type=int, help="Override the maximum simultaneously active sites."
    )
    parser.add_argument("--output-directory", default="outputs/imagery_features")
    parser.add_argument(
        "--checkpoint", help="Progress JSON path; defaults to the output directory."
    )
    parser.add_argument(
        "--resume", action="store_true", help="Reuse successful checkpoint records; retry failures."
    )
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    from dotenv import load_dotenv

    from pedflow.imagery import build_imagery_features, load_imagery_config
    from pedflow.imagery.io import write_imagery_outputs
    from pedflow.io import read_sites
    from pedflow.paths import find_project_root, resolve_project_path

    try:
        root = args.project_root.resolve() if args.project_root else find_project_root()
        load_dotenv(root / ".env", override=False)
        config = load_imagery_config(resolve_project_path(root, args.config))
        if args.workers is not None:
            config = replace(config, max_workers=args.workers)
        output = resolve_project_path(root, args.output_directory)
        checkpoint = (
            resolve_project_path(root, args.checkpoint)
            if args.checkpoint
            else output / "imagery.checkpoint.json"
        )
        sites = read_sites(resolve_project_path(root, args.input), sheet=args.sheet)
        result = build_imagery_features(
            sites,
            config,
            checkpoint_path=checkpoint,
            resume=args.resume,
            progress=lambda done, total, site, status: print(
                f"{done}/{total} {site}: {status}", flush=True
            ),
        )
        for name, path in write_imagery_outputs(result, output).items():
            print(f"{name}: {path}")
        return 0 if result.features["imagery_status"].eq("complete").all() else 2
    except (PedflowError, OSError) as exc:
        print(f"Imagery extraction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
