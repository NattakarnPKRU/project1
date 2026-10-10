from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "mpi_2569.xlsx"
REQUIRED_COLUMNS = {
    "IndexYear",
    "IndexMonth",
    "CommodityNameTH",
    "ProductGroupID",
    "Weight",
    "IndexValue",
}
ALL_GROUPS = "ทั้งหมด"

st.set_page_config(
    page_title="ดัชนีสินค้า | Data Visualization",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner="กำลังโหลดข้อมูล...")
def load_data() -> pd.DataFrame:
    return pd.read_excel(DATA_FILE, sheet_name="data", engine="openpyxl")


st.title("ดัชนีสินค้าและน้ำหนัก")
st.caption("Streamlit Data Visualization | ข้อมูลจากชุดแบบฝึกหัด")

if not DATA_FILE.is_file():
    st.error(f"ไม่พบไฟล์ข้อมูล: {DATA_FILE}")
    st.stop()

data = load_data()
missing_columns = REQUIRED_COLUMNS.difference(data.columns)
if missing_columns:
    st.error(f"ไฟล์ข้อมูลขาดคอลัมน์ที่จำเป็น: {', '.join(sorted(missing_columns))}")
    st.stop()
if data.empty:
    st.error("ไม่พบข้อมูลในชีต data")
    st.stop()

periods = (
    data[["IndexYear", "IndexMonth"]]
    .dropna()
    .drop_duplicates()
    .sort_values(["IndexYear", "IndexMonth"])
)
period = ", ".join(
    f"{int(row.IndexMonth):02d}/{int(row.IndexYear)}"
    for row in periods.itertuples(index=False)
)
st.caption(f"ช่วงข้อมูลในไฟล์: {period} | จำนวนข้อมูล: {len(data):,} รายการ")

groups = sorted(data["ProductGroupID"].dropna().unique().tolist())
left_filter, right_filter = st.columns(2)
with left_filter:
    selected_group = st.selectbox(
        "เลือกกลุ่มสินค้า",
        options=[ALL_GROUPS, *groups],
        format_func=lambda group: (
            ALL_GROUPS if group == ALL_GROUPS else f"กลุ่ม {group}"
        ),
    )

filtered_data = data
if selected_group != ALL_GROUPS:
    filtered_data = data.loc[data["ProductGroupID"] == selected_group]

with right_filter:
    top_n = st.slider(
        "จำนวนสินค้าที่แสดงในกราฟแท่ง",
        min_value=1,
        max_value=len(filtered_data),
        value=min(10, len(filtered_data)),
    )

average_index = filtered_data["IndexValue"].mean()
highest_row = filtered_data.loc[filtered_data["IndexValue"].idxmax()]
metric_columns = st.columns(3)
metric_columns[0].metric("จำนวนรายการ", f"{len(filtered_data):,}")
metric_columns[1].metric("ค่า IndexValue เฉลี่ย", f"{average_index:,.2f}")
metric_columns[2].metric(
    "IndexValue สูงสุด",
    f"{highest_row['IndexValue']:,.2f}",
    help=str(highest_row["CommodityNameTH"]),
)

top_items = filtered_data.nlargest(top_n, "IndexValue")
bar_chart = (
    alt.Chart(top_items)
    .mark_bar()
    .encode(
        x=alt.X("IndexValue:Q", title="IndexValue"),
        y=alt.Y("CommodityNameTH:N", sort="-x", title="สินค้า"),
        color=alt.Color("ProductGroupID:N", title="กลุ่มสินค้า"),
        tooltip=[
            alt.Tooltip("CommodityNameTH:N", title="สินค้า"),
            alt.Tooltip("ProductGroupID:N", title="กลุ่มสินค้า"),
            alt.Tooltip("Weight:Q", title="Weight", format=".4f"),
            alt.Tooltip("IndexValue:Q", title="IndexValue", format=".2f"),
        ],
    )
    .properties(height=max(300, 28 * len(top_items)))
)

scatter_chart = (
    alt.Chart(filtered_data)
    .mark_circle(size=100, opacity=0.8)
    .encode(
        x=alt.X("Weight:Q", title="Weight"),
        y=alt.Y("IndexValue:Q", title="IndexValue"),
        color=alt.Color("ProductGroupID:N", title="กลุ่มสินค้า"),
        tooltip=[
            alt.Tooltip("CommodityNameTH:N", title="สินค้า"),
            alt.Tooltip("ProductGroupID:N", title="กลุ่มสินค้า"),
            alt.Tooltip("Weight:Q", title="Weight", format=".4f"),
            alt.Tooltip("IndexValue:Q", title="IndexValue", format=".2f"),
        ],
    )
    .properties(height=380)
)

chart_columns = st.columns(2)
with chart_columns[0]:
    st.subheader(f"{top_n} สินค้าที่มี IndexValue สูง")
    st.altair_chart(bar_chart, width="stretch")
with chart_columns[1]:
    st.subheader("ความสัมพันธ์ระหว่าง Weight และ IndexValue")
    st.altair_chart(scatter_chart, width="stretch")

with st.expander("ดูข้อมูลในตาราง"):
    st.dataframe(
        filtered_data.rename(
            columns={
                "IndexYear": "ปี",
                "IndexMonth": "เดือน",
                "CommodityNameTH": "สินค้า",
                "ProductGroupID": "กลุ่มสินค้า",
                "Weight": "Weight",
                "IndexValue": "IndexValue",
            }
        ),
        width="stretch",
        hide_index=True,
    )

st.caption("หมายเหตุ: ชุดข้อมูลมีเพียงเดือนเดียว จึงใช้กราฟเปรียบเทียบรายการสินค้า")
