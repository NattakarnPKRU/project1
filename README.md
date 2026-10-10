# Streamlit Data Visualization

Interactive dashboard for the Industrial Production Index (MPI) dataset for
2026 (B.E. 2569), published by the Electrical and Electronics Institute on
[data.go.th](https://data.go.th/dataset/mpi-2569).

The app reads every XLS/XLSX monthly resource listed by the data.go.th CKAN API,
combines the records, and refreshes the live data every six hours. If the API is
temporarily unavailable, it clearly indicates that it is showing the bundled
`data/mpi_2569.xlsx` snapshot instead. The dashboard also lets you download the
combined data currently displayed.

## Dashboard

- Thai-language sidebar filters for month, industry group, and product ranking.
- Summary metrics, including weighted MPI, change from the previous month,
  total weight, and the highest-index product.
- Monthly weighted MPI trend, product-group weight-share doughnut chart, and
  top-product ranking.
- Product-level `Weight` versus `IndexValue` scatter plot and data table.
- Excel download for all months and CSV download for the filtered month.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app_dash.py
```

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**.
3. Select the repository and branch, then set the main file path to `app_dash.py`.
4. Choose **Deploy**. Dependencies are installed from `requirements.txt`.
