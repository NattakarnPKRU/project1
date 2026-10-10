# Waste Management Data Dashboard

Interactive dashboard for the solid-waste statistics published by Thailand's
Department of National Parks, Wildlife and Plant Conservation on
[data.go.th](https://data.go.th/dataset/gdpublish-69-dnp01-11-01).

The dashboard combines the XLSX resources for B.E. 2568 and B.E. 2569 from the
data.go.th CKAN API and refreshes them every six hours. It includes monthly
trends, waste handling totals, agency comparisons, interactive month and agency
selection from charts, and a detailed filtered data table. If the API is
temporarily unavailable, the bundled `data/waste_management_2568_2569.xlsx`
snapshot is used.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app_dash.py
```

## Deploy to Streamlit Community Cloud

1. Push the project to a GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**.
3. Select the repository and branch, then set the main file path to `app_dash.py`.
4. Choose **Deploy**. Dependencies are installed from `requirements.txt`.
