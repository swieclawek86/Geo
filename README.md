# Development Program Planner — Public Functional Demo

This build is intended exclusively for a public proof-of-concept using the bundled **synthetic** 16-well workbook. Excel uploads are disabled to help prevent accidental exposure of confidential well forecasts. Do **not** enter confidential information in scheduling fields, scenario names, or other inputs.

## Publish using Streamlit Community Cloud

1. Create a new **public** GitHub repository (for example, `well-planner-demo`).
2. Upload the files inside this ZIP to the **repository root**, keeping `app.py`, `engine.py`, `requirements.txt`, and `sample_well_database.xlsx` together.
3. Sign in to https://share.streamlit.io/ with GitHub, select **Create app** → **Yup, I have an app**.
4. Choose the new repository and its `main` branch, and set the entrypoint to `app.py`.
5. Select **Deploy**. Streamlit will provide a `https://....streamlit.app` link that you can share for the functional test.

This does not deploy automatically. The repository creation and Streamlit deployment steps must be performed by the owner of the accounts.

## What to test

- Change year start, mid-season break, year end, cadence and forecast horizon.
- Select wells and choose **Schedule selected**; inspect and manually edit onstream dates.
- Compare oil/gas wedges and annual capex charts as onstream dates change.
- Download annual, monthly, and per-well results; save and reload a scenario.

## Known prototype limitations

- No login or company access controls; assume all content is public.
- No shared database or persistent multi-user scenarios.
- Capital assigned to onstream month (not drilling or completion cash-flow timing).
- Scheduled wells spaced by a number of days, not modeled by rig-specific operations.
- Monthly gross well forecast volumes are netted using working interest.

For local debugging only, run `pip install -r requirements.txt` then `streamlit run app.py`.
