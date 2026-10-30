"""
แดชบอร์ดไฟฟ้าไทยและอาเซียน (World Energy Consumption)
ข้อมูล: data/energy_clean.csv (ผ่านการทำความสะอาด 5 ขั้น)

รันบนเครื่อง:  streamlit run app.py
"""
import hmac
import io
import os
import time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ไฟฟ้าไทยและอาเซียน", page_icon="⚡", layout="wide")

# ---------------------------------------------------------------------------
# 1) ค่าคงที่: ชื่อภาษาไทย และสีเชื้อเพลิง (ชุดเดียวทั้งแอป สีสื่อความหมาย)
# ---------------------------------------------------------------------------
FUELS = {  # คีย์: (ชื่อไทย, สี)
    "coal": ("ถ่านหิน", "#4A4039"),
    "oil": ("น้ำมัน", "#8C5A3C"),
    "gas": ("ก๊าซธรรมชาติ", "#E0913A"),
    "nuclear": ("นิวเคลียร์", "#7B61A8"),
    "hydro": ("พลังน้ำ", "#2E78AD"),
    "wind": ("ลม", "#5FB3A1"),
    "solar": ("แสงอาทิตย์", "#E8B923"),
    "biofuel": ("ชีวมวล", "#7A9A3A"),
    "other_renewable_exc_biofuel": ("หมุนเวียนอื่น", "#9AA5A8"),
}
FUEL_TWH = {f: f"{f}_electricity" for f in FUELS}
FUEL_SHARE = {f: f"{f}_share_elec" for f in FUELS}
FUEL_SHARE["other_renewable_exc_biofuel"] = "other_renewables_share_elec_exc_biofuel"
FUEL_COLOR = {th: c for th, c in FUELS.values()}
FUEL_ORDER = [v[0] for v in FUELS.values()]

METRICS = {  # คอลัมน์: (ชื่อไทย, หน่วย, ทศนิยม)
    "per_capita_electricity": ("ไฟฟ้าต่อคน", "kWh/คน", 0),
    "renewables_share_elec": ("สัดส่วนพลังงานหมุนเวียน", "%", 1),
    "fossil_share_elec": ("สัดส่วนฟอสซิล", "%", 1),
    "gas_share_elec": ("สัดส่วนก๊าซธรรมชาติ", "%", 1),
    "coal_share_elec": ("สัดส่วนถ่านหิน", "%", 1),
    "solar_share_elec": ("สัดส่วนแสงอาทิตย์", "%", 1),
    "carbon_intensity_elec": ("ความเข้มคาร์บอน", "gCO₂/kWh", 0),
    "electricity_generation": ("ไฟฟ้าที่ผลิตได้", "TWh", 1),
    "electricity_demand": ("ความต้องการไฟฟ้า", "TWh", 1),
}
REGION_TH = {"Asia": "เอเชีย", "Europe": "ยุโรป", "Africa": "แอฟริกา", "North America": "อเมริกาเหนือ",
             "South America": "อเมริกาใต้", "Oceania": "โอเชียเนีย"}
SOURCE_NOTE = "ที่มา: Our World in Data (Energy) · ปี 2000–2022 · ปี 2022 เป็นข้อมูลเบื้องต้น · ทำความสะอาดแล้ว 5 ขั้น"

FONT = "IBM Plex Sans Thai, sans-serif"
NAVY, INK, MUTED, LINE, PAPER = "#13212E", "#1C2733", "#5B6773", "#E1E7EC", "#F3F6F8"
BLUE, GREY_BAR = "#1F5F8B", "#C3CDD6"
GOOD, BAD = "#1E7D4F", "#B3412E"
PLOT_CFG = {"displaylogo": False, "displayModeBar": "hover", "toImageButtonOptions": {"format": "png", "scale": 2}}

# ---------------------------------------------------------------------------
# 2) ธีมหน้าเว็บ (CSS)
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select, label {{ font-family: {FONT} !important; }}
.stApp {{ background: {PAPER}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}

/* แถบด้านข้าง */
[data-testid="stSidebar"] {{ background: {NAVY}; }}
[data-testid="stSidebar"] * {{ color: #D5DEE6; }}
[data-testid="stSidebarNav"] a {{ border-radius: 8px; padding: 0.35rem 0.6rem; }}
[data-testid="stSidebarNav"] a:hover {{ background: rgba(255,255,255,0.06); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: rgba(255,255,255,0.12); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: #FFFFFF; font-weight: 600; }}
[data-testid="stSidebar"] button {{ background: transparent; border: 1px solid rgba(255,255,255,0.25); }}

/* หัวหน้า (hero) */
.hero {{ background: {NAVY}; border-radius: 14px; padding: 1.7rem 2rem 0 2rem; color: #fff; overflow: hidden;
         margin-bottom: 1.2rem; }}
.hero h1 {{ color: #fff; font-size: 2.15rem; font-weight: 700; margin: 0 0 0.35rem 0; line-height: 1.25; }}
.hero p {{ color: #B9C6D2; margin: 0 0 1.2rem 0; font-size: 1.02rem; max-width: 62ch; }}
.hero .stripe-label {{ display: flex; justify-content: space-between; color: #8FA1B1; font-size: 0.82rem;
                       margin-bottom: 0.35rem; }}
.stripe {{ display: flex; height: 14px; margin: 0 -2rem; }}
.stripe span {{ display: block; height: 100%; }}

/* ตัวเลขสรุป */
.kpi {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 1rem 1.15rem 0.95rem; height: 100%; }}
.kpi .label {{ color: {MUTED}; font-size: 0.92rem; margin-bottom: 0.2rem; }}
.kpi .value {{ color: {INK}; font-size: 1.95rem; font-weight: 700; line-height: 1.2; }}
.kpi .value small {{ font-size: 1rem; font-weight: 500; color: {MUTED}; margin-left: 0.2rem; }}
.kpi .delta {{ font-size: 0.88rem; margin-top: 0.35rem; color: {MUTED}; }}
.kpi .delta.good {{ color: {GOOD}; }} .kpi .delta.bad {{ color: {BAD}; }}
.kpi.thai {{ border-left: 5px solid {BLUE}; }}

/* แผงกราฟ */
[class*="st-key-panel"] {{ background: #fff; border-radius: 12px; border-color: {LINE} !important; }}
.panel-title {{ font-size: 1.12rem; font-weight: 600; color: {INK}; margin: 0.1rem 0 0.1rem 0; line-height: 1.4; }}
.panel-sub {{ color: {MUTED}; font-size: 0.88rem; margin-bottom: 0.2rem; }}
.section {{ font-size: 1.35rem; font-weight: 700; color: {INK}; margin: 1.6rem 0 0.6rem 0; }}
.wsn {{ border-left: 3px solid {BLUE}; background: rgba(31,95,139,0.05); padding: 0.6rem 0.9rem;
        border-radius: 0 8px 8px 0; margin: 0.1rem 0 0.3rem 0; line-height: 1.65; font-size: 0.93rem; color: {INK}; }}
.wsn b {{ color: {BLUE}; font-weight: 600; }}
.crumb {{ color: {MUTED}; font-size: 0.9rem; }}
.source {{ color: {MUTED}; font-size: 0.8rem; margin-top: 1.2rem; }}
.legend-row {{ display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; font-size: 0.85rem; color: {MUTED}; margin: 0.2rem 0 0.4rem; }}
.legend-row i {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 0.35rem; }}
@media (max-width: 640px) {{ .hero h1 {{ font-size: 1.6rem; }} .kpi .value {{ font-size: 1.55rem; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 3) โหลดข้อมูล (แคช = โหลดครั้งเดียว)
# ---------------------------------------------------------------------------
def find_file(name):
    for folder in ["data", os.path.join("..", "final"), "final"]:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder, name)
        if os.path.exists(path):
            return path
    return None


@st.cache_data(show_spinner=False)
def load_data():
    t0 = time.perf_counter()
    path = find_file("energy_clean.csv")
    if path is None:
        raise FileNotFoundError("energy_clean.csv")
    df = pd.read_csv(path)
    for c in ["country", "iso_code", "region"]:
        df[c] = df[c].astype("category")
    df["region_th"] = df["region"].map(REGION_TH).astype("category")
    load_ms = (time.perf_counter() - t0) * 1000

    # คำนวณภาพรวมโลกไว้ล่วงหน้าครั้งเดียว (ปีที่ข้อมูลครบเท่านั้น)
    t1 = time.perf_counter()
    twh = ["electricity_generation"] + list(FUEL_TWH.values()) + ["renewables_electricity", "fossil_electricity"]
    world = df[df["year_complete"]].groupby("year")[twh].sum()
    world["renewables_share"] = world["renewables_electricity"] / world["electricity_generation"] * 100
    world["fossil_share"] = world["fossil_electricity"] / world["electricity_generation"] * 100
    for f in FUELS:
        world[FUEL_SHARE[f]] = world[FUEL_TWH[f]] / world["electricity_generation"] * 100
    agg_ms = (time.perf_counter() - t1) * 1000
    return df, world, {"rows": len(df), "load_ms": load_ms, "agg_ms": agg_ms}


@st.cache_data(show_spinner=False)
def load_side_table(name):
    path = find_file(name)
    return pd.read_csv(path) if path else None


# ---------------------------------------------------------------------------
# 4) ตัวช่วยแสดงผล
# ---------------------------------------------------------------------------
def fmt(v, dec=1, unit=""):
    if v is None or pd.isna(v):
        return "ไม่มีข้อมูล"
    return f"{v:,.{dec}f} {unit}".strip()


def kpi(col, label, value, unit="", delta="", tone="", thai=False, help_text=""):
    """การ์ดตัวเลขสรุป tone = good / bad / '' (กลาง)"""
    title = f' title="{help_text}"' if help_text else ""
    col.markdown(f'<div class="kpi{" thai" if thai else ""}"{title}><div class="label">{label}</div>'
                 f'<div class="value">{value}<small>{unit}</small></div>'
                 f'<div class="delta {tone}">{delta}</div></div>', unsafe_allow_html=True)


def tone_of(change, higher_is_better=True):
    if change is None or pd.isna(change) or abs(change) < 1e-9:
        return ""
    return "good" if (change > 0) == higher_is_better else "bad"


_panel_no = [0]


def panel():
    """แผงสีขาวมีขอบ ใช้ห่อกราฟแต่ละชิ้น"""
    _panel_no[0] += 1
    return st.container(border=True, key=f"panel_{_panel_no[0]}")


def panel_title(title, sub=""):
    st.markdown(f'<div class="panel-title">{title}</div>' + (f'<div class="panel-sub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def section(text):
    st.markdown(f'<div class="section">{text}</div>', unsafe_allow_html=True)


def breadcrumb(*parts):
    st.markdown(f'<div class="crumb">หน้าหลัก › {" › ".join(parts)}</div>', unsafe_allow_html=True)


def wsn(what, so_what, now_what):
    """คำอธิบายใต้กราฟ: เห็นอะไร → หมายความว่า → ควรทำอะไรต่อ (เกณฑ์ 3.5.3.2.1)"""
    st.markdown(f'<div class="wsn"><b>เห็นอะไร:</b> {what}<br><b>หมายความว่า:</b> {so_what}<br>'
                f'<b>ควรทำอะไรต่อ:</b> {now_what}</div>', unsafe_allow_html=True)


def fuel_legend():
    items = "".join(f'<span><i style="background:{c}"></i>{th}</span>' for th, c in FUELS.values())
    st.markdown(f'<div class="legend-row">{items}</div>', unsafe_allow_html=True)


def source(extra=""):
    st.markdown(f'<div class="source">{SOURCE_NOTE}{" · " + extra if extra else ""}</div>', unsafe_allow_html=True)


def empty_state(message, reset_keys=None):
    """เมื่อไม่มีข้อมูล: บอกเหตุและทางออก (เกณฑ์ 3.5.4.2.3)"""
    st.info(f"🔎 {message}")
    if reset_keys:
        def _reset():
            for k in reset_keys:
                st.session_state.pop(k, None)
        st.button("ล้างตัวกรอง", key=f"reset_{reset_keys[0]}", on_click=_reset)


def show(fig):
    st.plotly_chart(fig, width="stretch", config=PLOT_CFG)


def style_fig(fig, height=340, ytitle=None, xtitle=None, legend=True):
    fig.update_layout(height=height, font=dict(family=FONT, size=13, color=INK),
                      margin=dict(l=4, r=8, t=8 if not legend else 36, b=4),
                      plot_bgcolor="white", paper_bgcolor="white", showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None, font=dict(size=12)),
                      hoverlabel=dict(font_family=FONT, bgcolor="white"))
    fig.update_xaxes(showgrid=False, title=xtitle, linecolor=LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#EDF1F4", title=ytitle, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def to_excel_bytes(frame):
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf) as xw:
            frame.to_excel(xw, index=False, sheet_name="data")
        return buf.getvalue()
    except ModuleNotFoundError:
        return None


# ---------------------------------------------------------------------------
# 5) กราฟ (ใช้ซ้ำได้ทุกหน้า)
# ---------------------------------------------------------------------------
def fig_mix_strip(rows, height=210):
    """แถบ 100% สัดส่วนเชื้อเพลิง rows = [(ชื่อแถว, dict ของสัดส่วน)]"""
    recs = [{"กลุ่ม": name, "เชื้อเพลิง": FUELS[f][0], "สัดส่วน": vals.get(FUEL_SHARE[f], np.nan)}
            for name, vals in rows for f in FUELS]
    long = pd.DataFrame(recs).dropna()
    fig = px.bar(long, y="กลุ่ม", x="สัดส่วน", color="เชื้อเพลิง", orientation="h",
                 color_discrete_map=FUEL_COLOR, category_orders={"เชื้อเพลิง": FUEL_ORDER})
    fig.update_traces(hovertemplate="%{y} · %{fullData.name}: %{x:.1f}%<extra></extra>",
                      texttemplate="%{x:.0f}%", textposition="inside", insidetextanchor="middle",
                      textfont=dict(color="white", size=12))
    fig.for_each_trace(lambda t: t.update(texttemplate=[f"{v:.0f}%" if v >= 6 else "" for v in t.x]))
    fig = style_fig(fig, height, legend=False, xtitle=None)
    fig.update_xaxes(range=[0, 100], ticksuffix="%", showticklabels=False)
    fig.update_yaxes(title=None, autorange="reversed", tickfont=dict(size=14, color=INK))
    fig.update_layout(bargap=0.3)
    return fig


def solid_area(fig):
    """ให้พื้นที่กราฟสีทึบตรงกับสีเชื้อเพลิง (ค่าเริ่มต้นของ plotly จางเกินไป)"""
    fig.for_each_trace(lambda t: t.update(fillcolor=FUEL_COLOR.get(t.name, None), line=dict(width=0.6, color="white")))
    return fig


def fig_world_trend(world, year):
    trend = world.loc[:year, list(FUEL_TWH.values())].rename(columns={v: FUELS[k][0] for k, v in FUEL_TWH.items()})
    long = trend.reset_index().melt("year", var_name="เชื้อเพลิง", value_name="TWh")
    fig = px.area(long, x="year", y="TWh", color="เชื้อเพลิง", color_discrete_map=FUEL_COLOR,
                  category_orders={"เชื้อเพลิง": FUEL_ORDER})
    fig.update_traces(hovertemplate="%{x}: %{y:,.0f} TWh<extra>%{fullData.name}</extra>")
    fig = style_fig(solid_area(fig), 330, "TWh", None, legend=False)
    fig.update_yaxes(rangemode="tozero")
    return fig


def fig_rank(frame, metric, dec, unit, highlight="Thailand", height=330, horizontal=True):
    f = frame.sort_values(metric, ascending=horizontal)
    colors = [BLUE if c == highlight else GREY_BAR for c in f["country"]]
    text = f[metric].map(lambda v: f"{v:,.{dec}f}")
    if horizontal:
        fig = go.Figure(go.Bar(x=f[metric], y=f["country"].astype(str), orientation="h", marker_color=colors,
                               text=text, textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x:,." + str(dec) + "f} " + unit + "<extra></extra>"))
        fig = style_fig(fig, height, None, None, legend=False)
        fig.update_xaxes(showticklabels=False, range=[0, f[metric].max() * 1.15])
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK))
    else:
        fig = go.Figure(go.Bar(x=f["country"].astype(str), y=f[metric], marker_color=colors, text=text,
                               textposition="outside", cliponaxis=False,
                               hovertemplate="%{x}: %{y:,." + str(dec) + "f} " + unit + "<extra></extra>"))
        fig = style_fig(fig, height, f"{unit}", None, legend=False)
        fig.update_xaxes(categoryorder="array", categoryarray=f["country"].astype(str).tolist())
    fig.update_layout(bargap=0.35)
    return fig


def fig_gen_demand(d):
    fig = go.Figure()
    fig.add_scatter(x=d["year"], y=d["electricity_demand"], name="ความต้องการ", mode="lines",
                    line=dict(color=INK, width=2.5), fill=None)
    fig.add_scatter(x=d["year"], y=d["electricity_generation"], name="ผลิตเอง", mode="lines",
                    line=dict(color=BLUE, width=2.5), fill="tonexty", fillcolor="rgba(224,145,58,0.18)")
    fig.update_traces(hovertemplate="%{x}: %{y:,.1f} TWh")
    fig = style_fig(fig, 300, "TWh")
    fig.update_yaxes(rangemode="tozero")
    return fig


def fig_mix_time(d):
    long = d.melt("year", value_vars=list(FUEL_SHARE.values()), var_name="col", value_name="สัดส่วน")
    long["เชื้อเพลิง"] = long["col"].map({v: FUELS[k][0] for k, v in FUEL_SHARE.items()})
    fig = px.area(long.dropna(), x="year", y="สัดส่วน", color="เชื้อเพลิง", color_discrete_map=FUEL_COLOR,
                  category_orders={"เชื้อเพลิง": FUEL_ORDER})
    fig.update_traces(hovertemplate="%{x}: %{y:.1f}%<extra>%{fullData.name}</extra>")
    fig = style_fig(solid_area(fig), 300, "%", legend=False)
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return fig


def fig_scatter(df, year, highlight):
    allc = df[(df["year"] == year) & ~df["low_precision"]].dropna(
        subset=["per_capita_electricity", "renewables_share_elec"])
    allc = allc[allc["per_capita_electricity"] > 0]
    fig = px.scatter(allc, x="per_capita_electricity", y="renewables_share_elec", color="region_th",
                     hover_name="country", log_x=True, color_discrete_sequence=["#9CB9D1", "#D9A0A0", "#D8C27A", "#8FC0A9", "#B3A3CF", "#C9A88B"],
                     labels={"per_capita_electricity": "ไฟฟ้าต่อคน (kWh, สเกล log)",
                             "renewables_share_elec": "สัดส่วนหมุนเวียน (%)", "region_th": "ทวีป"})
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=0)))
    hl = allc[allc["country"].isin(highlight)]
    fig.add_scatter(x=hl["per_capita_electricity"], y=hl["renewables_share_elec"], mode="markers+text",
                    text=hl["country"].astype(str), textposition="top center", name="ไทย/ที่เลือก",
                    textfont=dict(size=11, color=INK),
                    marker=dict(size=11, color=BLUE, line=dict(color="white", width=1.5)))
    r = allc[["per_capita_electricity", "renewables_share_elec"]].corr(method="spearman").iloc[0, 1]
    return style_fig(fig, 340, "สัดส่วนหมุนเวียน (%)", "ไฟฟ้าต่อคน (kWh, สเกล log)"), r, len(allc)


def fig_region_median(df, year):
    y = df[(df["year"] == year) & ~df["low_precision"]]
    med = y.groupby("region_th", observed=True)["per_capita_electricity"].median().sort_values()
    fig = go.Figure(go.Bar(x=med.values, y=med.index.astype(str), orientation="h", marker_color=GREY_BAR,
                           text=[f"{v:,.0f}" for v in med.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,.0f} kWh/คน<extra></extra>"))
    fig = style_fig(fig, 300, None, None, legend=False)
    fig.update_xaxes(showticklabels=False, range=[0, med.max() * 1.2])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK))
    return fig, med


def fig_carbon(d, med, name):
    fig = go.Figure()
    fig.add_scatter(x=med.index, y=med.values, name="มัธยฐานโลก", mode="lines", line=dict(color="#9AA5A8", width=2, dash="dash"))
    fig.add_scatter(x=d["year"], y=d["carbon_intensity_elec"], name=name, mode="lines+markers",
                    line=dict(color=BLUE, width=2.5), marker=dict(size=5))
    fig.update_traces(hovertemplate="%{x}: %{y:,.0f} gCO₂/kWh")
    fig = style_fig(fig, 300, "gCO₂/kWh")
    fig.update_yaxes(rangemode="tozero")
    return fig


# ---------------------------------------------------------------------------
# 6) เข้าสู่ระบบ (บัญชีทดสอบสำหรับกรรมการ ตั้งค่าได้ใน .streamlit/secrets.toml)
# ---------------------------------------------------------------------------
def get_users():
    try:
        return dict(st.secrets["users"])
    except Exception:
        return {"judge": "energy2025"}


def login_page():
    st.markdown('<div class="hero"><h1>⚡ ไฟฟ้าไทยและอาเซียน</h1>'
                '<p>ไฟฟ้ามาจากเชื้อเพลิงอะไร ใครใช้ไฟมากแค่ไหน และพลังงานสะอาดเติบโตเร็วแค่ไหน '
                'ข้อมูล 211 ประเทศ ปี 2000–2022</p>'
                '<div class="stripe" style="margin-top:0.4rem">'
                + "".join(f'<span style="width:{100/len(FUELS):.2f}%;background:{c}"></span>' for _, c in FUELS.values())
                + '</div></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with panel():
            st.markdown('<div class="panel-title">เข้าสู่ระบบ</div>', unsafe_allow_html=True)
            with st.form("login", border=False):
                user = st.text_input("ชื่อผู้ใช้")
                pw = st.text_input("รหัสผ่าน", type="password")
                ok = st.form_submit_button("เข้าสู่ระบบ", type="primary", width="stretch")
            if ok:
                users = get_users()
                if user in users and hmac.compare_digest(pw, str(users[user])):
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง ตรวจตัวพิมพ์เล็ก-ใหญ่และภาษาของแป้นพิมพ์ แล้วลองอีกครั้ง")
        source()


# ---------------------------------------------------------------------------
# 7) หน้าหลัก: รวมกราฟสำคัญทั้งหมดไว้หน้าเดียว
# ---------------------------------------------------------------------------
def page_home():
    df, world, _ = DATA
    years = sorted(world.index)

    # --- ตัวควบคุม (ปี + ประเทศที่โฟกัส) ---
    c1, c2 = st.columns([2.2, 1])
    year = c1.select_slider("ปีที่ต้องการดู (เฉพาะปีที่ข้อมูลครบทุกประเทศ)", options=years, value=years[-1], key="hm_year")
    countries = sorted(df["country"].astype(str).unique())
    focus = c2.selectbox("ประเทศที่โฟกัส", countries, index=countries.index("Thailand"), key="hm_focus")
    base = years[0]
    w, w0 = world.loc[year], world.loc[base]

    # --- hero: แถบสีบนสุด = สัดส่วนเชื้อเพลิงผลิตไฟฟ้าของโลกในปีที่เลือก (ข้อมูลจริง) ---
    stripe = "".join(f'<span style="width:{w[FUEL_SHARE[f]]:.2f}%;background:{c}" title="{th} {w[FUEL_SHARE[f]]:.1f}%"></span>'
                     for f, (th, c) in FUELS.items() if w[FUEL_SHARE[f]] > 0)
    st.markdown(f'<div class="hero"><h1>ไฟฟ้าของโลกในปี {year} และ{"ไทย" if focus == "Thailand" else " " + focus}</h1>'
                f'<p>โลกผลิตไฟฟ้า {w["electricity_generation"]:,.0f} TWh มาจากฟอสซิล {w["fossil_share"]:.0f}% '
                f'และพลังงานหมุนเวียน {w["renewables_share"]:.0f}% แถบสีด้านล่างคือสัดส่วนเชื้อเพลิงของโลกปีนี้</p>'
                f'<div class="stripe-label"><span>ฟอสซิล</span><span>คาร์บอนต่ำ</span></div>'
                f'<div class="stripe">{stripe}</div></div>', unsafe_allow_html=True)

    y = df[df["year"] == year]
    fc = y[y["country"] == focus]
    if fc.empty or pd.isna(fc.iloc[0]["electricity_generation"]):
        empty_state(f"{focus} ไม่มีข้อมูลไฟฟ้าปี {year} ลองเลือกปีอื่น หรือกลับไปโฟกัสที่ Thailand",
                    ["hm_year", "hm_focus"])
        return
    fc = fc.iloc[0]
    fname = "ไทย" if focus == "Thailand" else focus
    hist = df[(df["country"] == focus)].sort_values("year")
    fc0 = hist[hist["year"] == base].iloc[0] if (hist["year"] == base).any() else fc
    asean = y[y["is_asean"]].dropna(subset=["renewables_share_elec"])

    # --- ตัวเลขสรุป ---
    k = st.columns(4)
    g_chg = (w["electricity_generation"] / w0["electricity_generation"] - 1) * 100
    kpi(k[0], "ไฟฟ้าที่โลกผลิตได้", f"{w['electricity_generation']:,.0f}", "TWh",
        f"▲ {g_chg:.1f}% จากปี {base}", "")
    r_chg = w["renewables_share"] - w0["renewables_share"]
    kpi(k[1], "สัดส่วนหมุนเวียนของโลก", f"{w['renewables_share']:.1f}", "%",
        f"{'▲' if r_chg >= 0 else '▼'} {abs(r_chg):.1f} จุด จากปี {base}", tone_of(r_chg))
    pc_chg = fc["per_capita_electricity"] - fc0["per_capita_electricity"]
    kpi(k[2], f"{fname}: ไฟฟ้าต่อคน", fmt(fc["per_capita_electricity"], 0), "kWh",
        f"มัธยฐานโลก {y['per_capita_electricity'].median():,.0f} kWh", "", thai=True,
        help_text="ใช้มัธยฐานแทนค่าเฉลี่ย เพราะข้อมูลเบ้ขวามาก")
    fr_chg = fc["renewables_share_elec"] - fc0["renewables_share_elec"]
    rank_txt = ""
    if focus in asean["country"].values:
        rank = int(asean["renewables_share_elec"].rank(ascending=False)[asean["country"] == focus].iloc[0])
        rank_txt = f" · อันดับ {rank}/{len(asean)} อาเซียน"
    kpi(k[3], f"{fname}: สัดส่วนหมุนเวียน", fmt(fc["renewables_share_elec"], 1), "%",
        f"{'▲' if fr_chg >= 0 else '▼'} {abs(fr_chg):.1f} จุด จากปี {base}{rank_txt}", tone_of(fr_chg), thai=True)

    # --- 1. สัดส่วนเชื้อเพลิง ---
    section("ไฟฟ้ามาจากเชื้อเพลิงอะไร")
    asean_tot = y[y["is_asean"]][list(FUEL_TWH.values()) + ["electricity_generation"]].sum()
    asean_row = {FUEL_SHARE[f]: asean_tot[FUEL_TWH[f]] / asean_tot["electricity_generation"] * 100 for f in FUELS}
    rows = [(focus if focus != "Thailand" else "ไทย", fc.to_dict()), ("อาเซียน", asean_row), ("โลก", w.to_dict())]
    with panel():
        main_f = max(FUELS, key=lambda f: fc[FUEL_SHARE[f]] if pd.notna(fc[FUEL_SHARE[f]]) else -1)
        panel_title(f"{rows[0][0]}พึ่ง{FUELS[main_f][0]} {fc[FUEL_SHARE[main_f]]:.0f}% ของไฟฟ้าทั้งหมด",
                    f"สัดส่วนเชื้อเพลิงที่ใช้ผลิตไฟฟ้า ปี {year} เทียบอาเซียน (รวม) และโลก")
        fuel_legend()
        show(fig_mix_strip(rows))
        wsn(f"{rows[0][0]}ใช้{FUELS[main_f][0]} {fc[FUEL_SHARE[main_f]]:.1f}% ขณะที่โลกใช้ {w[FUEL_SHARE[main_f]]:.1f}%",
            "ยิ่งพึ่งเชื้อเพลิงเดียวมาก ค่าไฟยิ่งผันผวนตามราคาเชื้อเพลิงนั้น",
            "ดูกราฟถัดไปว่าสัดส่วนเปลี่ยนไปอย่างไรตั้งแต่ปี 2000")

    # --- 2. แนวโน้มของประเทศที่โฟกัส ---
    section(f"{rows[0][0]}: แนวโน้มตั้งแต่ปี 2000")
    h = hist[hist["year"] <= year]
    left, right = st.columns(2)
    with left, panel():
        imp = fc["net_elec_imports"]
        imp_share = imp / fc["electricity_demand"] * 100 if pd.notna(imp) and fc["electricity_demand"] else np.nan
        panel_title("ผลิตเองไม่พอ ต้องนำเข้าไฟฟ้า" if pd.notna(imp) and imp > 0 else "ผลิตเองเทียบกับความต้องการ",
                    "TWh ต่อปี · พื้นที่แรเงาคือส่วนต่างระหว่างความต้องการกับที่ผลิตเอง")
        show(fig_gen_demand(h))
        wsn(f"ปี {year} นำเข้าไฟฟ้าสุทธิ {fmt(imp, 1, 'TWh')} ({fmt(imp_share, 1, '%')} ของความต้องการ)",
            ("ไฟฟ้าที่นำเข้าส่วนใหญ่ของไทยมาจากเขื่อนในลาว ความมั่นคงด้านไฟฟ้าจึงผูกกับเพื่อนบ้าน" if focus == "Thailand"
             else ("ประเทศนี้ส่งออกไฟฟ้ามากกว่านำเข้า (ค่าติดลบ) ไฟฟ้าเป็นสินค้าส่งออก" if pd.notna(imp) and imp < 0
                   else "ถ้าความต้องการสูงกว่าที่ผลิตได้ ต้องพึ่งไฟฟ้าจากต่างประเทศ")),
            "วางแผนผลิตในประเทศเพิ่ม หรือทำสัญญาซื้อไฟระยะยาว" if pd.notna(imp) and imp > 0
            else "ติดตามว่ากำลังผลิตยังเพียงพอกับความต้องการที่โตขึ้นหรือไม่")
    with right, panel():
        grow = max(FUELS, key=lambda f: (fc[FUEL_SHARE[f]] - fc0[FUEL_SHARE[f]])
                   if pd.notna(fc[FUEL_SHARE[f]]) and pd.notna(fc0[FUEL_SHARE[f]]) else -999)
        panel_title(f"{FUELS[grow][0]}เพิ่มขึ้นมากที่สุด", "สัดส่วนเชื้อเพลิงตามเวลา (รวม 100%)")
        fuel_legend()
        show(fig_mix_time(h))
        wsn(f"{FUELS[grow][0]} {fc0[FUEL_SHARE[grow]]:.1f}% (ปี {base}) → {fc[FUEL_SHARE[grow]]:.1f}% (ปี {year})",
            "พื้นที่แต่ละสีบอกว่าเชื้อเพลิงไหนกำลังเข้ามาแทนที่เชื้อเพลิงไหน",
            "เร่งพลังงานที่กำลังโต เพื่อลดการพึ่งเชื้อเพลิงหลัก")

    # --- 3. เทียบกับโลกและอาเซียน ---
    section("เทียบกับอาเซียนและโลก")
    left, right = st.columns([1, 1.25])
    with left, panel():
        top = asean.sort_values("renewables_share_elec").iloc[-1]
        panel_title(f"อาเซียน: {top['country']} ใช้พลังงานหมุนเวียนมากที่สุด", f"สัดส่วนพลังงานหมุนเวียน (%) ปี {year}")
        show(fig_rank(asean, "renewables_share_elec", 1, "%", highlight=focus, height=360))
        wsn(f"{top['country']} {top['renewables_share_elec']:.1f}% · มัธยฐานอาเซียน {asean['renewables_share_elec'].median():.1f}%",
            "ประเทศที่สัดส่วนสูงส่วนใหญ่มีเขื่อนพลังน้ำขนาดใหญ่",
            "ไทยมีพื้นที่ทำเขื่อนจำกัด จึงควรเน้นแสงอาทิตย์และลม")
    with right, panel():
        sc, r, n = fig_scatter(df, year, [focus] + (["Laos", "Vietnam"] if focus == "Thailand" else []))
        strength = "แทบไม่สัมพันธ์" if abs(r) < 0.2 else ("สัมพันธ์อ่อน" if abs(r) < 0.4 else "สัมพันธ์ปานกลางขึ้นไป")
        panel_title("ใช้ไฟมากขึ้น ไม่ได้แปลว่าสะอาดขึ้น", f"{n} ประเทศ ปี {year} · แต่ละจุดคือ 1 ประเทศ")
        show(sc)
        wsn(f"ค่าสหสัมพันธ์ Spearman = {r:.2f} ({strength})",
            "การใช้พลังงานสะอาดขึ้นกับทรัพยากรธรรมชาติและนโยบาย มากกว่าระดับการใช้ไฟ",
            "สหสัมพันธ์ไม่ได้บอกเหตุและผล ต้องดูนโยบายประกอบก่อนสรุป")

    left, right = st.columns([1.25, 1])
    with left, panel():
        panel_title(f"โลกผลิตไฟฟ้าเพิ่ม {g_chg:.0f}% แต่ส่วนใหญ่ยังเป็นฟอสซิล", f"TWh ต่อปี แยกตามเชื้อเพลิง {base}–{year}")
        fuel_legend()
        show(fig_world_trend(world, year))
        wsn(f"ฟอสซิล {w0['fossil_share']:.1f}% → {w['fossil_share']:.1f}% · หมุนเวียน {w0['renewables_share']:.1f}% → {w['renewables_share']:.1f}%",
            "พลังงานหมุนเวียนโตเร็ว แต่ยังโตไม่ทันความต้องการไฟฟ้าที่เพิ่มขึ้น",
            "ติดตามว่าแสงอาทิตย์และลมจะแซงถ่านหินได้เมื่อไร")
    with right, panel():
        rm, med = fig_region_median(df, year)
        panel_title(f"{med.index[-1]}ใช้ไฟต่อคนสูงสุด", f"มัธยฐานไฟฟ้าต่อคน (kWh) แยกทวีป ปี {year}")
        show(rm)
        wsn(f"{med.index[-1]} {med.iloc[-1]:,.0f} kWh/คน มากกว่า{med.index[0]} ({med.iloc[0]:,.0f}) ราว {med.iloc[-1] / med.iloc[0]:.0f} เท่า",
            "ความต่างนี้สะท้อนระดับการพัฒนาและการเข้าถึงไฟฟ้า",
            "ใช้มัธยฐานเพราะประเทศที่ใช้ไฟสูงมากไม่กี่ประเทศดึงค่าเฉลี่ยให้เพี้ยน")

    # --- ไปหน้ารายละเอียด ---
    section("ดูรายละเอียดเพิ่ม")
    n1, n2, n3 = st.columns(3)
    with n1, panel():
        st.page_link(PAGES["country"], label="รายประเทศ", icon="📈")
        st.caption("เลือกช่วงปีเอง ดูความเข้มคาร์บอน และดาวน์โหลดข้อมูลรายประเทศ")
    with n2, panel():
        st.page_link(PAGES["compare"], label="เปรียบเทียบ", icon="📊")
        st.caption("จัดอันดับประเทศใดก็ได้ ด้วยตัวชี้วัด 9 แบบ")
    with n3, panel():
        st.page_link(PAGES["explorer"], label="ตารางข้อมูล", icon="🗂️")
        st.caption("กรอง ค้นหา เรียง และส่งออกเป็น CSV หรือ Excel")
    source(f"ภาพรวมโลกใช้เฉพาะปีที่ข้อมูลครบ ({years[0]}–{years[-1]})")


# ---------------------------------------------------------------------------
# 8) หน้ารายละเอียด
# ---------------------------------------------------------------------------
def page_country():
    df, world, _ = DATA
    breadcrumb("รายประเทศ")
    st.title("รายประเทศ")
    countries = sorted(df["country"].astype(str).unique())
    c1, c2 = st.columns([1, 1.6])
    country = c1.selectbox("เลือกประเทศ (พิมพ์เพื่อค้นหา)", countries, index=countries.index("Thailand"),
                           key="ct_country")
    yr = c2.slider("ช่วงปี", 2000, 2022, (2000, 2022), key="ct_years")
    d = df[(df["country"] == country) & df["year"].between(*yr)].sort_values("year")
    d_ok = d.dropna(subset=["electricity_generation"])
    if d_ok.empty:
        empty_state(f"{country} ไม่มีข้อมูลไฟฟ้าในช่วงปี {yr[0]}–{yr[1]} ลองขยายช่วงปีหรือเลือกประเทศอื่น", ["ct_years"])
        return
    first, last = d_ok.iloc[0], d_ok.iloc[-1]
    if not last["year_complete"]:
        st.caption(f"ℹ️ ปี {int(last['year'])} เป็นข้อมูลเบื้องต้น อาจมีการปรับแก้ภายหลัง")
    if d["low_precision"].any():
        st.warning("ประเทศนี้ผลิตไฟฟ้าน้อยมาก (< 0.1 TWh) ตัวเลขถูกปัด สัดส่วนและความเข้มคาร์บอนอาจคลาดเคลื่อน")

    k = st.columns(4)
    g = (last["electricity_generation"] / first["electricity_generation"] - 1) * 100 if first["electricity_generation"] else np.nan
    kpi(k[0], f"ไฟฟ้าที่ผลิต ({int(last['year'])})", fmt(last["electricity_generation"], 1), "TWh",
        f"{'▲' if g >= 0 else '▼'} {abs(g):.0f}% จากปี {int(first['year'])}" if pd.notna(g) else "")
    pc = last["per_capita_electricity"] - first["per_capita_electricity"]
    kpi(k[1], "ไฟฟ้าต่อคน", fmt(last["per_capita_electricity"], 0), "kWh",
        f"{'▲' if pc >= 0 else '▼'} {abs(pc):,.0f} kWh" if pd.notna(pc) else "")
    rs = last["renewables_share_elec"] - first["renewables_share_elec"]
    kpi(k[2], "สัดส่วนหมุนเวียน", fmt(last["renewables_share_elec"], 1), "%",
        f"{'▲' if rs >= 0 else '▼'} {abs(rs):.1f} จุด" if pd.notna(rs) else "", tone_of(rs))
    ci = last["carbon_intensity_elec"] - first["carbon_intensity_elec"]
    kpi(k[3], "ความเข้มคาร์บอน", fmt(last["carbon_intensity_elec"], 0), "g/kWh",
        f"{'▲' if ci >= 0 else '▼'} {abs(ci):.0f} (ยิ่งต่ำยิ่งสะอาด)" if pd.notna(ci) else "ยิ่งต่ำยิ่งสะอาด",
        tone_of(ci, higher_is_better=False))

    section("สัดส่วนเชื้อเพลิง")
    with panel():
        panel_title(f"ปี {int(first['year'])} เทียบกับ {int(last['year'])}")
        fuel_legend()
        show(fig_mix_strip([(f"ปี {int(first['year'])}", first.to_dict()), (f"ปี {int(last['year'])}", last.to_dict())], 170))
        main_f = max(FUELS, key=lambda f: last[FUEL_SHARE[f]] if pd.notna(last[FUEL_SHARE[f]]) else -1)
        wsn(f"เชื้อเพลิงหลักปี {int(last['year'])} คือ{FUELS[main_f][0]} ({last[FUEL_SHARE[main_f]]:.1f}%)",
            "การพึ่งเชื้อเพลิงเดียวสูงทำให้ค่าไฟผันผวนตามราคาเชื้อเพลิงนั้น",
            "เทียบกับเพื่อนบ้านในหน้า “เปรียบเทียบ”")

    left, right = st.columns(2)
    with left, panel():
        panel_title("ผลิตเองเทียบกับความต้องการ", "TWh ต่อปี")
        show(fig_gen_demand(d))
    with right, panel():
        panel_title("สัดส่วนเชื้อเพลิงตามเวลา", "รวม 100%")
        fuel_legend()
        show(fig_mix_time(d))

    with panel():
        med = df[df["year_complete"]].groupby("year")["carbon_intensity_elec"].median().loc[yr[0]:yr[1]]
        panel_title("ความเข้มคาร์บอน เทียบมัธยฐานโลก", "กรัม CO₂ ต่อไฟฟ้า 1 kWh · ยิ่งต่ำยิ่งสะอาด")
        show(fig_carbon(d, med, country))
        wsn(f"ปี {int(last['year'])} {country} ปล่อย {fmt(last['carbon_intensity_elec'], 0, 'gCO₂')} ต่อไฟฟ้า 1 kWh",
            "ถ้าเส้นอยู่ใต้มัธยฐานโลก แปลว่าไฟฟ้าสะอาดกว่าประเทศส่วนใหญ่",
            "ลดได้โดยเพิ่มพลังงานหมุนเวียนแทนถ่านหินและก๊าซ")

    with st.expander("ดูตารางข้อมูลของประเทศนี้ และดาวน์โหลด"):
        cols = ["year", "electricity_generation", "electricity_demand", "per_capita_electricity",
                "renewables_share_elec", "fossil_share_elec", "gas_share_elec", "carbon_intensity_elec"]
        st.dataframe(d[cols].rename(columns={c: METRICS.get(c, ("ปี",))[0] for c in cols}), hide_index=True, width="stretch")
        st.download_button("ดาวน์โหลด CSV", d.to_csv(index=False).encode("utf-8-sig"), f"{country}_{yr[0]}-{yr[1]}.csv", "text/csv")
    source()


def page_compare():
    df, _, _ = DATA
    breadcrumb("เปรียบเทียบ")
    st.title("เปรียบเทียบประเทศ")
    all_countries = sorted(df["country"].astype(str).unique())
    asean = sorted(df.loc[df["is_asean"], "country"].astype(str).unique())

    f1, f2, f3 = st.columns([1.2, 1, 0.8])
    metric = f1.selectbox("ตัวชี้วัด", list(METRICS), format_func=lambda c: f"{METRICS[c][0]} ({METRICS[c][1]})",
                          index=1, key="cp_metric")
    year = f2.select_slider("ปี", options=list(range(2000, 2023)), value=2021, key="cp_year")
    order = f3.radio("เรียง", ["มาก → น้อย", "น้อย → มาก"], horizontal=True, key="cp_order")
    p1, p2 = st.columns([3, 1])
    st.session_state.setdefault("cp_countries", asean)
    countries = p1.multiselect("ประเทศ (พิมพ์เพื่อค้นหา)", all_countries, key="cp_countries")
    with p2:
        st.write("")
        st.button("ใช้ชุดอาเซียน", width="stretch", on_click=lambda: st.session_state.update(cp_countries=asean))
    hide_small = st.checkbox("ซ่อนประเทศที่ผลิตไฟฟ้าน้อยมาก (ตัวเลขถูกปัด อาจคลาดเคลื่อน)", value=True, key="cp_small")
    name, unit, dec = METRICS[metric]

    if not countries:
        empty_state("ยังไม่ได้เลือกประเทศ เลือกอย่างน้อย 1 ประเทศ หรือกดปุ่ม “ใช้ชุดอาเซียน”")
        return
    if year == 2022:
        st.caption("ℹ️ ปี 2022 เป็นข้อมูลเบื้องต้น หลายประเทศยังไม่มีข้อมูล")
    sel = df[df["country"].isin(countries)]
    if hide_small:
        sel = sel[~sel["low_precision"]]
    y = sel[sel["year"] == year].dropna(subset=[metric])
    missing = sorted(set(countries) - set(y["country"].astype(str)))
    if y.empty:
        empty_state(f"ไม่มีข้อมูล {name} ของประเทศที่เลือกในปี {year} ลองเลือกปีอื่น (ปี 2021 ข้อมูลครบที่สุด)", ["cp_year"])
        return

    with panel():
        panel_title(f"{name} ปี {year}", f"หน่วย: {unit} · ไทยเป็นแท่งสีน้ำเงิน")
        yy = y.sort_values(metric, ascending=(order == "น้อย → มาก"))
        fig = fig_rank(yy, metric, dec, unit, horizontal=False, height=400)
        fig.update_xaxes(categoryarray=yy["country"].astype(str).tolist())
        show(fig)
        med = y[metric].median()
        hi, lo = y.loc[y[metric].idxmax()], y.loc[y[metric].idxmin()]
        th_txt = ""
        if "Thailand" in y["country"].values:
            thv = y.loc[y["country"] == "Thailand", metric].iloc[0]
            th_txt = f" · ไทย {thv:,.{dec}f} {unit} ({'สูงกว่า' if thv > med else 'ต่ำกว่า'}มัธยฐานกลุ่ม)"
        wsn(f"สูงสุด {hi['country']} {hi[metric]:,.{dec}f} · ต่ำสุด {lo['country']} {lo[metric]:,.{dec}f} · "
            f"มัธยฐานกลุ่ม {med:,.{dec}f} {unit}{th_txt}",
            "ความต่างระหว่างประเทศบอกว่าแต่ละประเทศมีทรัพยากรและนโยบายพลังงานต่างกันมาก",
            "เลือกประเทศที่ทำได้ดีกว่า แล้วไปดูหน้า “รายประเทศ” ว่าเขาเปลี่ยนอย่างไร")
        if missing:
            st.caption(f"ไม่มีข้อมูลปีนี้: {', '.join(missing)}")

    with panel():
        panel_title(f"แนวโน้ม {name}", "เส้นสีน้ำเงินหนาคือไทย · คลิกชื่อประเทศในคำอธิบายเพื่อซ่อน/แสดง")
        t = sel.dropna(subset=[metric])
        fig = px.line(t, x="year", y=metric, color="country",
                      labels={"year": "ปี", metric: f"{name} ({unit})", "country": "ประเทศ"})
        fig.update_traces(line=dict(width=1.6), opacity=0.5)
        fig.for_each_trace(lambda tr: tr.update(line=dict(width=4, color=BLUE), opacity=1) if tr.name == "Thailand" else None)
        show(style_fig(fig, 380, f"{unit}"))
    source()


def page_explorer():
    df, _, _ = DATA
    breadcrumb("ตารางข้อมูล")
    st.title("ตารางข้อมูล")
    groups = {
        "หลัก": ["electricity_generation", "electricity_demand", "per_capita_electricity", "carbon_intensity_elec"],
        "สัดส่วนเชื้อเพลิง (%)": list(FUEL_SHARE.values()) + ["fossil_share_elec", "renewables_share_elec"],
        "ปริมาณตามเชื้อเพลิง (TWh)": list(FUEL_TWH.values()),
        "บริบท": ["population", "gdp", "primary_energy_consumption"],
        "ธงคุณภาพข้อมูล": ["year_complete", "is_outlier_pc_elec", "low_precision", "gdp_available"],
    }
    with panel():
        f1, f2, f3 = st.columns(3)
        regions = f1.multiselect("ทวีป", sorted(df["region_th"].dropna().unique()), key="ex_region", placeholder="ทุกทวีป")
        search = f2.text_input("ค้นหาชื่อประเทศ (ภาษาอังกฤษ)", key="ex_search", placeholder="เช่น Thai, Viet")
        yr = f3.slider("ช่วงปี", 2000, 2022, (2015, 2022), key="ex_years")
        g1, g2, g3 = st.columns([2, 1, 1])
        picked = g1.multiselect("กลุ่มคอลัมน์", list(groups), default=["หลัก"], key="ex_groups")
        asean_only = g2.checkbox("เฉพาะอาเซียน", key="ex_asean")
        complete_only = g3.checkbox("เฉพาะปีที่ข้อมูลครบ", key="ex_complete")

    d = df[df["year"].between(*yr)]
    if regions:
        d = d[d["region_th"].isin(regions)]
    if search.strip():
        d = d[d["country"].astype(str).str.contains(search.strip(), case=False, regex=False)]
    if asean_only:
        d = d[d["is_asean"]]
    if complete_only:
        d = d[d["year_complete"]]
    cols = ["country", "region_th", "year"] + [c for g in picked for c in groups[g]]
    if d.empty:
        empty_state("ไม่พบข้อมูลตามตัวกรอง ตรวจคำค้นหา (ใช้ชื่อภาษาอังกฤษ) หรือล้างตัวกรอง",
                    ["ex_region", "ex_search", "ex_years", "ex_asean", "ex_complete"])
        return
    s1, s2 = st.columns([1, 2])
    sort_col = s1.selectbox("เรียงตาม", cols, index=2, key="ex_sort")
    d = d[cols].sort_values([sort_col, "country"], ascending=[sort_col in ("country", "region_th", "year"), True])
    s2.markdown(f"<div style='padding-top:2rem;color:{MUTED}'>พบ {len(d):,} แถว จาก {d['country'].nunique()} ประเทศ · "
                f"คลิกหัวคอลัมน์ในตารางเพื่อเรียงได้เช่นกัน</div>", unsafe_allow_html=True)
    st.dataframe(d, hide_index=True, width="stretch", height=440)

    b1, b2, _ = st.columns([1, 1, 3])
    b1.download_button("ดาวน์โหลด CSV", d.to_csv(index=False).encode("utf-8-sig"), "energy_filtered.csv",
                       "text/csv", width="stretch")
    xls = to_excel_bytes(d)
    if xls:
        b2.download_button("ดาวน์โหลด Excel", xls, "energy_filtered.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    dic = load_side_table("data_dictionary.csv")
    if dic is not None:
        with st.expander("ความหมายของแต่ละคอลัมน์ (Data Dictionary)"):
            show_d = dic[dic["column"].isin(cols)][["column", "description_th", "unit_or_domain", "missing_pct"]]
            st.dataframe(show_d.rename(columns={"column": "คอลัมน์", "description_th": "ความหมาย",
                                                "unit_or_domain": "หน่วย", "missing_pct": "ค่าว่าง (%)"}),
                         hide_index=True, width="stretch")
    source()


def page_about():
    df, _, info = DATA
    breadcrumb("วิธีใช้และที่มาข้อมูล")
    st.title("วิธีใช้และที่มาข้อมูล")
    left, right = st.columns(2)
    with left, panel():
        panel_title("ใช้งานใน 3 ขั้น")
        st.markdown("""
1. **หน้าหลัก** ดูกราฟสำคัญทั้งหมด เลื่อนแถบปีและเลือกประเทศที่โฟกัสด้านบน
2. **รายประเทศ** เลือกประเทศและช่วงปีเอง ดูความเข้มคาร์บอนและดาวน์โหลดข้อมูล
3. **เปรียบเทียบ / ตารางข้อมูล** จัดอันดับหลายประเทศ กรอง และส่งออก CSV หรือ Excel
""")
    with right, panel():
        panel_title("ข้อจำกัด")
        st.markdown("""
- GDP มีถึงปี 2018 เท่านั้น
- ภาพรวมโลกใช้ปีที่ข้อมูลครบเท่านั้น (ถึงปี 2021)
- ไฟฟ้าต่อคนเบ้ขวามาก จึงใช้ **มัธยฐาน** เป็นค่ากลาง
- ประเทศที่ผลิตไฟฟ้า < 0.1 TWh ตัวเลขถูกปัด
- สหสัมพันธ์ไม่ได้บอกเหตุและผล
""")
    with panel():
        panel_title("ข้อมูลและคุณภาพ",
                    f"Our World in Data · {info['rows']:,} แถว · {df['country'].nunique()} ประเทศ · ปี {df['year'].min()}–{df['year'].max()} "
                    f"· ปีล่าสุดที่ข้อมูลครบ {int(df.loc[df['year_complete'], 'year'].max())}")
        q = load_side_table("data_quality_summary.csv")
        if q is not None:
            st.dataframe(q.rename(columns={q.columns[0]: "ตัวชี้วัด"}), hide_index=True, width="stretch")
    with panel():
        panel_title("ประสิทธิภาพระบบ", "วัดจากเซิร์ฟเวอร์จริงทุกครั้งที่เปิดหน้านี้")
        t0 = time.perf_counter()
        _ = df[df["country"] == "Thailand"]
        filter_ms = (time.perf_counter() - t0) * 1000
        m = st.columns(3)
        kpi(m[0], "โหลดข้อมูลครั้งแรก", f"{info['load_ms']:.0f}", "ms")
        kpi(m[1], "คำนวณภาพรวมล่วงหน้า", f"{info['agg_ms']:.0f}", "ms")
        kpi(m[2], "กรองข้อมูล 1 ประเทศ", f"{filter_ms:.1f}", "ms")
        st.caption("วิธีที่ทำให้เร็ว: แคชข้อมูลด้วย st.cache_data (โหลดครั้งเดียวต่อเซิร์ฟเวอร์) · คำนวณภาพรวมโลกไว้ล่วงหน้า · "
                   "ใช้ชนิด category กับคอลัมน์ข้อความ · ไฟล์ข้อมูลเล็ก (~1 MB)")
    source()


# ---------------------------------------------------------------------------
# 9) เริ่มแอป
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    login_page()
    st.stop()

try:
    with st.spinner("กำลังโหลดข้อมูล..."):
        DATA = load_data()
except FileNotFoundError:
    st.error("ไม่พบไฟล์ข้อมูล energy_clean.csv ให้วางไฟล์ไว้ในโฟลเดอร์ dashboard/data/ "
             "(คัดลอกจาก final/energy_clean.csv) แล้วกดรีเฟรชหน้า")
    st.stop()
except Exception as e:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {e} ลองรีเฟรชหน้า ถ้ายังไม่หาย ให้รันขั้นทำความสะอาดที่ 5 ใหม่")
    st.stop()

PAGES = {
    "home": st.Page(page_home, title="หน้าหลัก", icon="🏠", url_path="home", default=True),
    "country": st.Page(page_country, title="รายประเทศ", icon="📈", url_path="country"),
    "compare": st.Page(page_compare, title="เปรียบเทียบ", icon="📊", url_path="compare"),
    "explorer": st.Page(page_explorer, title="ตารางข้อมูล", icon="🗂️", url_path="data"),
    "about": st.Page(page_about, title="วิธีใช้และที่มาข้อมูล", icon="ℹ️", url_path="about"),
}
with st.sidebar:
    st.markdown("### ⚡ ไฟฟ้าไทยและอาเซียน")
    st.caption(f"เข้าสู่ระบบ: {st.session_state['user']}")
    st.button("ออกจากระบบ", on_click=lambda: st.session_state.pop("user", None), width="stretch")
nav = st.navigation(list(PAGES.values()))
nav.run()
