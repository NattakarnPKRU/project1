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

MONTH_NAMES_TH = {
    1: "มกราคม",
    2: "กุมภาพันธ์",
    3: "มีนาคม",
    4: "เมษายน",
    5: "พฤษภาคม",
    6: "มิถุนายน",
    7: "กรกฎาคม",
    8: "สิงหาคม",
    9: "กันยายน",
    10: "ตุลาคม",
    11: "พฤศจิกายน",
    12: "ธันวาคม",
}
GROUP_NAMES_TH = {
    1: "เครื่องใช้ไฟฟ้า",
    2: "อิเล็กทรอนิกส์",
}
latest_year, latest_month = period_options[-1]
month_data_latest = data.loc[
    (data["IndexYear"] == latest_year) & (data["IndexMonth"] == latest_month)
]
groups = sorted(data["ProductGroupID"].dropna().unique().tolist())

st.markdown(
    """
    <style>
    :root {
        --mpi-ink: #183153;
        --mpi-muted: #64748b;
        --mpi-primary: #1877a8;
        --mpi-accent: #14a98b;
        --mpi-surface: #ffffff;
        --mpi-border: #e5edf3;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 95% 0%, rgba(20, 169, 139, 0.08), transparent 28rem),
            #f5f8fb;
    }
    [data-testid="stHeader"] { background: rgba(245, 248, 251, 0.88); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #edf5f8 0%, #f7fafc 100%);
        border-right: 1px solid var(--mpi-border);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: var(--mpi-ink);
        font-size: 1.08rem;
    }
    .mpi-hero {
        padding: 1.5rem 1.7rem;
        border: 1px solid rgba(206, 226, 236, 0.9);
        border-radius: 22px;
        background: linear-gradient(115deg, #ffffff 0%, #eef8f8 60%, #edf5fb 100%);
        box-shadow: 0 12px 36px rgba(31, 70, 94, 0.07);
        margin: 0.4rem 0 1.25rem;
    }
    .mpi-eyebrow {
        color: #167a82;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .mpi-hero h1 {
        color: var(--mpi-ink);
        font-size: clamp(1.65rem, 3vw, 2.35rem);
        line-height: 1.2;
        margin: 0;
    }
    .mpi-hero p {
        color: var(--mpi-muted);
        font-size: 1rem;
        margin: 0.55rem 0 0;
    }
    .mpi-section-note {
        color: var(--mpi-muted);
        font-size: 0.9rem;
        margin: -0.45rem 0 0.8rem;
    }
    div[data-testid="stMetric"] {
        background: var(--mpi-surface);
        border: 1px solid var(--mpi-border);
        border-radius: 16px;
        padding: 1rem 1.05rem;
        box-shadow: 0 4px 16px rgba(31, 70, 94, 0.04);
    }
    div[data-testid="stMetricLabel"] p {
        color: var(--mpi-muted);
        font-size: 0.88rem;
    }
    div[data-testid="stMetricValue"] {
        color: var(--mpi-ink);
        font-size: 1.75rem;
    }
    div[data-testid="stTabs"] button {
        border-radius: 10px 10px 0 0;
        font-weight: 650;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--mpi-border);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.82);
    }
    @media (max-width: 760px) {
        .mpi-hero { padding: 1.2rem; border-radius: 16px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🔎 ปรับมุมมองข้อมูล")
    st.caption("เลือกช่วงเวลาและกลุ่มสินค้าเพื่อกรองข้อมูล")
    selected_period = st.selectbox(
        "เดือนที่ต้องการวิเคราะห์",
        options=period_options,
        index=len(period_options) - 1,
        format_func=lambda period: (
            f"{MONTH_NAMES_TH[period[1]]} {period[0] + 543}"
        ),
    )
    selected_year, selected_month = selected_period
    selected_group = st.selectbox(
        "กลุ่มอุตสาหกรรม",
        options=[ALL_GROUPS, *groups],
        format_func=lambda group: (
            ALL_GROUPS
            if group == ALL_GROUPS
            else GROUP_NAMES_TH.get(group, f"กลุ่ม {group}")
        ),
    )
    month_data_for_filter = data.loc[
        (data["IndexYear"] == selected_year)
        & (data["IndexMonth"] == selected_month)
    ]
    selected_products = month_data_for_filter
    if selected_group != ALL_GROUPS:
        selected_products = month_data_for_filter.loc[
            month_data_for_filter["ProductGroupID"] == selected_group
        ]
    top_n = st.slider(
        "จำนวนสินค้าในอันดับ",
        min_value=3,
        max_value=max(3, len(selected_products)),
        value=min(8, max(3, len(selected_products))),
        help="เลือกจำนวนรายการที่ต้องการแสดงในกราฟจัดอันดับ",
    )
    st.divider()
    st.markdown("### 📥 ดาวน์โหลดข้อมูล")
    download = BytesIO()
    with pd.ExcelWriter(download, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="MPI ครบทุกเดือน", index=False)
    st.download_button(
        "ดาวน์โหลด Excel ครบทุกเดือน",
        data=download.getvalue(),
        file_name="mpi_2569.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )
    st.link_button(
        "เปิดแหล่งข้อมูล data.go.th",
        DATASET_URL,
        use_container_width=True,
    )
    st.caption(f"ข้อมูล {resource_count} เดือน · รวม {len(data):,} รายการ")

st.markdown(
    f"""
    <div class="mpi-hero">
      <div class="mpi-eyebrow">DATA DASHBOARD · MPI 2569</div>
      <h1>ดัชนีผลผลิตอุตสาหกรรม</h1>
      <p>สำรวจข้อมูลสินค้า กลุ่มอุตสาหกรรม และแนวโน้มรายเดือน
      · ข้อมูลล่าสุด {MONTH_NAMES_TH[latest_month]} {latest_year + 543}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

current_data = data.loc[
    (data["IndexYear"] == selected_year) & (data["IndexMonth"] == selected_month)
].copy()
trend_data = data.copy()
if selected_group != ALL_GROUPS:
    current_data = current_data.loc[
        current_data["ProductGroupID"] == selected_group
    ].copy()
    trend_data = trend_data.loc[
        trend_data["ProductGroupID"] == selected_group
    ].copy()

period_index = period_options.index(selected_period)
previous_data = pd.DataFrame()
if period_index > 0:
    previous_year, previous_month = period_options[period_index - 1]
    previous_data = data.loc[
        (data["IndexYear"] == previous_year)
        & (data["IndexMonth"] == previous_month)
    ].copy()
    if selected_group != ALL_GROUPS:
        previous_data = previous_data.loc[
            previous_data["ProductGroupID"] == selected_group
        ]

if current_data.empty:
    st.warning("ไม่มีข้อมูลสำหรับตัวกรองที่เลือก")
    st.stop()

total_weight = current_data["Weight"].sum()
weighted_index = (
    (current_data["Weight"] * current_data["IndexValue"]).sum() / total_weight
    if total_weight
    else current_data["IndexValue"].mean()
)
previous_weighted_index = None
if not previous_data.empty:
    previous_total_weight = previous_data["Weight"].sum()
    previous_weighted_index = (
        (previous_data["Weight"] * previous_data["IndexValue"]).sum()
        / previous_total_weight
        if previous_total_weight
        else previous_data["IndexValue"].mean()
    )
index_change = (
    weighted_index - previous_weighted_index
    if previous_weighted_index is not None
    else None
)
change_percent = (
    index_change / previous_weighted_index * 100
    if previous_weighted_index
    else None
)
change_delta = (
    f"{index_change:+,.2f} จุด ({change_percent:+.1f}%) เทียบเดือนก่อน"
    if index_change is not None and change_percent is not None
    else "ยังไม่มีเดือนก่อนหน้าให้เปรียบเทียบ"
)
top_product = current_data.loc[current_data["IndexValue"].idxmax()]
period_label = f"{MONTH_NAMES_TH[selected_month]} {selected_year + 543}"

st.markdown(f"#### สรุปข้อมูล · {period_label}")
st.markdown(
    '<p class="mpi-section-note">ตัวชี้วัดสรุปจากข้อมูลในเดือนและกลุ่มที่เลือก</p>',
    unsafe_allow_html=True,
)
metric_columns = st.columns(4)
metric_columns[0].metric(
    "ดัชนีถ่วงน้ำหนัก",
    f"{weighted_index:,.1f}",
    delta=change_delta,
    help="คำนวณจากผลรวม Weight × IndexValue หารด้วยผลรวม Weight",
)
metric_columns[1].metric(
    "สินค้าในมุมมอง",
    f"{len(current_data):,} รายการ",
)
metric_columns[2].metric(
    "น้ำหนักรวม",
    f"{total_weight:,.2f}",
)
metric_columns[3].metric(
    "ดัชนีสูงสุด",
    f"{top_product['IndexValue']:,.1f}",
    help=str(top_product["CommodityNameTH"]),
)

monthly_weighted = (
    trend_data.assign(
        WeightedIndex=trend_data["Weight"] * trend_data["IndexValue"]
    )
    .groupby(["IndexYear", "IndexMonth", "ProductGroupID"], as_index=False)
    .agg(
        WeightedIndex=("WeightedIndex", "sum"),
        TotalWeight=("Weight", "sum"),
    )
)
monthly_weighted["MPI ถ่วงน้ำหนัก"] = (
    monthly_weighted["WeightedIndex"] / monthly_weighted["TotalWeight"]
)
month_abbreviations_th = {
    1: "ม.ค.",
    2: "ก.พ.",
    3: "มี.ค.",
    4: "เม.ย.",
    5: "พ.ค.",
    6: "มิ.ย.",
    7: "ก.ค.",
    8: "ส.ค.",
    9: "ก.ย.",
    10: "ต.ค.",
    11: "พ.ย.",
    12: "ธ.ค.",
}
monthly_weighted["เดือน"] = monthly_weighted["IndexMonth"].map(
    lambda month: month_abbreviations_th[int(month)]
)
monthly_weighted["กลุ่มอุตสาหกรรม"] = monthly_weighted["ProductGroupID"].map(
    lambda group: GROUP_NAMES_TH.get(group, f"กลุ่ม {group}")
)
monthly_weighted["ลำดับเดือน"] = (
    monthly_weighted["IndexYear"] * 100 + monthly_weighted["IndexMonth"]
)
trend_chart = (
    alt.Chart(monthly_weighted)
    .mark_line(point=alt.OverlayMarkDef(size=75, filled=True), strokeWidth=3)
    .encode(
        x=alt.X(
            "เดือน:N",
            sort=monthly_weighted.sort_values("ลำดับเดือน")["เดือน"]
            .drop_duplicates()
            .tolist(),
            title="เดือน",
        ),
        y=alt.Y("MPI ถ่วงน้ำหนัก:Q", title="ดัชนีถ่วงน้ำหนัก"),
        color=alt.Color("กลุ่มอุตสาหกรรม:N", title="กลุ่มอุตสาหกรรม"),
        tooltip=[
            alt.Tooltip("เดือน:N", title="เดือน"),
            alt.Tooltip("กลุ่มอุตสาหกรรม:N", title="กลุ่ม"),
            alt.Tooltip("MPI ถ่วงน้ำหนัก:Q", title="ดัชนีถ่วงน้ำหนัก", format=".2f"),
        ],
    )
    .properties(height=330)
)

group_weight = (
    current_data.groupby("ProductGroupID", as_index=False)["Weight"]
    .sum()
    .rename(columns={"Weight": "น้ำหนักรวม"})
)
group_weight["กลุ่มอุตสาหกรรม"] = group_weight["ProductGroupID"].map(
    lambda group: GROUP_NAMES_TH.get(group, f"กลุ่ม {group}")
)
weight_share_chart = (
    alt.Chart(group_weight)
    .mark_arc(innerRadius=72, outerRadius=118, cornerRadius=5)
    .encode(
        theta=alt.Theta("น้ำหนักรวม:Q"),
        color=alt.Color("กลุ่มอุตสาหกรรม:N", title="กลุ่มอุตสาหกรรม"),
        tooltip=[
            alt.Tooltip("กลุ่มอุตสาหกรรม:N", title="กลุ่ม"),
            alt.Tooltip("น้ำหนักรวม:Q", title="น้ำหนัก", format=".2f"),
        ],
    )
    .properties(height=330)
)

top_items = current_data.nlargest(min(top_n, len(current_data)), "IndexValue")
top_items = top_items.assign(
    **{
        "สินค้า": top_items["CommodityNameTH"],
        "กลุ่มอุตสาหกรรม": top_items["ProductGroupID"].map(
            lambda group: GROUP_NAMES_TH.get(group, f"กลุ่ม {group}")
        ),
    }
)
ranking_chart = (
    alt.Chart(top_items)
    .mark_bar(cornerRadiusEnd=5)
    .encode(
        x=alt.X("IndexValue:Q", title="ค่าดัชนี"),
        y=alt.Y("สินค้า:N", sort="-x", title=None),
        color=alt.Color("กลุ่มอุตสาหกรรม:N", title="กลุ่มอุตสาหกรรม"),
        tooltip=[
            alt.Tooltip("สินค้า:N", title="สินค้า"),
            alt.Tooltip("กลุ่มอุตสาหกรรม:N", title="กลุ่ม"),
            alt.Tooltip("Weight:Q", title="น้ำหนัก", format=".4f"),
            alt.Tooltip("IndexValue:Q", title="ค่าดัชนี", format=".2f"),
        ],
    )
    .properties(height=max(300, 32 * len(top_items)))
)

scatter_data = current_data.assign(
    **{
        "สินค้า": current_data["CommodityNameTH"],
        "กลุ่มอุตสาหกรรม": current_data["ProductGroupID"].map(
            lambda group: GROUP_NAMES_TH.get(group, f"กลุ่ม {group}")
        ),
    }
)
scatter_chart = (
    alt.Chart(scatter_data)
    .mark_circle(size=125, opacity=0.8, stroke="white", strokeWidth=1)
    .encode(
        x=alt.X("Weight:Q", title="น้ำหนักสินค้า (Weight)"),
        y=alt.Y("IndexValue:Q", title="ดัชนีสินค้า (IndexValue)"),
        color=alt.Color("กลุ่มอุตสาหกรรม:N", title="กลุ่มอุตสาหกรรม"),
        size=alt.Size("Weight:Q", legend=None, scale=alt.Scale(range=[60, 500])),
        tooltip=[
            alt.Tooltip("สินค้า:N", title="สินค้า"),
            alt.Tooltip("กลุ่มอุตสาหกรรม:N", title="กลุ่ม"),
            alt.Tooltip("Weight:Q", title="Weight", format=".4f"),
            alt.Tooltip("IndexValue:Q", title="IndexValue", format=".2f"),
        ],
    )
    .properties(height=380)
)

st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
    gap:1rem;flex-wrap:wrap;margin:.4rem 0 .7rem">
      <div>
        <h3 style="color:#183153;margin:0">สำรวจข้อมูลเชิงลึก</h3>
        <span style="color:#64748b">เลือกดูแนวโน้ม สัดส่วน และรายละเอียดสินค้า</span>
      </div>
      <span style="background:#e8f5f2;color:#167a68;padding:.4rem .75rem;
      border-radius:99px;font-weight:650">● {period_label}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

overview_tab, product_tab, data_tab = st.tabs(
    ["📊 ภาพรวมตลาด", "🔍 วิเคราะห์สินค้า", "📋 รายการข้อมูล"]
)
with overview_tab:
    trend_column, share_column = st.columns([1.55, 1])
    with trend_column:
        with st.container(border=True):
            st.markdown("#### แนวโน้ม MPI รายเดือน")
            st.caption("ดัชนีถ่วงน้ำหนักของแต่ละกลุ่มในเดือนที่มีข้อมูล")
            st.altair_chart(trend_chart, width="stretch")
    with share_column:
        with st.container(border=True):
            st.markdown("#### สัดส่วนน้ำหนักสินค้า")
            st.caption("ส่วนประกอบของน้ำหนักในเดือนที่เลือก")
            st.altair_chart(weight_share_chart, width="stretch")
    with st.container(border=True):
        st.markdown("#### สินค้าที่มีดัชนีสูง")
        st.caption("รายการสินค้าสูงสุดตามจำนวนที่เลือกในแถบด้านข้าง")
        st.altair_chart(ranking_chart, width="stretch")

with product_tab:
    scatter_column, ranking_column = st.columns([1.15, 1])
    with scatter_column:
        with st.container(border=True):
            st.markdown("#### น้ำหนักเทียบกับดัชนี")
            st.caption(
                "แต่ละจุดคือสินค้า · วางเมาส์เพื่อดูรายละเอียด"
            )
            st.altair_chart(scatter_chart, width="stretch")
    with ranking_column:
        with st.container(border=True):
            st.markdown("#### รายละเอียดสินค้า")
            st.caption(
                f"เรียง {len(top_items)} รายการตาม IndexValue จากมากไปน้อย"
            )
            st.dataframe(
                top_items[
                    ["CommodityNameTH", "ProductGroupID", "Weight", "IndexValue"]
                ].rename(
                    columns={
                        "CommodityNameTH": "สินค้า",
                        "ProductGroupID": "กลุ่ม",
                        "Weight": "น้ำหนัก",
                        "IndexValue": "ดัชนี",
                    }
                ),
                width="stretch",
                hide_index=True,
                height=420,
            )
    st.caption(
        "หมายเหตุ: Weight และ IndexValue เป็นค่าตามนิยามของชุดข้อมูลต้นทาง "
        "ควรพิจารณาร่วมกับรายละเอียดและบริบทของแต่ละรายการ"
    )

with data_tab:
    st.markdown("#### ข้อมูลต้นทางสำหรับตรวจสอบและวิเคราะห์ต่อ")
    st.caption(
        f"แสดง {len(current_data):,} รายการ · ใช้ตัวกรองเดือนและกลุ่มอุตสาหกรรมจากแถบด้านข้าง"
    )
    table_data = current_data.rename(
        columns={
            "IndexYear": "ปี",
            "IndexMonth": "เดือน",
            "CommodityNameTH": "สินค้า",
            "ProductGroupID": "กลุ่มสินค้า",
            "Weight": "น้ำหนัก",
            "IndexValue": "ดัชนีสินค้า",
        }
    )
    st.dataframe(table_data, width="stretch", hide_index=True)
    st.download_button(
        "ดาวน์โหลดเฉพาะข้อมูลที่กรอง (.csv)",
        data=table_data.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"mpi_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    f"แหล่งข้อมูล: สถาบันไฟฟ้าและอิเล็กทรอนิกส์ · "
    f"[data.go.th]({DATASET_URL}) · อัปเดตข้อมูลอัตโนมัติทุก 6 ชั่วโมง"
)
