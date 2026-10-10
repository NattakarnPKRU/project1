import hashlib
from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st


DATASET_ID = "gdpublish-69-dnp01-11-01"
PUBLISHER_DATASET_ID = "5fd1ccae-e476-4fc9-9348-b1eaed66e00b"
DATASET_API_URL = (
    "https://catalog.dnp.go.th/api/3/action/"
    f"package_show?id={PUBLISHER_DATASET_ID}"
)
DATASET_URL = f"https://data.go.th/dataset/{DATASET_ID}"
SNAPSHOT_FILE = Path(__file__).parent / "data" / "waste_management_2568_2569.xlsx"
ALL = "ทั้งหมด"
ALL_PERIODS = "รวมทุกเดือน"
MONTHS_TH = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]
MONTH_ORDER = {month: index for index, month in enumerate(MONTHS_TH, start=1)}
REUSED_COLUMN = "นำไปใช้ประโยชน์ (กก.)"
GENERATED_COLUMN = "ขยะที่เกิดขึ้น (กก.)"
DISPOSED_COLUMN = "ขยะที่ส่งกำจัด (กก.)"
NUMERIC_COLUMNS = [
    "ปี",
    "คนเฉลี่ย",
    "วันทำงาน",
    "โฟมบรรจุอาหาร (ใบ)",
    GENERATED_COLUMN,
    REUSED_COLUMN,
    DISPOSED_COLUMN,
    "ร้อยละขยะส่งกำจัดลดลง",
]
REQUIRED_COLUMNS = {
    "ปี",
    "สังกัด",
    "หน่วยงาน",
    "เดือน",
    "คนเฉลี่ย",
    "วันทำงาน",
    GENERATED_COLUMN,
    REUSED_COLUMN,
    DISPOSED_COLUMN,
}

st.set_page_config(
    page_title="สถิติปริมาณขยะมูลฝอย",
    page_icon="♻️",
    layout="wide",
)


def normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    data = data.rename(
        columns={
            "ใช้ประโยชน์ (กก.)": REUSED_COLUMN,
            "นำไปใช้ประโยชน์ (กก.)": REUSED_COLUMN,
            "ร้อยละส่งกำจัดลดลง": "ร้อยละขยะส่งกำจัดลดลง",
        }
    ).copy()
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        raise ValueError(
            f"ไฟล์ข้อมูลขาดคอลัมน์ที่จำเป็น: {', '.join(sorted(missing_columns))}"
        )
    for column in NUMERIC_COLUMNS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    data["เดือน"] = data["เดือน"].astype("string").str.strip()
    data["สังกัด"] = data["สังกัด"].astype("string").str.strip()
    data["หน่วยงาน"] = data["หน่วยงาน"].astype("string").str.strip()
    data["เดือนที่"] = data["เดือน"].map(MONTH_ORDER)
    if data["เดือนที่"].isna().any():
        unknown_months = sorted(data.loc[data["เดือนที่"].isna(), "เดือน"].dropna().unique())
        raise ValueError(f"พบชื่อเดือนที่ไม่รู้จัก: {', '.join(unknown_months)}")
    return data


@st.cache_data(ttl=6 * 60 * 60, show_spinner="กำลังดึงข้อมูลจาก data.go.th...")
def load_data() -> tuple[pd.DataFrame, int]:
    response = requests.get(DATASET_API_URL, timeout=(10, 30))
    response.raise_for_status()
    package = response.json()
    if not package.get("success") or not isinstance(package.get("result"), dict):
        raise ValueError(f"ไม่พบชุดข้อมูล {DATASET_ID} บน data.go.th")

    resources = [
        resource
        for resource in package["result"].get("resources", [])
        if resource.get("format", "").upper() == "CSV"
    ]
    if not resources:
        raise ValueError("ชุดข้อมูลไม่มีไฟล์ CSV")

    frames = []
    for resource in resources:
        url = resource.get("url")
        if not url:
            raise ValueError(f"ไม่พบ URL ของไฟล์ {resource.get('name', 'ไม่ทราบชื่อ')}")
        file_response = requests.get(url, timeout=(10, 60))
        file_response.raise_for_status()
        frame = pd.read_csv(BytesIO(file_response.content), encoding="cp874")
        frames.append(normalize_columns(frame))

    data = pd.concat(frames, ignore_index=True)
    if data.empty:
        raise ValueError("ไม่พบรายการข้อมูลในไฟล์ของชุดข้อมูล")
    return data, len(resources)


try:
    data, resource_count = load_data()
except requests.RequestException as error:
    if not SNAPSHOT_FILE.is_file():
        st.error(f"ดึงข้อมูลจาก data.go.th ไม่สำเร็จ: {error}")
        st.link_button("เปิดชุดข้อมูลต้นทาง", DATASET_URL)
        st.stop()
    try:
        data = normalize_columns(
            pd.read_excel(SNAPSHOT_FILE, sheet_name="ข้อมูลขยะ")
        )
    except (OSError, ValueError, KeyError) as snapshot_error:
        st.error(f"โหลดข้อมูลสำรองไม่สำเร็จ: {snapshot_error}")
        st.stop()
    resource_count = data["ปี"].nunique()
    failure_reason = (
        f"HTTP {error.response.status_code}"
        if isinstance(error, requests.HTTPError) and error.response is not None
        else type(error).__name__
    )
    st.warning(
        f"ดึงข้อมูลล่าสุดจากแหล่งข้อมูลของกรมไม่สำเร็จ ({failure_reason}) "
        "ขณะนี้กำลังแสดงข้อมูลสำรองที่รวมอยู่ในโครงการ"
    )
except (ValueError, KeyError) as error:
    st.error(f"โหลดชุดข้อมูลไม่สำเร็จ: {error}")
    st.link_button("เปิดชุดข้อมูลต้นทาง", DATASET_URL)
    st.stop()

available_periods = sorted(
    {
        (int(row["ปี"]), int(row["เดือนที่"]))
        for _, row in data[["ปี", "เดือนที่"]].dropna().drop_duplicates().iterrows()
    }
)
if not available_periods:
    st.error("ไม่พบเดือนและปีที่ใช้งานได้ในชุดข้อมูล")
    st.stop()

PERIOD_LABELS = {
    f"{year}-{month:02d}": f"{MONTHS_TH[month - 1]} {year}"
    for year, month in available_periods
}
PERIOD_KEYS = {
    (year, month): f"{year}-{month:02d}"
    for year, month in available_periods
}
latest_period = PERIOD_KEYS[available_periods[-1]]
affiliations = sorted(data["สังกัด"].dropna().unique().tolist())
units = sorted(data["หน่วยงาน"].dropna().unique().tolist())


def selected_month_from_chart(chart_key: str) -> None:
    chart_state = st.session_state.get(chart_key, {})
    selected = chart_state.get("selection", {}).get("month_pick", [])
    if selected:
        period_key = selected[-1].get("period_id")
        if period_key in PERIOD_LABELS:
            st.session_state["period_filter"] = period_key


def selected_unit_from_chart(chart_key: str) -> None:
    chart_state = st.session_state.get(chart_key, {})
    selected = chart_state.get("selection", {}).get("unit_pick", [])
    if selected:
        unit = selected[-1].get("unit")
        if unit in units:
            st.session_state["unit_filter"] = [unit]


def reset_dashboard() -> None:
    st.session_state["period_filter"] = ALL_PERIODS
    st.session_state["affiliation_filter"] = ALL
    st.session_state["unit_filter"] = []
    st.session_state["chart_epoch"] = st.session_state.get("chart_epoch", 0) + 1


if "period_filter" not in st.session_state or st.session_state["period_filter"] not in [
    ALL_PERIODS,
    *PERIOD_LABELS,
]:
    st.session_state["period_filter"] = latest_period
if "affiliation_filter" not in st.session_state:
    st.session_state["affiliation_filter"] = ALL
if "unit_filter" not in st.session_state:
    st.session_state["unit_filter"] = []
if "chart_epoch" not in st.session_state:
    st.session_state["chart_epoch"] = 0

st.markdown(
    """
    <style>
    :root {
        --waste-ink: #183153;
        --waste-muted: #64748b;
        --waste-primary: #1877a8;
        --waste-green: #159978;
        --waste-border: #e5edf3;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 94% 0%, rgba(21, 153, 120, .075), transparent 27rem),
            #f5f8fb;
    }
    [data-testid="stHeader"] { background: rgba(245, 248, 251, .9); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #edf5f4 0%, #f7fafc 100%);
        border-right: 1px solid var(--waste-border);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: var(--waste-ink);
        font-size: 1.08rem;
    }
    .waste-hero {
        padding: 1.45rem 1.7rem;
        border: 1px solid rgba(206, 226, 236, .9);
        border-radius: 22px;
        background: linear-gradient(115deg, #fff 0%, #eff9f6 58%, #edf5fb 100%);
        box-shadow: 0 12px 36px rgba(31, 70, 94, .07);
        margin: .35rem 0 1.1rem;
    }
    .waste-eyebrow {
        color: #167a68;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .09em;
        margin-bottom: .35rem;
    }
    .waste-hero h1 {
        color: var(--waste-ink);
        font-size: clamp(1.6rem, 3vw, 2.25rem);
        line-height: 1.2;
        margin: 0;
    }
    .waste-hero p { color: var(--waste-muted); margin: .5rem 0 0; }
    .waste-note { color: var(--waste-muted); font-size: .9rem; }
    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid var(--waste-border);
        border-radius: 16px;
        padding: .95rem 1rem;
        box-shadow: 0 4px 16px rgba(31, 70, 94, .04);
    }
    div[data-testid="stMetricLabel"] p { color: var(--waste-muted); font-size: .88rem; }
    div[data-testid="stMetricValue"] { color: var(--waste-ink); font-size: 1.7rem; }
    div[data-testid="stTabs"] button { border-radius: 10px 10px 0 0; font-weight: 650; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--waste-border);
        border-radius: 16px;
        background: rgba(255, 255, 255, .84);
    }
    @keyframes chartReveal {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    [class*="st-key-animated-dashboard-"] {
        animation: chartReveal .42s cubic-bezier(.2, .75, .25, 1) both;
    }
    @media (prefers-reduced-motion: reduce) {
        [class*="st-key-animated-dashboard-"] { animation: none !important; }
    }
    @media (max-width: 760px) {
        .waste-hero { padding: 1.15rem; border-radius: 16px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

month_chart_key = f"waste_month_chart_{st.session_state['chart_epoch']}"
unit_chart_key = f"waste_unit_chart_{st.session_state['chart_epoch']}"

with st.sidebar:
    st.markdown("## 🔎 ตัวกรองข้อมูล")
    st.caption("คลิกเดือนหรือหน่วยงานบนกราฟเพื่อกรองข้อมูลได้เช่นกัน")
    st.selectbox(
        "เดือนและปี",
        options=[ALL_PERIODS, *PERIOD_LABELS],
        format_func=lambda key: ALL_PERIODS if key == ALL_PERIODS else PERIOD_LABELS[key],
        key="period_filter",
    )
    st.selectbox(
        "สังกัด",
        options=[ALL, *affiliations],
        key="affiliation_filter",
    )
    affiliation_units = (
        units
        if st.session_state["affiliation_filter"] == ALL
        else sorted(
            data.loc[
                data["สังกัด"] == st.session_state["affiliation_filter"], "หน่วยงาน"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )
    st.session_state["unit_filter"] = [
        unit
        for unit in st.session_state["unit_filter"]
        if unit in affiliation_units
    ]
    st.multiselect(
        "หน่วยงาน",
        options=affiliation_units,
        key="unit_filter",
        placeholder="ทุกหน่วยงาน",
    )
    st.button(
        "ล้างตัวกรองและการเลือกบนกราฟ",
        on_click=reset_dashboard,
        use_container_width=True,
    )
    st.divider()
    st.caption(f"ข้อมูล {resource_count} ไฟล์ · {len(data):,} แถว · {len(units)} หน่วยงาน")

filtered = data
period_key = st.session_state["period_filter"]
if period_key != ALL_PERIODS:
    selected_year, selected_month_number = map(int, period_key.split("-"))
    filtered = filtered.loc[
        (filtered["ปี"] == selected_year)
        & (filtered["เดือนที่"] == selected_month_number)
    ]
if st.session_state["affiliation_filter"] != ALL:
    filtered = filtered.loc[
        filtered["สังกัด"] == st.session_state["affiliation_filter"]
    ]
if st.session_state["unit_filter"]:
    filtered = filtered.loc[
        filtered["หน่วยงาน"].isin(st.session_state["unit_filter"])
    ]

if filtered.empty:
    st.warning("ไม่พบข้อมูลตามตัวกรองที่เลือก")
    st.stop()

period_description = (
    ALL_PERIODS if period_key == ALL_PERIODS else PERIOD_LABELS[period_key]
)
st.markdown(
    f"""
    <div class="waste-hero">
      <div class="waste-eyebrow">DATA DASHBOARD · กรมอุทยานแห่งชาติ สัตว์ป่า และพันธุ์พืช</div>
      <h1>สถิติปริมาณขยะมูลฝอย</h1>
      <p>สำรวจข้อมูลปริมาณขยะ การนำไปใช้ประโยชน์ และการส่งกำจัด
      · แสดง {period_description}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

total_generated = filtered[GENERATED_COLUMN].sum()
total_reused = filtered[REUSED_COLUMN].sum()
total_disposed = filtered[DISPOSED_COLUMN].sum()
reuse_rate = total_reused / total_generated * 100 if total_generated else 0.0
metric_columns = st.columns(4)
metric_columns[0].metric(
    "ขยะที่เกิดขึ้น",
    f"{total_generated:,.1f} กก.",
)
metric_columns[1].metric(
    "นำไปใช้ประโยชน์",
    f"{total_reused:,.1f} กก.",
    delta=f"{reuse_rate:.1f}% ของขยะที่เกิดขึ้น",
)
metric_columns[2].metric(
    "ส่งกำจัด",
    f"{total_disposed:,.1f} กก.",
)
metric_columns[3].metric(
    "หน่วยงานในมุมมอง",
    f"{filtered['หน่วยงาน'].nunique():,}",
)

trend_data = data
if st.session_state["affiliation_filter"] != ALL:
    trend_data = trend_data.loc[
        trend_data["สังกัด"] == st.session_state["affiliation_filter"]
    ]
if st.session_state["unit_filter"]:
    trend_data = trend_data.loc[
        trend_data["หน่วยงาน"].isin(st.session_state["unit_filter"])
    ]

period_summary = (
    trend_data.groupby(["ปี", "เดือนที่", "เดือน"], as_index=False)
    .agg(
        **{
            GENERATED_COLUMN: (GENERATED_COLUMN, "sum"),
            REUSED_COLUMN: (REUSED_COLUMN, "sum"),
            DISPOSED_COLUMN: (DISPOSED_COLUMN, "sum"),
        }
    )
    .sort_values(["ปี", "เดือนที่"])
)
period_summary["period_id"] = period_summary.apply(
    lambda row: f"{int(row['ปี'])}-{int(row['เดือนที่']):02d}", axis=1
)
period_summary["period_label"] = period_summary.apply(
    lambda row: f"{row['เดือน']} {int(row['ปี'])}", axis=1
)
month_selection = alt.selection_point(
    name="month_pick",
    fields=["period_id"],
    empty=True,
)
monthly_long = period_summary.melt(
    id_vars=["ปี", "เดือนที่", "เดือน", "period_id", "period_label"],
    value_vars=[GENERATED_COLUMN, REUSED_COLUMN, DISPOSED_COLUMN],
    var_name="waste_type",
    value_name="amount_kg",
)
type_labels = {
    GENERATED_COLUMN: "ขยะที่เกิดขึ้น",
    REUSED_COLUMN: "นำไปใช้ประโยชน์",
    DISPOSED_COLUMN: "ส่งกำจัด",
}
monthly_long["waste_type"] = monthly_long["waste_type"].map(type_labels)
trend_chart = (
    alt.Chart(monthly_long)
    .mark_line(point=alt.OverlayMarkDef(size=78, filled=True), strokeWidth=2.8)
    .add_params(month_selection)
    .encode(
        x=alt.X(
            "period_label:N",
            sort=period_summary["period_label"].tolist(),
            title="เดือน",
            axis=alt.Axis(labelAngle=-35),
        ),
        y=alt.Y("amount_kg:Q", title="ปริมาณ (กก.)"),
        color=alt.Color("waste_type:N", title="ประเภทขยะ"),
        opacity=alt.condition(month_selection, alt.value(1), alt.value(0.72)),
        tooltip=[
            alt.Tooltip("period_label:N", title="เดือน"),
            alt.Tooltip("waste_type:N", title="ประเภท"),
            alt.Tooltip("amount_kg:Q", title="ปริมาณ", format=",.1f"),
        ],
    )
    .properties(height=340)
)

agency_base = data
if period_key != ALL_PERIODS:
    agency_base = agency_base.loc[
        (agency_base["ปี"] == selected_year)
        & (agency_base["เดือนที่"] == selected_month_number)
    ]
if st.session_state["affiliation_filter"] != ALL:
    agency_base = agency_base.loc[
        agency_base["สังกัด"] == st.session_state["affiliation_filter"]
    ]
agency_totals = (
    agency_base.groupby(["หน่วยงาน", "สังกัด"], as_index=False)[GENERATED_COLUMN]
    .sum()
    .nlargest(15, GENERATED_COLUMN)
    .sort_values(GENERATED_COLUMN)
    .rename(
        columns={
            "หน่วยงาน": "unit",
            "สังกัด": "affiliation",
            GENERATED_COLUMN: "waste_generated_kg",
        }
    )
)
unit_selection = alt.selection_point(
    name="unit_pick",
    fields=["unit"],
    empty=True,
)
agency_chart = (
    alt.Chart(agency_totals)
    .mark_bar(cornerRadiusEnd=5)
    .add_params(unit_selection)
    .encode(
        x=alt.X("waste_generated_kg:Q", title="ขยะที่เกิดขึ้น (กก.)"),
        y=alt.Y("unit:N", sort="-x", title=None),
        color=alt.Color("affiliation:N", title="สังกัด"),
        opacity=alt.condition(unit_selection, alt.value(1), alt.value(0.72)),
        tooltip=[
            alt.Tooltip("unit:N", title="หน่วยงาน"),
            alt.Tooltip("affiliation:N", title="สังกัด"),
            alt.Tooltip("waste_generated_kg:Q", title="ขยะที่เกิดขึ้น (กก.)", format=",.1f"),
        ],
    )
    .properties(height=max(330, 29 * len(agency_totals)))
)

treatment_totals = pd.DataFrame(
    {
        "category": ["นำไปใช้ประโยชน์", "ส่งกำจัด"],
        "amount_kg": [total_reused, total_disposed],
    }
)
treatment_chart = (
    alt.Chart(treatment_totals)
    .mark_arc(innerRadius=45, outerRadius=75, cornerRadius=4)
    .encode(
        theta=alt.Theta("amount_kg:Q"),
        color=alt.Color("category:N", title="วิธีจัดการ"),
        tooltip=[
            alt.Tooltip("category:N", title="วิธีจัดการ"),
            alt.Tooltip("amount_kg:Q", title="ปริมาณ", format=",.1f"),
        ],
    )
    .properties(height=320)
)

st.markdown(
    '<p class="waste-note">คลิกจุดบนกราฟแนวโน้มเพื่อเลือกเดือน หรือคลิกแท่งหน่วยงานเพื่อดูรายละเอียดเฉพาะหน่วยงาน กราฟจะปรับข้อมูลและเคลื่อนไหวเมื่อเปลี่ยนมุมมอง</p>',
    unsafe_allow_html=True,
)

filter_signature = "\0".join(
    [
        st.session_state["affiliation_filter"],
        *st.session_state["unit_filter"],
    ]
)
filter_token = hashlib.blake2s(
    filter_signature.encode("utf-8"), digest_size=4
).hexdigest()
view_signature = (
    f"{period_key.replace('-', '')}-{filter_token}-{st.session_state['chart_epoch']}"
)
with st.container(key=f"animated-dashboard-{view_signature}"):
    overview_tab, details_tab, table_tab = st.tabs(
        ["📊 ภาพรวม", "🔍 รายละเอียดหน่วยงาน", "📋 ตารางข้อมูล"]
    )

    with overview_tab:
        trend_col, treatment_col = st.columns([1.55, 1])
        with trend_col:
            with st.container(border=True):
                st.markdown("#### แนวโน้มปริมาณขยะรายเดือน")
                st.caption("เปรียบเทียบขยะที่เกิดขึ้น นำไปใช้ประโยชน์ และส่งกำจัด")
                st.altair_chart(
                    trend_chart,
                    width="stretch",
                    key=month_chart_key,
                    on_select=lambda: selected_month_from_chart(month_chart_key),
                    selection_mode="month_pick",
                )
        with treatment_col:
            with st.container(border=True):
                st.markdown("#### การจัดการขยะ")
                st.caption("ปริมาณที่นำไปใช้ประโยชน์ เทียบกับปริมาณที่ส่งกำจัด")
                st.altair_chart(treatment_chart, width="stretch")
        with st.container(border=True):
            st.markdown("#### หน่วยงานที่มีขยะเกิดขึ้นสูงสุด")
            st.caption("แสดง 15 อันดับ · คลิกแท่งเพื่อกรองข้อมูลหน่วยงาน")
            st.altair_chart(
                agency_chart,
                width="stretch",
                key=unit_chart_key,
                on_select=lambda: selected_unit_from_chart(unit_chart_key),
                selection_mode="unit_pick",
            )

    with details_tab:
        if st.session_state["unit_filter"]:
            detail_units = st.session_state["unit_filter"]
        else:
            detail_units = filtered["หน่วยงาน"].dropna().unique().tolist()
        detail_data = filtered.loc[filtered["หน่วยงาน"].isin(detail_units)]
        detail_chart_data = (
            detail_data.groupby(["หน่วยงาน", "สังกัด"], as_index=False)
            .agg(
                **{
                    GENERATED_COLUMN: (GENERATED_COLUMN, "sum"),
                    REUSED_COLUMN: (REUSED_COLUMN, "sum"),
                    DISPOSED_COLUMN: (DISPOSED_COLUMN, "sum"),
                }
            )
            .melt(
                id_vars=["หน่วยงาน", "สังกัด"],
                value_vars=[GENERATED_COLUMN, REUSED_COLUMN, DISPOSED_COLUMN],
                var_name="ประเภท",
                value_name="ปริมาณ (กก.)",
            )
        )
        detail_chart_data["ประเภท"] = detail_chart_data["ประเภท"].map(type_labels)
        detail_chart_data = detail_chart_data.rename(
            columns={
                "หน่วยงาน": "unit",
                "สังกัด": "affiliation",
                "ประเภท": "waste_type",
                "ปริมาณ (กก.)": "amount_kg",
            }
        )
        st.markdown("#### เปรียบเทียบปริมาณตามหน่วยงาน")
        st.caption(
            f"แสดง {detail_data['หน่วยงาน'].nunique()} หน่วยงานในมุมมองปัจจุบัน"
        )
        unit_detail_chart = (
            alt.Chart(detail_chart_data)
            .mark_bar()
            .encode(
                x=alt.X("unit:N", title="หน่วยงาน", axis=alt.Axis(labelAngle=-40)),
                y=alt.Y("amount_kg:Q", title="ปริมาณ (กก.)"),
                color=alt.Color("waste_type:N", title="ประเภทขยะ"),
                xOffset="waste_type:N",
                tooltip=[
                    alt.Tooltip("unit:N", title="หน่วยงาน"),
                    alt.Tooltip("affiliation:N", title="สังกัด"),
                    alt.Tooltip("waste_type:N", title="ประเภท"),
                    alt.Tooltip("amount_kg:Q", title="ปริมาณ", format=",.1f"),
                ],
            )
            .properties(height=430)
        )
        st.altair_chart(unit_detail_chart, width="stretch")
        st.markdown("#### สัดส่วนการใช้ประโยชน์รายหน่วยงาน")
        unit_rates = (
            detail_data.groupby(["หน่วยงาน", "สังกัด"], as_index=False)
            .agg(
                **{
                    GENERATED_COLUMN: (GENERATED_COLUMN, "sum"),
                    REUSED_COLUMN: (REUSED_COLUMN, "sum"),
                }
            )
        )
        unit_rates["reuse_rate"] = (
            unit_rates[REUSED_COLUMN]
            .div(unit_rates[GENERATED_COLUMN].where(unit_rates[GENERATED_COLUMN] != 0))
            .fillna(0)
            * 100
        )
        unit_rates = unit_rates.rename(
            columns={
                "หน่วยงาน": "unit",
                "สังกัด": "affiliation",
                GENERATED_COLUMN: "waste_generated_kg",
                REUSED_COLUMN: "waste_reused_kg",
            }
        )
        rate_chart = (
            alt.Chart(unit_rates)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                x=alt.X("reuse_rate:Q", title="นำไปใช้ประโยชน์ (%)"),
                y=alt.Y("unit:N", sort="-x", title=None),
                color=alt.Color("affiliation:N", title="สังกัด"),
                tooltip=[
                    alt.Tooltip("unit:N", title="หน่วยงาน"),
                    alt.Tooltip("reuse_rate:Q", title="สัดส่วน (%)", format=".1f"),
                    alt.Tooltip("waste_generated_kg:Q", title="ขยะที่เกิดขึ้น (กก.)", format=",.1f"),
                    alt.Tooltip("waste_reused_kg:Q", title="นำไปใช้ประโยชน์ (กก.)", format=",.1f"),
                ],
            )
            .properties(height=max(300, 27 * len(unit_rates)))
        )
        st.altair_chart(rate_chart, width="stretch")

    with table_tab:
        st.markdown("#### รายการข้อมูลขยะ")
        st.caption(f"แสดง {len(filtered):,} แถวตามตัวกรองปัจจุบัน")
        display_columns = [
            "ปี",
            "สังกัด",
            "หน่วยงาน",
            "เดือน",
            "คนเฉลี่ย",
            "วันทำงาน",
            "โฟมบรรจุอาหาร (ใบ)",
            GENERATED_COLUMN,
            REUSED_COLUMN,
            DISPOSED_COLUMN,
            "ร้อยละขยะส่งกำจัดลดลง",
        ]
        table_data = filtered.sort_values(["ปี", "เดือนที่", "หน่วยงาน"])[
            [column for column in display_columns if column in filtered]
        ]
        st.dataframe(table_data, width="stretch", hide_index=True)
        st.download_button(
            "ดาวน์โหลดข้อมูลที่กรองเป็น CSV",
            data=table_data.to_csv(index=False).encode("utf-8-sig"),
            file_name="waste_management_filtered.csv",
            mime="text/csv",
        )

st.divider()
st.caption(
    f"แหล่งข้อมูล: กรมอุทยานแห่งชาติ สัตว์ป่า และพันธุ์พืช · "
    f"[data.go.th]({DATASET_URL}) · โหลดข้อมูลใหม่อัตโนมัติทุก 6 ชั่วโมง"
)
