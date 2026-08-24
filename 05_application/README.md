# Stage 5 application

This stage contains the software that lets a user run the agreed prediction workflow and view or download its results.

- `backend/` contains the API and application-side input validation. It should call `04_prediction_pipeline/` instead of duplicating preparation, feature or model logic.
- `frontend/` contains the user interface for submitting inputs, showing processing status and presenting results.

The team has not yet selected the application technology. Add framework-specific files only after that decision is recorded and reviewed.
