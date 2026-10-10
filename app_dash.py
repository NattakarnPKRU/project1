from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st


DATASET_API_URL = "https://data.go.th/api/3/action/package_show?id=mpi-2569"
DATASET_URL = "https://data.go.th/dataset/mpi-2569"
SNAPSHOT_FILE = Path(__file__).parent / "data" / "mpi_2569.xlsx"
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
    page_title="ดัชนีผลผลิตอุตสาหกรรม MPI 2569",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="กำลังดึงข้อมูล MPI จาก data.go.th...")
def load_data() -> tuple[pd.DataFrame, int]:
    response = requests.get(DATASET_API_URL, timeout=(10, 30))
    response.raise_for_status()
    package = response.json()
    if not package.get("success") or not isinstance(package.get("result"), dict):
        raise ValueError("data.go.th ไม่พบ dataset mpi-2569")

    resources = package["result"].get("resources", [])
    monthly_resources = [
        resource
        for resource in resources
        if resource.get("format", "").upper() in {"XLS", "XLSX"}
    ]
    if not monthly_resources:
        raise ValueError("dataset ไม่มีไฟล์ XLS/XLSX รายเดือน")

    frames = []
    for resource in monthly_resources:
        url = resource.get("url")
        if not url:
            raise ValueError(f"ไม่พบ URL ของ resource: {resource.get('name', 'ไม่ทราบชื่อ')}")
        file_response = requests.get(url, timeout=(10, 60))
        file_response.raise_for_status()
        frame = pd.read_excel(
            BytesIO(file_response.content),
            sheet_name="data",
            engine="openpyxl",
        )
        missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
        if missing_columns:
            raise ValueError(
                f"ไฟล์ {resource.get('name', url)} ขาดคอลัมน์: "
                f"{', '.join(sorted(missing_columns))}"
            )
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    if data.empty:
        raise ValueError("ไม่พบรายการข้อมูลใน resource รายเดือน")
    return data, len(monthly_resources)


st.title("ดัชนีผลผลิตอุตสาหกรรม (MPI) ปี 2569")
st.caption("ข้อมูลรายเดือนจากสถาบันไฟฟ้าและอิเล็กทรอนิกส์ ผ่าน data.go.th")

try:
    data, resource_count = load_data()
except requests.RequestException as error:
    if not SNAPSHOT_FILE.is_file():
        st.error(f"ดึงข้อมูลจาก data.go.th ไม่สำเร็จ: {error}")
        st.link_button("เปิดชุดข้อมูล data.go.th", DATASET_URL)
        st.stop()
    data = pd.read_excel(SNAPSHOT_FILE, sheet_name="data", engine="openpyxl")
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        st.error(
            f"ไฟล์ข้อมูลสำรองขาดคอลัมน์ที่จำเป็น: "
            f"{', '.join(sorted(missing_columns))}"
        )
        st.stop()
    resource_count = data[["IndexYear", "IndexMonth"]].drop_duplicates().shape[0]
    st.warning(
        f"ดึงข้อมูลสดจาก data.go.th ไม่สำเร็จ ({error}) "
        "จึงแสดงข้อมูลสำรองที่รวมอยู่ในโครงการ"
    )
except (ValueError, KeyError) as error:
    st.error(f"ดึงข้อมูลจาก data.go.th ไม่สำเร็จ: {error}")
    st.link_button("เปิดชุดข้อมูล data.go.th", DATASET_URL)
    st.stop()

periods = (
    data[["IndexYear", "IndexMonth"]]
    .dropna()
    .drop_duplicates()
    .sort_values(["IndexYear", "IndexMonth"])
)
period_options = [
    (int(row.IndexYear), int(row.IndexMonth))
    for row in periods.itertuples(index=False)
]
if not period_options:
    st.error("ข้อมูลจาก data.go.th ไม่มีปีและเดือนที่ใช้งานได้")
    st.stop()

latest_year, latest_month = period_options[-1]
st.caption(
    f"โหลด {resource_count} ไฟล์รายเดือน ครอบคลุม "
    f"{len(period_options)} เดือน | รวม {len(data):,} รายการ"
)
download = BytesIO()
with pd.ExcelWriter(download, engine="openpyxl") as writer:
    data.to_excel(writer, sheet_name="data", index=False)
st.download_button(
    "ดาวน์โหลดข้อมูล MPI ครบทุกเดือน (.xlsx)",
    data=download.getvalue(),
    file_name="mpi_2569.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

month_column, group_column, top_n_column = st.columns(3)
with month_column:
    selected_year, selected_month = st.selectbox(
        "เลือกเดือน",
        options=period_options,
        index=len(period_options) - 1,
        format_func=lambda period: f"{period[1]:02d}/{period[0]}",
    )

month_data = data.loc[
    (data["IndexYear"] == selected_year)
    & (data["IndexMonth"] == selected_month)
]
groups = sorted(month_data["ProductGroupID"].dropna().unique().tolist())
with group_column:
    selected_group = st.selectbox(
        "เลือกกลุ่มสินค้า",
        options=[ALL_GROUPS, *groups],
        format_func=lambda group: (
            ALL_GROUPS if group == ALL_GROUPS else f"กลุ่ม {group}"
        ),
    )

filtered_month = month_data
trend_data = data
if selected_group != ALL_GROUPS:
    filtered_month = month_data.loc[
        month_data["ProductGroupID"] == selected_group
    ]
    trend_data = data.loc[data["ProductGroupID"] == selected_group]

with top_n_column:
    top_n = st.slider(
        "จำนวนสินค้าในกราฟแท่ง",
        min_value=1,
        max_value=len(filtered_month),
        value=min(10, len(filtered_month)),
    )

average_index = filtered_month["IndexValue"].mean()
highest_row = filtered_month.loc[filtered_month["IndexValue"].idxmax()]
metric_columns = st.columns(3)
metric_columns[0].metric("จำนวนรายการ", f"{len(filtered_month):,}")
metric_columns[1].metric("ค่า IndexValue เฉลี่ย", f"{average_index:,.2f}")
metric_columns[2].metric(
    "IndexValue สูงสุด",
    f"{highest_row['IndexValue']:,.2f}",
    help=str(highest_row["CommodityNameTH"]),
)

monthly_average = (
    trend_data.groupby(
        ["IndexYear", "IndexMonth", "ProductGroupID"], as_index=False
    )["IndexValue"]
    .mean()
    .rename(columns={"IndexValue": "AverageIndexValue"})
)
monthly_average["Period"] = pd.to_datetime(
    {
        "year": monthly_average["IndexYear"],
        "month": monthly_average["IndexMonth"],
        "day": 1,
    }
)
trend_chart = (
    alt.Chart(monthly_average)
    .mark_line(point=True)
    .encode(
        x=alt.X("Period:T", title="เดือน", axis=alt.Axis(format="%b %Y")),
        y=alt.Y("AverageIndexValue:Q", title="ค่าเฉลี่ย IndexValue"),
        color=alt.Color("ProductGroupID:N", title="กลุ่มสินค้า"),
        tooltip=[
            alt.Tooltip("Period:T", title="เดือน", format="%m/%Y"),
            alt.Tooltip("ProductGroupID:N", title="กลุ่มสินค้า"),
            alt.Tooltip("AverageIndexValue:Q", title="ค่าเฉลี่ย IndexValue", format=".2f"),
        ],
    )
    .properties(height=350)
)

top_items = filtered_month.nlargest(top_n, "IndexValue")
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
    alt.Chart(filtered_month)
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
    .properties(height=350)
)

st.subheader("แนวโน้มค่าเฉลี่ยรายเดือน")
st.caption("ค่าเฉลี่ย IndexValue ของสินค้าในแต่ละกลุ่ม")
st.altair_chart(trend_chart, width="stretch")

chart_columns = st.columns(2)
with chart_columns[0]:
    st.subheader(f"{top_n} สินค้า IndexValue สูง | {selected_month:02d}/{selected_year}")
    st.altair_chart(bar_chart, width="stretch")
with chart_columns[1]:
    st.subheader(f"Weight เทียบกับ IndexValue | {selected_month:02d}/{selected_year}")
    st.altair_chart(scatter_chart, width="stretch")

with st.expander("ดูข้อมูลในตาราง"):
    st.dataframe(
        filtered_month.rename(
            columns={
                "IndexYear": "ปี",
                "IndexMonth": "เดือน",
                "CommodityNameTH": "สินค้า",
                "ProductGroupID": "กลุ่มสินค้า",
            }
        ),
        width="stretch",
        hide_index=True,
    )

st.caption(
    f"แหล่งข้อมูล: data.go.th | อัปเดตข้อมูลอัตโนมัติทุก 6 ชั่วโมง "
    f"(เดือนล่าสุดที่พบ: {latest_month:02d}/{latest_year})"
)
