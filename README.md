# Streamlit Data Visualization

Dashboard for the exercise dataset, showing product index values and weights.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app_dash.py
```

The workbook is stored in `data/mpi_2569.xlsx` and is read from the app directory,
so the dashboard does not depend on a local Downloads folder.

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**.
3. Select the repository and branch, then set the main file path to `app_dash.py`.
4. Choose **Deploy**. Dependencies are installed from `requirements.txt`.
