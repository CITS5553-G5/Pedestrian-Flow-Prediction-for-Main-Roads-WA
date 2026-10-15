"""Export the offline survey comparison as CSV, strict JSON and a short report."""

import argparse
import json
from pathlib import Path

from pedflow.evaluation.irap import MODEL_LABEL, REFERENCE_LABEL, load_comparison
from pedflow.io import atomic_path, write_json_atomic


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    folder = args.output_directory
    if folder.exists() and any(folder.iterdir()):
        parser.error("Use a new empty output directory; existing research results are not overwritten.")
    result = load_comparison(args.project_root, args.audit)
    folder.mkdir(parents=True, exist_ok=True)
    for filename, table in [("site_comparison.csv", result.sites),
                            ("paired_errors.csv", result.errors), ("metrics.csv", result.metrics)]:
        with atomic_path(folder / filename) as temporary:
            table.to_csv(temporary, index=False)
    # Pandas serialises missing values as JSON null, retaining real zero flows.
    payload = {"manifest": result.manifest, "sites": json.loads(result.sites.to_json(orient="records", double_precision=15)),
               "errors": json.loads(result.errors.to_json(orient="records", double_precision=15)),
               "metrics": json.loads(result.metrics.to_json(orient="records", double_precision=15))}
    write_json_atomic(folder / "comparison.json", payload)
    write_json_atomic(folder / "manifest.json", result.manifest)
    lines = ["# Observed pedestrian flow comparison", "",
             "Internal road-grouped OOF comparison; units: pedestrians/hour.", "",
             "| Direction | Method | N | MAE | RMSE |", "| --- | --- | ---: | ---: | ---: |"]
    for row in result.metrics.itertuples(index=False):
        mae = "unavailable" if row.n == 0 else f"{row.mae:.4f}"
        rmse = "unavailable" if row.n == 0 else f"{row.rmse:.4f}"
        lines.append(f"| {row.direction} | {row.method} | {row.n} | {mae} | {rmse} |")
    lines += ["", "All survey rows remain in site_comparison.csv. Eligibility is direction-specific.",
              "The reference column retains the name: " + REFERENCE_LABEL + ".", ""]
    for direction in result.manifest["sample_ids"]:
        m = result.metrics[result.metrics.direction.eq(direction)].set_index("method")
        base = m.loc[REFERENCE_LABEL, "mae"]
        if base > 0:
            reduction = 100 * (1 - m.loc[MODEL_LABEL, "mae"] / base)
            lines.append(f"{direction}: model MAE is {reduction:.2f}% lower than the recoded reference on the same sites.")
    lines += ["", "## Interpretation limits", "", *result.manifest["limitations"], ""]
    (folder / "comparison_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(result.metrics.to_string(index=False))
    print(f"Saved comparison for {len(result.sites)} sites to {folder}")


if __name__ == "__main__":
    main()
