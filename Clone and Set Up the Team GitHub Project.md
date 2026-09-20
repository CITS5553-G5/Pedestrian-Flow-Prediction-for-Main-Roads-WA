# Clone and Set Up the Team GitHub Project

## 1. Get repository access

Send your personal GitHub username to the repository administrator. You must accept the Collaborator invitation before you can access this private repository.

## 2. Clone the repository

Open the repository on GitHub, select the green **Code** button, choose **HTTPS**, and copy the repository address.

Open macOS Terminal, Windows PowerShell, or the VS Code terminal and run:

```bash
git clone https://github.com/CITS5553-G5/Pedestrian-Flow-Prediction-for-Main-Roads-WA.git
cd Pedestrian-Flow-Prediction-for-Main-Roads-WA
```

GitHub may ask you to sign in through a browser the first time.

You can clone the repository into any normal folder on your computer. Team members do not need to use the same local path.

## 3. Open the project

In VS Code, select **File → Open Folder**, then open:

```text
Pedestrian-Flow-Prediction-for-Main-Roads-WA
```

If the VS Code terminal command is available, you can instead run:

```bash
code .
```

## 4. Create the Python environment

The pinned packages support binary installation on Windows x64 and Apple Silicon macOS 14 or newer. Use the container for a consistent Linux environment; other native platforms require separate compatibility checks.

`requirements.txt` is already included in the repository. It does not need to be sent separately.

On macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
```

Creating `.venv` and installing the packages is normally required only once.

When opening a new terminal later, do nothing if `(.venv)` is already shown at the start of the prompt. Otherwise, run the relevant activation command again. You do not need to recreate the environment.

## 5. Create a personal working branch

Do not develop directly on `main`. First update it:

```bash
git switch main
git pull origin main
```

Then create your personal branch for the current stage:

```bash
git switch -c chris/02-extract-features
git push -u origin chris/02-extract-features
```

Replace `chris` with your own name. After the first push, later updates from the same branch require only:

```bash
git push
```

See `GIT_WORKFLOW.md` in the repository root for the complete commit, review, and Pull Request workflow.