# Stage 5 application

This stage contains the application prototype and the reserved backend area for a future validated prediction service.

- `backend/` is reserved for the API and application-side input validation. The backend technology and API contract have not been selected.
- `frontend/` contains a React/Vite demonstration interface.

The frontend currently uses hard-coded demonstration data and browser-side rules. It is not connected to a trained model and must not be presented as a working prediction product. Once the team validates the prediction workflow, both the batch interface and backend should call the same shared inference implementation rather than duplicating model or feature logic.
