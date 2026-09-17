# GitHub Team Workflow (English)

## 1. First clone and setup

Clone the repository from GitHub and open a terminal at the repository root. `requirements.txt` is already included in the clone; nobody needs a separate copy.

macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Creating `.venv` and installing the packages is normally a one-time setup. The `.venv` folder remains on the computer and is not committed to Git. In a new terminal, do nothing if `(.venv)` is already shown at the start of the prompt. Otherwise run `source .venv/bin/activate` on macOS or `.venv\Scripts\Activate.ps1` on Windows. Reinstall the requirements only after `requirements.txt` changes.

## 2. Start work

Do not develop directly on `main`. Update `main`, then create your own branch for the current project stage:

```bash
git switch main
git pull origin main
git switch -c haoqi/02-extract-features
```

Replace `haoqi` with your own name. Each member uses one personal branch for the stage, such as `chris/02-extract-features`. A member may work on several related Stage 2 notebooks on that branch; a separate branch for every notebook is unnecessary.

## 3. Commit and publish the branch

Add only the files that belong to the change. Do not use an unchecked `git add .`:

```bash
git status
git add <file-path>
git status
git commit -m "Briefly describe the result"
git push -u origin haoqi/02-extract-features
```

Use `-u origin <branch-name>` for the first push. Later pushes from the same branch need only `git push`. Other members can see a branch on GitHub only after it has been pushed.

## 4. View remote branches on GitHub

Open the repository page and select the branch dropdown that currently shows `main` to see all published branches. Open **Pull requests** to see changes that members are preparing to merge.

You normally do not need to download every branch to see other members' work. Open the relevant Pull Request and select **Files changed** to review every added, removed or edited line.

If you need to run a teammate's branch locally:

```bash
git fetch origin
git switch --track origin/chris/02-extract-features
```

`git fetch origin` updates information about remote branches without changing the current working files. Do not try to use `git pull` to download every branch; `git pull` updates only the current branch.

## 5. Open a Pull Request and request review

After pushing, select **Compare & pull request** on GitHub. Confirm that the base is `main` and the compare branch is your branch. Describe the changes and what you checked, then create the Pull Request.

Select at least one teammate under **Reviewers** on the right side of the Pull Request. The reviewer opens **Files changed**, reads the diff and can leave line comments. They then select **Review changes** and choose **Approve**, **Request changes** or **Comment**. The reviewer needs to download the branch only when they want to run the code locally.

No repository setting is required when the team follows the one-review rule voluntarily. To enforce it, a repository administrator can open **Settings → Rules → Rulesets**, target `main`, require a Pull Request before merging and require one approval. Enable this only after at least one teammate has accepted the Collaborator invitation.

## 6. After merging

After approval and merge, delete the temporary branch on GitHub. Start the next piece of work from the latest `main`:

```bash
git switch main
git pull origin main
git branch -d haoqi/02-extract-features
git switch -c haoqi/03-model-development
```

If more Stage 2 work is needed, you may create a new `haoqi/02-extract-features` branch from the updated `main` instead.

## 7. Before every commit

Run `git status`. Do not commit `.env`, secrets, passwords, personal absolute paths, automatically downloaded external caches, the legacy `outputs/` directory, `tmp/` directory. Files under `06_outputs/` may be committed only when they are reviewed team results and the generating notebook or script is included in the same change. Shared code must use repository-relative paths and work from different clone locations on both Windows and macOS.
