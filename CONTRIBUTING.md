# Team contribution guide

## Normal workflow

1. Pull the latest `main` before starting new work.
2. Create one short-lived branch for one task, such as `member/02-topic`.
3. Make small, related commits with action-oriented messages.
4. Push the branch and open a Pull Request into `main`.
5. Ask at least one teammate to review the changed files and instructions.
6. Merge the Pull Request, delete the short-lived branch and pull the updated `main`.

Do not use a long-lived `develop` branch. Do not force-push or delete `main`. Repository owners should enable branch protection after the initial cleanup is on GitHub.

## Before a commit

- Run `git status` and stage only files that belong to the task.
- Do not commit `.env`, passwords, API keys, tokens or personal credentials.
- Clear notebook execution outputs when they contain personal paths, large results or credentials.
- Keep generated files under `outputs/`, temporary files under `tmp/` and personal experiments under the ignored `05_test/` directory.
- Confirm that any new data is authorised, documented and required for a reproducible project workflow.
- Check that code uses repository-relative paths and runs from a clone with an arbitrary folder name.

## Naming

Personal notebooks use `<stage>_<sequence>_<member>_<topic>.ipynb`. Shared integration files omit the member name. Use lowercase letters, two-digit numbers and underscores; do not use spaces or characters that are invalid on Windows.

Branches use lowercase words separated by hyphens after a member or purpose prefix, for example `haoqi/02-pta-stops`, `docs/native-setup` or `fix/model-input-path`.

Commit messages should explain the outcome, for example `Document native Windows and macOS setup` or `Add PTA stop feature notebook`.

## Pull Request review

The reviewer should confirm that the change is understandable, does not expose secrets, follows the data policy and does not introduce host-specific paths. For code changes, the author should state what was run and whether the result passed.
