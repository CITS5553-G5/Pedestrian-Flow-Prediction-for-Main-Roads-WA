# Research configuration

`context_features_v1.json` preserves the historical multi-source Context settings.
Research callers must supply their source registry explicitly. Google Places
Aggregate remains excluded.

`imagery.env.example` lists keys and switches used by earlier imagery experiments.
Copy only the settings needed by that experiment into the local environment.

Formal prediction uses `configs/prediction/` and the root `.env.example`.
