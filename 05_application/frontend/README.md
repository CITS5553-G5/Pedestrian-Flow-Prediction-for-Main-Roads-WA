# Frontend demo

This React/Vite interface is an early visual prototype. It currently uses hard-coded demonstration records and browser-side rules; it is not connected to the project's trained model or a backend API.

From this directory, install the locked dependencies and start the development server:

```bash
npm ci
npm run dev
```

Use `npm run build` to verify that the production bundle compiles. Generated `node_modules/` and `dist/` directories are local build artefacts and are excluded from Git.

Before this interface is described as functional, replace all demonstration prediction logic and unsupported confidence values with responses from the validated backend contract.
