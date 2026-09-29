"""Project path discovery without machine-specific absolute paths."""

from __future__ import annotations

from pathlib import Path

from pedflow.exceptions import ConfigurationError


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root containing the package and Stage 2 directory."""

    current = (start or Path.cwd()).resolve()
    candidates = (current, *current.parents)

    for candidate in candidates:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src" / "pedflow").is_dir()
            and (candidate / "02_feature_extraction").is_dir()
        ):
            return candidate

    raise ConfigurationError(
        "Could not find the repository root. Run the command from within the "
        "repository or pass an explicit project root."
    )


def resolve_project_path(project_root: Path, configured_path: str | Path) -> Path:
    """Resolve a configuration path relative to the project root."""

    path = Path(configured_path)
    return path if path.is_absolute() else project_root / path
