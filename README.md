# Development Program Planner — public Gantt demo

Synthetic well inventory only. **Never enter or upload proprietary company information in this public demo.**

## Deploy to Streamlit Community Cloud

1. Create or open your GitHub repository (for example `well-development-planner`).
2. Upload the **contents of this folder** to the repository root: `app.py`, `engine.py`, `requirements.txt`, `sample_well_database.xlsx`, `README.md`. Choose **Commit changes**. When updating an older version, overwrite the existing files.
3. In Streamlit Community Cloud, choose the correct GitHub repository, branch (`main` if that is the branch shown in GitHub), and main file path `app.py`.
4. Deploy/reboot your app. No Python installation is needed on viewers' computers.

## Test the Gantt planner

* Open the **Drag-and-drop development schedule** section.
* Drag an existing colored well bar left/right to modify its onstream date. The production wedge and capital profile will recalculate after each accepted move.
* Switch between month and week timeline views. The gray area is the inclusive mid-season break; moving wells there or outside the year start/end dates is blocked.
* Use **Edit exact well dates / schedule unscheduled wells** to set dates for entities with no bar. Click **Apply edited dates**.
* The sample formations are **Formation 1** and **Formation 2** throughout the Excel database and UI.
* Download CSV outputs or a scenario JSON as required.

The Gantt chart uses streamlit-calendar / FullCalendar's resource timeline feature and the GPL key for a publicly available open-source demonstration; review license suitability before proprietary or commercial deployment. Dragging modifies onstream date only, not a drilling/completion duration. Capital remains assumed to be paid in the onstream month. Streamlit sessions are not a shared team database.
