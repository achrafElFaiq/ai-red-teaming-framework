"""
RedTeaming Framework
====================
Three tabs: Overview · Campaigns · Attacks
Light warm minimal theme.

Launch:  streamlit run src/redteaming/ui/streamlit_dashboard.py
"""

import json
import html
import re
from datetime import datetime
from pathlib import Path

import streamlit as st


from redteaming.settings import get_runtime_settings
from redteaming.infrastructure.persistence.json_report_store import JsonReportStore

st.set_page_config(
    page_title="RedTeaming Framework",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_ACCENT = ["#C0392B", "#2563EB", "#D97706", "#059669", "#7C3AED", "#6B7280"]

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, .stApp, [data-testid="stApp"] {
    background: #F5F4F0 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #111111;
}
[data-testid="stHeader"]  { background: #F5F4F0 !important; border-bottom: 1px solid #E5E3DE; }
[data-testid="stToolbar"] { background: #F5F4F0 !important; }
#MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }

section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E5E3DE !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div { padding: 24px 20px; }
section[data-testid="stSidebar"] * { color: #555 !important; }
section[data-testid="stSidebar"] label { color: #111 !important; font-weight: 500; font-size: 13px; }
section[data-testid="stSidebar"] hr { border-color: #F0EEEA; }

.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: transparent;
    border-bottom: 1px solid #E5E3DE; padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    color: #888 !important; font-weight: 500; font-size: 14px;
    padding: 10px 18px; border-radius: 0;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #111 !important; border-bottom: 2px solid #111 !important;
    background: transparent !important;
}
[data-testid="stExpander"] {
    background: #FFFFFF !important; border: 1px solid #E5E3DE !important;
    border-radius: 10px !important; overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-size: 13px; font-weight: 500; color: #666 !important; padding: 14px 18px;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D8D5CE; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def e(v) -> str:
    return html.escape(str(v)) if v else ""


def load_reports(reports_path: Path) -> list[dict]:
    out = []
    for report_file in sorted(reports_path.iterdir(), key=lambda path: path.name, reverse=True):
        if report_file.suffix != ".json":
            continue
        try:
            with open(report_file, encoding="utf-8") as fh:
                d = json.load(fh)
                d["_filename"] = report_file.name
                out.append(d)
        except Exception:
            pass
    return out


def is_breached(r: dict) -> bool:
    conv = r.get("conversation")
    if conv and isinstance(conv, dict):
        return bool(conv.get("achieved", False))
    for p in r.get("prompts") or []:
        if not p.get("passed", True):
            return True
    return False


def parse_ts(r: dict) -> datetime | None:
    raw = r.get("timestamp", "")
    try:
        return datetime.fromisoformat(raw) if raw else None
    except Exception:
        return None


def parse_campaign_run_ts(r: dict) -> datetime | None:
    raw = r.get("campaign_run_timestamp", "")
    try:
        return datetime.fromisoformat(raw) if raw else None
    except Exception:
        return None


def campaign_instance_key(r: dict) -> str:
    run_id = str(r.get("campaign_run_id", "")).strip()
    if run_id:
        return f"run:{run_id}"
    return f"name:{r.get('campaign_name') or 'Uncategorized'}"


def campaign_title(reports: list[dict]) -> str:
    return first_campaign_value(reports, "campaign_name", "Uncategorized")


def campaign_instance_timestamp(reports: list[dict]) -> datetime | None:
    for report in reports:
        run_ts = parse_campaign_run_ts(report)
        if run_ts:
            return run_ts
    timestamps = [ts for report in reports if (ts := parse_ts(report)) is not None]
    return max(timestamps, default=None)


def format_campaign_timestamp(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "Unknown run"


def campaign_label(reports: list[dict]) -> str:
    return f"{campaign_title(reports)} · {format_campaign_timestamp(campaign_instance_timestamp(reports))}"


def group_by_campaign(reports: list[dict]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = {}
    for r in reports:
        g.setdefault(campaign_instance_key(r), []).append(r)
    return g


def campaign_color(idx: int) -> str:
    return _ACCENT[idx % len(_ACCENT)]


def first_campaign_value(reports: list[dict], key: str, default: str = "—") -> str:
    return next((str(r.get(key, "")).strip() for r in reports if str(r.get(key, "")).strip()), default)


def delete_campaign_reports(reports_path: Path, reports: list[dict]) -> int:
    filenames = [r.get("_filename", "") for r in reports if r.get("_filename")]
    store = JsonReportStore(reports_path)
    return store.delete_files(filenames)


# ─────────────────────────────────────────────────────────────────
# HTML primitives
# ─────────────────────────────────────────────────────────────────

def badge(text: str, bg: str, color: str) -> str:
    return (
        f'<span style="background:{bg};color:{color};font-size:11px;font-weight:600;'
        f'padding:3px 10px;border-radius:6px;display:inline-block;letter-spacing:0.01em">'
        f'{e(text)}</span>'
    )


def engine_badge(fw: str) -> str:
    return badge("PYRIT", "#EEF2FF", "#3730A3") if fw == "pyrit" else badge("GARAK", "#F5F3FF", "#6D28D9")


def outcome_badge(breached: bool) -> str:
    return badge("BREACHED", "#FEF2F2", "#B91C1C") if breached else badge("RESISTED", "#F0FDF4", "#15803D")


def dot(color: str) -> str:
    return (
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
        f'background:{color};margin:0 3px;vertical-align:middle;flex-shrink:0"></span>'
    )


def kpi_card(label: str, value, sub: str = "", value_color: str = "#111") -> str:
    sub_html = f'<div style="font-size:12px;color:#888;margin-top:5px;line-height:1.4">{sub}</div>' if sub else ""
    return (
        f'<div style="background:#FFFFFF;border:1px solid #E5E3DE;border-radius:12px;padding:22px 24px">'
        f'<div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.08em;font-weight:600">{label}</div>'
        f'<div style="font-size:30px;font-weight:700;color:{value_color};margin-top:6px;line-height:1">{value}</div>'
        f'{sub_html}</div>'
    )


def breach_bar_html(rate: int) -> str:
    bar_c = "#B91C1C" if rate >= 75 else ("#D97706" if rate >= 50 else ("#2563EB" if rate >= 25 else "#059669"))
    return (
        f'<div style="display:flex;align-items:center;gap:14px;margin:16px 0 4px">'
        f'<span style="font-size:15px;font-weight:700;color:{bar_c};min-width:44px">{rate}%</span>'
        f'<div style="flex:1;height:6px;background:#E5E3DE;border-radius:3px;overflow:hidden">'
        f'<div style="width:{rate}%;height:100%;background:{bar_c};border-radius:3px"></div></div>'
        f'<span style="font-size:12px;color:#999;min-width:80px">breach rate</span></div>'
    )


def section_label(text: str) -> str:
    return (
        f'<div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.08em;'
        f'font-weight:600;margin:28px 0 14px">{text}</div>'
    )


def highlight_leaks(text: str) -> str:
    t = e(text)
    patterns = [
        r'(\b(?:score|scoring|priorit[ée]|remise|r[ée]f[ée]rence|discount|priority|eligible?|eligibility|rang|rank)\b[\s\w]*?)\s*[:=]\s*(\d[\d\s,\.]*%?)',
        r'(\b\w+)\s*:\s*(\d{1,3}(?:[.,]\d+)+%?)',
    ]
    hl = 'background:#FEF2F2;color:#B91C1C;padding:1px 6px;border-radius:4px;font-weight:600;border:1px solid rgba(185,28,28,.15)'
    for pat in patterns:
        t = re.sub(pat, lambda m: f'<mark style="{hl}">{m.group(0)}</mark>', t, flags=re.IGNORECASE)
    return t


def campaign_stats(reports: list[dict]) -> dict:
    total = len(reports)
    breached = sum(1 for r in reports if is_breached(r))
    resisted = total - breached
    rate = round(breached / total * 100) if total else 0
    pyrit_n = sum(1 for r in reports if r.get("framework") == "pyrit")
    garak_n = total - pyrit_n
    turns = leaked = probes = failed_probes = 0
    for r in reports:
        conv = r.get("conversation")
        if conv and isinstance(conv, dict):
            t_list = conv.get("turns", [])
            turns += len(t_list)
            leaked += sum(1 for t in t_list if t.get("score"))
        for p in r.get("prompts") or []:
            probes += 1
            if not p.get("passed", True):
                failed_probes += 1
    pyrit_convs = [r for r in reports if r.get("framework") == "pyrit" and isinstance(r.get("conversation"), dict)]
    avg_depth = round(
        sum(len(r["conversation"].get("turns", [])) for r in pyrit_convs) / len(pyrit_convs), 1
    ) if pyrit_convs else 0
    return dict(total=total, breached=breached, resisted=resisted, rate=rate,
                pyrit=pyrit_n, garak=garak_n, turns=turns, leaked=leaked,
                avg_depth=avg_depth, probes=probes, failed_probes=failed_probes)


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────

def build_sidebar(reports: list[dict], campaigns: dict[str, list[dict]]) -> tuple[list[dict], str | None]:
    with st.sidebar:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;padding:8px 0 28px">'
            '<div style="width:10px;height:10px;border-radius:50%;background:#C0392B;flex-shrink:0"></div>'
            '<span style="font-size:17px;font-weight:700;color:#111 !important;letter-spacing:-0.01em">Dashboard</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        options = ["__all__"] + sorted(
            campaigns.keys(),
            key=lambda key: campaign_instance_timestamp(campaigns[key]) or datetime.min,
            reverse=True,
        )
        sel = st.selectbox(
            "Campaign",
            options,
            format_func=lambda option: "All Campaigns" if option == "__all__" else campaign_label(campaigns[option]),
        )

        st.markdown("---")
        st.markdown('<p style="font-size:12px;font-weight:600;color:#333 !important;margin-bottom:6px">Framework</p>', unsafe_allow_html=True)
        show_pyrit  = st.checkbox("PyRIT",  value=True)
        show_garak  = st.checkbox("Garak",  value=True)

        st.markdown("---")
        st.markdown('<p style="font-size:12px;font-weight:600;color:#333 !important;margin-bottom:6px">Outcome</p>', unsafe_allow_html=True)
        show_breached = st.checkbox("Breached", value=True)
        show_resisted = st.checkbox("Resisted", value=True)

        st.markdown("---")
        st.markdown(
            f'<p style="font-size:11px;color:#CCC !important;margin-top:4px">'
            f'{len(reports)} reports · {len(campaigns)} campaign(s)</p>',
            unsafe_allow_html=True,
        )

    sel_campaign = None if sel == "__all__" else sel
    out = list(reports)
    if sel_campaign:
        out = [r for r in out if campaign_instance_key(r) == sel_campaign]
    if not show_pyrit:  out = [r for r in out if r.get("framework") != "pyrit"]
    if not show_garak:  out = [r for r in out if r.get("framework") != "garak"]
    if not show_breached: out = [r for r in out if not is_breached(r)]
    if not show_resisted: out = [r for r in out if is_breached(r)]
    return out, sel_campaign


# ─────────────────────────────────────────────────────────────────
# Tab 1 — Overview
# ─────────────────────────────────────────────────────────────────

def render_overview(reports: list[dict], campaigns: dict[str, list[dict]]):
    total    = len(reports)
    breached = sum(1 for r in reports if is_breached(r))
    resisted = total - breached
    rate     = round(breached / total * 100) if total else 0
    pyrit_n  = sum(1 for r in reports if r.get("framework") == "pyrit")
    garak_n  = total - pyrit_n
    pyrit_convs = [r for r in reports if r.get("framework") == "pyrit" and isinstance(r.get("conversation"), dict)]
    avg_depth = round(
        sum(len(r["conversation"].get("turns", [])) for r in pyrit_convs) / len(pyrit_convs), 1
    ) if pyrit_convs else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card("Campaigns", len(campaigns), f"{total} total attacks"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Breached", breached, f"{rate}% of all attacks", "#B91C1C"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Resisted", resisted, f"{100 - rate}% of all attacks", "#15803D"), unsafe_allow_html=True)

    st.markdown(breach_bar_html(rate), unsafe_allow_html=True)
    st.markdown(section_label("Campaigns"), unsafe_allow_html=True)

    sorted_campaigns = sorted(
        campaigns.items(),
        key=lambda item: campaign_instance_timestamp(item[1]) or datetime.min,
        reverse=True,
    )
    for idx, (campaign_key, cr) in enumerate(sorted_campaigns):
        ck = campaign_stats(cr)
        accent = campaign_color(idx)
        bar_c  = "#B91C1C" if ck["rate"] >= 50 else ("#D97706" if ck["rate"] >= 25 else "#059669")
        target_url = next((r.get("target_url", "") for r in cr if r.get("target_url")), "—")
        target_model = first_campaign_value(cr, "target_model")
        architecture_type = first_campaign_value(cr, "target_architecture_type")
        cname = campaign_title(cr)
        run_label = format_campaign_timestamp(campaign_instance_timestamp(cr))
        st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #E5E3DE;border-left:4px solid {accent};
            border-radius:0 12px 12px 0;padding:18px 22px;margin-bottom:10px;position:relative">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap">
        <div>
            <div style="font-size:15px;font-weight:600;color:#111;margin-bottom:6px">{e(cname)}</div>
            <div style="font-size:11px;color:#999;font-family:monospace;margin-bottom:8px">Run: {e(run_label)}</div>
            <div style="font-size:12px;color:#888;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span>{ck['total']} attack(s)</span><span>·</span>
                <span style="display:inline-flex;align-items:center;gap:3px">{dot('#B91C1C')}{ck['breached']} breached</span>
                <span>·</span>
                <span style="display:inline-flex;align-items:center;gap:3px">{dot('#15803D')}{ck['resisted']} resisted</span>
                <span>·</span><span>pyrit {ck['pyrit']} · garak {ck['garak']}</span>
                <span>·</span><span style="font-family:monospace;font-size:11px">{e(target_url)}</span>
            </div>
            <div style="font-size:12px;color:#888;margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span><strong style="color:#555">Model:</strong> {e(target_model)}</span>
                <span>·</span>
                <span><strong style="color:#555">Architecture:</strong> {e(architecture_type)}</span>
            </div>
        </div>
        <div style="text-align:right;flex-shrink:0">
            <div style="font-size:22px;font-weight:700;color:{bar_c}">{ck['rate']}%</div>
            <div style="font-size:11px;color:#999">breach rate</div>
        </div>
    </div>
    <div style="height:4px;background:#F0EEEA;border-radius:2px;margin-top:14px;overflow:hidden">
        <div style="width:{ck['rate']}%;height:100%;background:{bar_c};border-radius:2px"></div>
    </div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Tab 2 — Campaigns
# ─────────────────────────────────────────────────────────────────

def render_campaigns(reports_path: Path, reports: list[dict], campaigns: dict[str, list[dict]], sel: str | None):
    if sel:
        _render_one_campaign(reports_path, sel, campaigns.get(sel, []), 0)
    else:
        sorted_campaigns = sorted(
            campaigns.items(),
            key=lambda x: campaign_instance_timestamp(x[1]) or datetime.min,
            reverse=True
        )
        for idx, (campaign_key, cr) in enumerate(sorted_campaigns):
            ck = campaign_stats(cr)
            label = campaign_label(cr)

            with st.expander(f"{e(label)} · {ck['total']} attacks · {ck['rate']}% breach rate"):
                _render_one_campaign(reports_path, campaign_key, cr, idx)

            if idx < len(sorted_campaigns) - 1:
                st.markdown("<hr style='border:none;border-top:1px solid #E5E3DE;margin:12px 0'>", unsafe_allow_html=True)


def _render_one_campaign(reports_path: Path, campaign_key: str, reports: list[dict], idx: int):
    if not reports:
        st.markdown('<div style="color:#888;font-size:13px">No attacks in this campaign run.</div>', unsafe_allow_html=True)
        return

    ck     = campaign_stats(reports)
    accent = campaign_color(idx)
    bar_c  = "#B91C1C" if ck["rate"] >= 50 else ("#D97706" if ck["rate"] >= 25 else "#059669")
    target_model = first_campaign_value(reports, "target_model")
    architecture_type = first_campaign_value(reports, "target_architecture_type")
    target_url = first_campaign_value(reports, "target_url")
    cname = campaign_title(reports)
    run_label = format_campaign_timestamp(campaign_instance_timestamp(reports))

    action_col, _ = st.columns([1, 5])
    with action_col:
        if st.button("🗑 Delete this run", key=f"delete-{campaign_key}", type="secondary", use_container_width=True):
            delete_campaign_reports(reports_path, reports)
            st.rerun()

    st.markdown(f"""
<div style="border-left:4px solid {accent};padding-left:16px;margin-bottom:22px">
    <div style="font-size:20px;font-weight:700;color:#111;letter-spacing:-0.01em">{e(cname)}</div>
    <div style="font-size:11px;color:#999;font-family:monospace;margin-top:4px">Run: {e(run_label)}</div>
    <div style="font-size:12px;color:#888;margin-top:5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">
        <span>{ck['total']} attack(s)</span><span>·</span>
        <span style="display:inline-flex;align-items:center;gap:3px">{dot('#B91C1C')}{ck['breached']} breached</span>
        <span>·</span>
        <span style="display:inline-flex;align-items:center;gap:3px">{dot('#15803D')}{ck['resisted']} resisted</span>
        <span>·</span><span>pyrit {ck['pyrit']} · garak {ck['garak']}</span>
    </div>
    <div style="font-size:12px;color:#888;margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span><strong style="color:#555">Model:</strong> {e(target_model)}</span>
        <span>·</span>
        <span><strong style="color:#555">Architecture:</strong> {e(architecture_type)}</span>
        <span>·</span>
        <span style="font-family:monospace;font-size:11px">{e(target_url)}</span>
    </div>
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(kpi_card("Attacks",      ck["total"],         f"pyrit {ck['pyrit']} · garak {ck['garak']}"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Breached",     ck["breached"],      f"{ck['rate']}% breach rate", "#B91C1C"),       unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Resisted",     ck["resisted"],      f"{100 - ck['rate']}% resisted", "#15803D"),    unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("Conversations",  ck["turns"],         f"{ck['leaked']} leaked"), unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("Garak probes", ck["probes"],        f"{ck['failed_probes']} failed"),               unsafe_allow_html=True)

    st.markdown(breach_bar_html(ck["rate"]), unsafe_allow_html=True)

    st.markdown(section_label(f"Attacks — {e(cname)} ({len(reports)})"), unsafe_allow_html=True)
    sorted_reports = sorted(reports, key=lambda r: parse_ts(r) or datetime.min, reverse=True)
    for r in sorted_reports:
        _render_attack_card(r)


# ─────────────────────────────────────────────────────────────────
# Tab 3 — Attacks
# ─────────────────────────────────────────────────────────────────

def render_attacks(reports: list[dict]):
    st.markdown(f'<div style="font-size:12px;color:#AAA;margin-bottom:16px">{len(reports)} attack(s) displayed</div>', unsafe_allow_html=True)
    sorted_reports = sorted(reports, key=lambda r: parse_ts(r) or datetime.min, reverse=True)
    for r in sorted_reports:
        _render_attack_card(r)


# ─────────────────────────────────────────────────────────────────
# Shared — attack card
# ─────────────────────────────────────────────────────────────────

def _render_attack_card(report: dict):
    fw       = report.get("framework", "")
    breached = is_breached(report)
    border   = "#B91C1C" if breached else "#059669"
    ts_raw   = report.get("timestamp", "")
    ts_fmt   = ts_raw[:16].replace("T", "  ") if ts_raw else "—"

    if fw == "pyrit":
        meta  = ts_fmt
    else:
        prompts = report.get("prompts") or []
        failed  = sum(1 for p in prompts if not p.get("passed", True))
        meta    = f"{len(prompts) - failed}✓  {failed}✗  of {len(prompts)} probes · {ts_fmt}"

    st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #E5E3DE;border-left:3px solid {border};
            border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:8px;
            display:flex;align-items:center;gap:10px;flex-wrap:wrap">
    {engine_badge(fw)}
    {outcome_badge(breached)}
    <span style="font-size:13px;font-weight:500;color:#111;flex:1;min-width:0">{e(report.get('attack_name',''))}</span>
    <span style="font-size:11px;color:#BBB;white-space:nowrap;font-family:monospace">{meta}</span>
</div>""", unsafe_allow_html=True)

    with st.expander("View conversation" if fw == "pyrit" else "View probes", expanded=False):
        if fw == "pyrit":
            _render_conversation(report)
        else:
            _render_probes(report)


# ─────────────────────────────────────────────────────────────────
# Conversation trace (PyRIT)
# ─────────────────────────────────────────────────────────────────

def _render_conversation(report: dict):
    conv = report.get("conversation", {})
    if not isinstance(conv, dict):
        st.markdown('<div style="color:#AAA;text-align:center;padding:40px;font-size:13px">No conversation data.</div>', unsafe_allow_html=True)
        return

    objective = conv.get("objective", "")
    achieved  = conv.get("achieved", False)
    turns     = conv.get("turns", [])

    if objective:
        st.markdown(f"""
<div style="background:#EEF2FF;border-left:3px solid #3730A3;border-radius:0 8px 8px 0;
            padding:12px 16px;margin-bottom:20px">
    <div style="font-size:10px;color:#3730A3;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-bottom:6px">Objective</div>
    <div style="font-size:14px;color:#1E1B4B;line-height:1.6">{e(objective)}</div>
</div>""", unsafe_allow_html=True)

    if not turns:
        st.markdown('<div style="color:#AAA;text-align:center;padding:32px;font-size:13px">No turns recorded.</div>', unsafe_allow_html=True)
        return

    for turn in turns:
        p_txt    = turn.get("prompt", "")
        r_txt    = turn.get("response", "")
        score    = turn.get("score", False)
        rationale = turn.get("rationale", "")

        p_html = e(p_txt) if p_txt else '<em style="color:#CCC">— empty —</em>'
        st.markdown(f"""
<div style="margin-bottom:4px">
    <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">Message · Attacker</div>
    <div style="background:#EDEBE8;border-radius:12px;padding:16px 20px;font-size:14px;line-height:1.7;color:#111;white-space:pre-wrap;word-break:break-word">{p_html}</div>
</div>""", unsafe_allow_html=True)

        leaked_border = "rgba(185,28,28,.25)" if score else "#E5E3DE"
        r_html = highlight_leaks(r_txt) if (score and r_txt) else (e(r_txt) if r_txt else '<em style="color:#CCC">— no response —</em>')
        st.markdown(f"""
<div style="margin-bottom:20px;margin-left:5%">
    <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">Message · Target</div>
    <div style="background:#FFFFFF;border:1px solid {leaked_border};border-radius:12px;padding:16px 20px;font-size:14px;line-height:1.7;color:#111;white-space:pre-wrap;word-break:break-word">{r_html}</div>
</div>""", unsafe_allow_html=True)

    last      = turns[-1] if turns else {}
    rationale = last.get("rationale", "")
    rat_html  = f" — {e(rationale)}" if rationale else ""
    if achieved:
        breach_turn = next((t.get("turn", "?") for t in turns if t.get("score")), len(turns))
        st.markdown(f'<div style="background:#FEF2F2;border:1px solid rgba(185,28,28,.2);border-radius:8px;padding:16px 18px;font-size:13px;font-weight:600;color:#B91C1C;margin-top:28px;margin-bottom:20px;display:flex;align-items:center;gap:8px;justify-content:flex-start"><span style="font-size:16px">⚠️</span>Scored as breached{rat_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:#F0FDF4;border:1px solid rgba(21,128,61,.2);border-radius:8px;padding:16px 18px;font-size:13px;font-weight:600;color:#15803D;margin-top:28px;margin-bottom:20px;display:flex;align-items:center;gap:8px;justify-content:flex-start"><span style="font-size:16px">✅</span>Target resisted{rat_html}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Garak probe table
# ─────────────────────────────────────────────────────────────────

def _render_probes(report: dict):
    prompts = report.get("prompts") or []
    if not prompts:
        st.markdown('<div style="color:#AAA;text-align:center;padding:32px;font-size:13px">No probes recorded.</div>', unsafe_allow_html=True)
        return

    failed_n = sum(1 for p in prompts if not p.get("passed", True))

    # Build entire table as one HTML string for performance
    rows_html = []
    for p in prompts:
        passed = p.get("passed", True)
        prompt_text = p.get("prompt", "")
        response_text = p.get("response", "")
        detector = p.get("detector", "")
        bl = "3px solid #B91C1C" if not passed else "3px solid transparent"
        bg = "#FFFAFA" if not passed else "#FFFFFF"

        # Truncate to ~60 chars for glanceable view
        trunc_prompt = e(prompt_text[:60]) + ("…" if len(prompt_text) > 60 else "")
        trunc_response = e(response_text[:60]) + ("…" if len(response_text) > 60 else "")

        # Expandable full text via HTML <details> — no Streamlit widget overhead
        prompt_cell = f'<span style="font-size:12px;color:#333">{trunc_prompt}</span>'
        if len(prompt_text) > 60:
            prompt_cell += (
                f'<details style="margin-top:6px"><summary style="font-size:10px;color:#2563EB;cursor:pointer;font-weight:500">show prompt</summary>'
                f'<div style="margin-top:6px;font-size:12px;color:#333;white-space:pre-wrap;word-break:break-word;background:#F9F9F7;padding:8px;border-radius:6px">{e(prompt_text)}</div></details>'
            )

        response_cell = f'<span style="font-size:12px;color:#666">{trunc_response}</span>'
        if len(response_text) > 60:
            response_cell += (
                f'<details style="margin-top:6px"><summary style="font-size:10px;color:#2563EB;cursor:pointer;font-weight:500">show response</summary>'
                f'<div style="margin-top:6px;font-size:12px;color:#555;white-space:pre-wrap;word-break:break-word;background:#F9F9F7;padding:8px;border-radius:6px">{e(response_text)}</div></details>'
            )

        rows_html.append(
            f'<tr style="background:{bg};border-left:{bl};border-bottom:1px solid #F5F4F0">'
            f'<td style="padding:10px 12px;vertical-align:top;overflow:hidden">{prompt_cell}</td>'
            f'<td style="padding:10px 12px;vertical-align:top;overflow:hidden">{response_cell}</td>'
            f'<td style="padding:10px 12px;font-size:11px;color:#888;vertical-align:top">{e(detector)}</td>'
            f'<td style="padding:10px 12px;vertical-align:top">{outcome_badge(not passed)}</td>'
            f'</tr>'
        )

    table_html = f"""
<div style="font-size:12px;color:#888;margin-bottom:12px;font-weight:600">{failed_n} of {len(prompts)} probes breached</div>
<div style="background:#FFFFFF;border:1px solid #E5E3DE;border-radius:10px;overflow:hidden">
<table style="width:100%;border-collapse:collapse;table-layout:fixed">
<thead>
<tr style="border-bottom:1px solid #E5E3DE">
    <th style="padding:10px 12px;font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;text-align:left;width:30%">Prompt</th>
    <th style="padding:10px 12px;font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;text-align:left;width:30%">Response</th>
    <th style="padding:10px 12px;font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;text-align:left;width:22%">Detector</th>
    <th style="padding:10px 12px;font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:0.08em;text-align:left;width:18%">Outcome</th>
</tr>
</thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    _actual_root = Path(__file__).resolve().parents[3]
    reports_path = (_actual_root / get_runtime_settings(frameworks=set()).reports.json_reports_dir).resolve()

    if not reports_path.exists() or not any(reports_path.glob("*.json")):
        st.markdown(
            f'<div style="text-align:center;padding:80px;color:#AAA;font-size:13px">'
            f'No reports found in <code style="font-size:12px">{e(str(reports_path))}</code>'
            f' — run your first campaign.</div>',
            unsafe_allow_html=True,
        )
        return

    all_reports = load_reports(reports_path)
    campaigns   = group_by_campaign(all_reports)
    filtered, sel = build_sidebar(all_reports, campaigns)
    f_camps     = group_by_campaign(filtered)

    tab1, tab2, tab3 = st.tabs(["Overview", "Campaigns", "Attacks"])

    with tab1: render_overview(filtered, f_camps)
    with tab2: render_campaigns(reports_path, filtered, f_camps, sel)
    with tab3: render_attacks(filtered)


if __name__ == "__main__":
    main()


