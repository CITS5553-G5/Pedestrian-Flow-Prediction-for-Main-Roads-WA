# Stage 5 application

This directory contains a [React/Vite frontend demonstration](frontend/README.md) and a [reserved backend area](backend/README.md). The API framework and application contract have not been selected.

The frontend uses hard-coded records and browser-side rules. It is not connected to the released model or a backend API; its demonstration values and confidence displays are not validated model outputs. Operational prediction is available separately through the [batch workflow](../docs/04_prediction_pipeline/prediction_workflow.md).

The shared inference service is `pedflow.prediction.predict_sites`. Future application integration should call that service and present its location, prediction and comparison statuses without duplicating model or feature logic. Dashboard integration and live-service acceptance remain separate work.
