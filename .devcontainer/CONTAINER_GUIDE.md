# Pedestrian Exposure WA — Container Guide

## Environment

The optional development container uses the Rocker R 4.5.3 image pinned by digest, Python 3.11.16 and Node.js 22.23.2. It includes R Markdown, Pandoc, LaTeX and the project's analysis tools. The image supports Linux ARM64 and AMD64. VS Code connects as the Linux user `rstudio` and opens the repository at `/workspace`.

Python packages are installed in `/opt/pedflow-venv`, outside the host repository. VS Code uses `/opt/pedflow-venv/bin/python`; notebooks can select **Pedflow (Python 3.11)**. The shared `pedflow` package is installed in editable mode, so source edits are immediately available to notebooks and the `pedflow-context` command.

`requirements.in` declares the direct Python dependencies, and `requirements.txt` fixes the installation versions, including transitive dependencies and platform markers. `renv.lock` records the R version and package versions. The setup script restores R packages into the container's site library and checks their versions; it does not activate a host-side R project library. Frontend dependencies are fixed by `package-lock.json`. Dev Container Features are fixed by `devcontainer-lock.json`.

The frontend's `node_modules` directory uses a Compose-managed named volume. Python and R libraries belong to the container and are restored when it is recreated. The repository itself is a bind mount, so source files and project outputs remain on the host.

## Open the project

Install OrbStack or Docker Desktop, Visual Studio Code and the Microsoft Dev Containers extension.

1. Start the container engine and open the cloned repository root in VS Code.
2. Run **Dev Containers: Reopen in Container** from the Command Palette.
3. Wait for initialization to install Python dependencies, register the notebook kernel and restore the R library.
4. Select **Pedflow (Python 3.11)** when opening a project notebook.

The Dev Container CLI provides the equivalent terminal entry point. With the CLI installed, run this from the repository root:

```bash
devcontainer up --workspace-folder . --frozen-lockfile
devcontainer exec --workspace-folder . bash
```

Environment creation uses Dev Containers so that Features and initialization commands are applied. Ordinary `docker compose up` does not perform that initialization.

## Runtime configuration and data

Copy `.env.example` to `.env` at the repository root and fill in only the credentials required by the active experiment. Python code loads `/workspace/.env` explicitly with `python-dotenv`. Restart the command or notebook kernel after changing runtime settings. Keep `.env` local and out of Git.

Authorised source data belongs in `data/raw/`. Code uses repository-relative paths so that Python work also runs in a native Python 3.11 environment on Windows or macOS, as described in the repository README.

## Frontend

Run these commands inside the container:

```bash
cd /workspace/05_application/frontend
npm ci
npm run dev -- --host 0.0.0.0
```

VS Code forwards port 5173. Open the forwarded address shown by VS Code, normally `http://localhost:5173`. Run `npm ci` again whenever `package-lock.json` changes. Initialization assigns the frontend dependency volume to the connected user.

## R Markdown

Render a project document from the repository root:

```bash
Rscript -e "rmarkdown::render('03_model_development/03_Yashika_Predict_Pedestrians_Final_Model_Comparison.Rmd', output_format = 'html_document')"
```

Use `output_format = 'pdf_document'` for PDF, or `output_format = 'all'` for every format declared in the document. Without an explicit format, R Markdown selects the first format in the YAML header. Rendering project documents runs their analysis code and requires their input datasets.

## Verify the environment

From the repository root inside the container:

```bash
bash .devcontainer/verify.sh
```

The check verifies Python and Node versions, Python dependency consistency and imports, the installed project command, the project test suite, frontend installation/lint/build, R package versions, and HTML/PDF rendering of a small synthetic document. It writes frontend build files under the ignored `dist/` directory. Tests that require the optional local Overture download cache skip when that cache is absent.

## Restore, rebuild and stop

After pulling changes to `requirements.txt` or `renv.lock`, restore the environment from the repository root and restart active Python kernels and R sessions:

```bash
bash .devcontainer/setup.sh
```

Use **Dev Containers: Rebuild Container** after changing the base image, Features, toolchain versions or container configuration. VS Code waits for initialization to finish before the environment is ready.

For status, logs and stopping an existing environment, run from the repository root on the host:

```bash
docker compose -f .devcontainer/compose.yaml ps
docker compose -f .devcontainer/compose.yaml logs app
docker compose -f .devcontainer/compose.yaml stop
```

`docker compose -f .devcontainer/compose.yaml down` removes the project's containers and network while retaining named volumes. Adding `--volumes` also deletes the frontend dependency volume; `npm ci` restores those packages. Closing the VS Code remote connection stops the Compose services according to `shutdownAction`.

## Parallel copies

The default Compose project name is `pedestrian-exposure-wa`. Each concurrently running clone or worktree needs a distinct `COMPOSE_PROJECT_NAME`. For example, in a host terminal:

```bash
export COMPOSE_PROJECT_NAME=pedestrian-exposure-wa-experiment
devcontainer up --workspace-folder . --frozen-lockfile
devcontainer exec --workspace-folder . bash
```

Use the same environment variable for that copy's subsequent CLI and Compose commands. On PowerShell, set it with `$env:COMPOSE_PROJECT_NAME = "pedestrian-exposure-wa-experiment"`. Container and frontend volume names are scoped to the chosen project name.

## Dependency maintenance

Team members install with pip from the committed `requirements.txt`. Maintainers edit `requirements.in` and regenerate the lock using a universal Python 3.11 resolution; uv is only a lock-generation tool here, not a required team package manager:

```bash
uv pip compile requirements.in --python-version 3.11 --universal --output-file requirements.txt
```

Existing pins are retained where compatible. Use `--upgrade-package PACKAGE` for a deliberate package upgrade, then verify the environment and commit both requirements files. Validate native Windows/macOS environments as well as the container before claiming support for all three platforms.

For R updates, install and test the selected package versions in a disposable copy of the container, then record that container library with `renv::snapshot(lockfile = 'renv.lock', library = .libPaths()[1L], type = 'all', prompt = FALSE)`. Keep the R package versions in the `r-packages` Feature aligned with the lockfile, rebuild, and run the verification script. Base-image digests and exact Python/Node versions are updated deliberately together with compatibility checks. System packages installed by apt are resolved from the distribution repositories at build time; the configuration does not freeze those repositories.

The setup follows the [Dev Container CLI](https://code.visualstudio.com/docs/devcontainers/devcontainer-cli), [renv restore](https://rstudio.github.io/renv/reference/restore.html), [uv requirements locking](https://docs.astral.sh/uv/pip/compile/) and [R Markdown rendering](https://rmarkdown.rstudio.com/docs/reference/render.html) documentation.
