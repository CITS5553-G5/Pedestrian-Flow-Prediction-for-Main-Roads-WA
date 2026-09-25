"""The single batch prediction command."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from pedflow.exceptions import PedflowError
from pedflow.io import read_sites
from pedflow.paths import find_project_root, resolve_project_path
from pedflow.prediction import predict_sites
from pedflow.prediction.io import write_prediction_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Predict pedestrian flow from road/SLK or coordinate Excel, CSV or Parquet input."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet", default="Batch_Input", help="Excel sheet: Batch_Input, Road_SLK or Coordinates.")
    parser.add_argument("--output-directory", default="outputs/predictions")
    parser.add_argument("--config", default="configs/prediction/workflow_v1.json")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--resume", action="store_true", help="Reuse saved imagery; retry failed sites.")
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve() if args.project_root else find_project_root()
        load_dotenv(root / ".env", override=False)
        sites = read_sites(resolve_project_path(root, args.input), sheet=args.sheet)
        output = resolve_project_path(root, args.output_directory)
        result = predict_sites(
            sites, root, config_path=args.config, workers=args.workers,
            checkpoint_path=output / "imagery.checkpoint.json", resume=args.resume,
            progress=lambda done, total, site, status: print(
                f"Imagery {done}/{total} {site}: {status}", flush=True
            ),
        )
        for name, path in write_prediction_outputs(
            result, output, template_path=root / "data/templates/prediction_output_template.xlsx"
        ).items():
            print(f"{name}: {path}")
        print(f"Run {result.metadata['run_id']}: {result.metadata['status_counts']}")
        return 0 if result.predictions.status.isin(["predicted", "predicted_with_warning"]).all() else 2
    except (PedflowError, OSError) as exc:
        print(f"Prediction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
