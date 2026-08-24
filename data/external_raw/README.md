# External source snapshots

This directory holds only selected snapshots of external sources used by a documented feature workflow. Files are not approved for Git merely because they were downloaded into this directory.

Each shared source should have a stable provider directory and, when the source changes over time, a dated snapshot directory. Its corresponding guidance under `docs/feature_sources/` should record the provider, source URL, retrieval or release date, licence, expected files and the notebook that consumes it.

Before adding a snapshot to Git, confirm all of the following:

1. The source licence and client arrangements permit sharing it with approved collaborators in this private repository.
2. The file is required to reproduce the current project workflow.
3. A download script or external approved storage location would not be a better option.
4. The file size and expected update frequency are suitable for ordinary Git.
5. No credentials, private cache files or disposable partial downloads are included.

Temporary `.part` downloads, imagery payloads and local caches must not be committed. Treat existing tracked snapshots as immutable; add a new dated snapshot rather than silently replacing source evidence.
