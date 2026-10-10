# Waste Management Data Dashboard

Interactive dashboard for the solid-waste statistics published by Thailand's
Department of National Parks, Wildlife and Plant Conservation.

The dashboard reads the bundled Excel workbook
`data/ปริมาณขยะมูลฝอย.xlsx` directly; it makes no requests to external websites.
To update the dashboard data, replace this workbook with the latest Excel file
and redeploy the app. The dashboard includes monthly trends, waste handling
totals, agency comparisons, interactive month and agency selection from charts,
and a detailed filtered data table.

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
