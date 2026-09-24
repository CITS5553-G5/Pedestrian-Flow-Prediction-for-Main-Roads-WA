"""The single batch prediction command."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from pedflow.exceptions import PedflowError
from pedflow.io import read_sites
from pedflow.paths import find_project_root, resolve_project_path
from pedflow.prediction import predict_sites
from pedflow.prediction.io import refresh_prediction_outputs, write_prediction_outputs


def main() -> int:
    """Run the shared service and return distinct complete, partial and failed exit codes."""
    parser = argparse.ArgumentParser(
        description="Predict pedestrian flow from an Excel, CSV or Parquet site table."
    )
    parser.add_argument(
        "--input", help="Location input; optional when refreshing saved comparisons."
    )
    parser.add_argument(
        "--refresh-comparison",
        action="store_true",
        help="Refresh only comparison columns in the saved output; no extraction or inference.",
    )
    parser.add_argument("--sheet", default="Batch_Input")
    parser.add_argument("--output-directory", default="outputs/predictions")
    parser.add_argument("--config", default="configs/prediction/workflow_v1.json")
    parser.add_argument(
        "--workers", type=int, help="Maximum concurrent imagery sites (default: 10)."
    )
    parser.add_argument(
        "--resume", action="store_true", help="Reuse saved imagery; retry failed sites."
    )
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    if args.refresh_comparison and args.resume:
        parser.error("--refresh-comparison and --resume are separate operations.")
    if not args.refresh_comparison and not args.input:
        parser.error("--input is required for prediction.")
    try:
        root = args.project_root.resolve() if args.project_root else find_project_root()
        load_dotenv(root / ".env", override=False)
        sites = (
            read_sites(resolve_project_path(root, args.input), sheet=args.sheet)
            if args.input
            else None
        )
        output = resolve_project_path(root, args.output_directory)
        if args.refresh_comparison:
            for name, path in refresh_prediction_outputs(output, root, sites=sites).items():
                print(f"{name}: {path}")
            return 0
        result = predict_sites(
            sites,
            root,
            config_path=args.config,
            workers=args.workers,
            checkpoint_path=output / "imagery.checkpoint.json",
            resume=args.resume,
            progress=lambda done, total, site, status: print(
                f"Imagery {done}/{total} {site}: {status}", flush=True
            ),
        )
        for name, path in write_prediction_outputs(result, output).items():
            print(f"{name}: {path}")
        print(f"Run {result.metadata['run_id']}: {result.metadata['status_counts']}")
        return (
            0
            if result.predictions.status.isin(["predicted", "predicted_with_warning"]).all()
            else 2
        )
    except (PedflowError, OSError) as exc:
        print(f"Prediction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
