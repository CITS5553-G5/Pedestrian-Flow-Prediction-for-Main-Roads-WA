# Backend

This directory is reserved for the application API and application-side input validation. The backend should call the shared prediction function under `src/pedflow/` and return its results without duplicating prediction logic.

The backend framework and API contract have not yet been selected.

The shared function is now implemented as `pedflow.prediction.predict_sites`.
Its [run guide](../../docs/04_prediction_pipeline/prediction_workflow.md) documents
inputs, results and per-site statuses. The backend connection remains to be built.
