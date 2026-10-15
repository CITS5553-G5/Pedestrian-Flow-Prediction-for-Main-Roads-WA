# Imagery notebooks

The [original research notebook](Image_Feature_Extraction_Pipeline.ipynb) preserves the full image-feature extraction process for customer review: location input, coordinate offsets, Google satellite and Street View retrieval, sample image previews, the original 13-field Gemini prompt, sequential site and batch processing, CSV export, limitations and optional geometry/Colab helpers. Its extraction functions and stored research previews are preserved. Credentials are read from the local environment rather than embedded in the file.

The [reviewed workflow notebook](Run_Reviewed_Imagery_Workflow.ipynb) calls the maintained `pedflow.imagery` implementation. It uses the concurrency set in `configs/prediction/imagery_v1.json` (currently 50 workers), checkpoints, retry handling and per-site statuses. Routine prediction uses this shared implementation; the original research notebook remains available to explain how the imagery process was developed.

## Configure your own API keys

Complete the [project setup](../../README.md#native-setup-for-windows-and-macos), then copy the project root `.env.example` to `.env`. Enter your own Google Maps and Gemini API credentials in that local file:

```dotenv
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

The values above are placeholders. Both notebooks load the repository-root `.env`; existing process environment variables take precedence. `.env` is Git-ignored. Keep actual credentials in that file or your environment and leave them out of notebook source, printed diagnostics and saved outputs. Do not edit `.env.example` to contain working keys.

Open either notebook within the repository and select the project Python environment. Running image retrieval or Gemini extraction makes external service requests. Viewing the saved research outputs requires no API key.

## Run the original research process

Run the primary sections in order. In the input cell, set `INPUT_PATH` and `INPUT_SHEET` for your location table; the delivered default is `data/processed/model_dataset.xlsx`, worksheet `Model_Data`. Inputs need `site_id`, `latitude` and `longitude`. The notebook then defines coordinate offsets and imagery retrieval, demonstrates a sample image set, defines Gemini extraction, processes sites in sequential batches of 20, and joins the results to the input table. New files are written under `outputs/imagery_features/research_notebook/`, including per-batch CSV files and `ausrap_with_gemini_features.csv`.

The displayed tables and image previews are preserved historical research outputs. They were not regenerated during restoration and need not describe a newly selected input file. The final appendix contains optional original midpoint and Google Colab upload/download helpers; use only the helpers relevant to your environment and fill their file placeholders before running them.

The research notebook retains its original sampling, prompt, model selection and function implementations. Its sequential batch processing and row-order join differ from the maintained workflow's concurrency, validation and recovery. The [imagery integration guide](../../docs/02_feature_extraction/imagery_integration.md) describes operational configuration, statuses and validation limits. New prediction batches use the [prediction run guide](../../docs/04_prediction_pipeline/prediction_workflow.md).
