import streamlit as st
import json, subprocess, sys
from pathlib import Path
from datetime import date

BASE_DIR = Path('/home/admin/workspace/ai-bubble-monitor')
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'
REPORTS_DIR = BASE_DIR / 'reports' / 'weekly'
CONTENT_DIR = BASE_DIR / 'content_output'
INTERVIEWS_DIR = Path('/home/admin/workspace/silicon-valley-interviews')

st.set_page_config(
    page_title="AI 行业洞察系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #111318;
    border-right: 1px solid #2a2d3a;
}
[data-testid="stSidebar"] * { color: #e4e4e7 !important; }
.main-header {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}
.sub-header { color: #9ca3af; font-size: 0.9rem; margin-bottom: 2rem; }
.stat-card {
    background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 12px;
    padding: 18px 20px; text-align: center;
}
.stat-number { font-size: 2rem; font-weight: 700; color: #e4e4e7; }
.stat-label { font-size: 0.8rem; color: #9ca3af; margin-top: 4px; }
.stat-delta-pos { color: #22c55e; font-size: 0.85rem; }
.stat-delta-neg { color: #ef4444; font-size: 0.85rem; }
.company-row {
    background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px;
    padding: 14px 18px; margin: 6px 0;
    display: flex; align-items: center; justify-content: space-between;
}
.signal-box {
    background: #1a1d27; border-left: 4px solid #6366f1;
    border-radius: 0 8px 8px 0; padding: 12px 16px; margin: 8px 0;
}
.signal-facepalm { border-left-color: #f97316; }
.signal-corpse    { border-left-color: #ef4444; }
.signal-history   { border-left-color: #eab308; }
.signal-conflict  { border-left-color: #3b82f6; }
.signal-reversal  { border-left-color: #a855f7; }
.virality-bar {
    display: inline-block; height: 6px; border-radius: 3px;
    background: #6366f1; margin-right: 4px; vertical-align: middle;
}
code { background: #2a2d3a !important; color: #a5b4fc !important; }
.stButton button {
    background: #6366f1; color: white; border: none;
    border-radius: 8px; padding: 8px 20px; font-weight: 600;
}
.stButton button:hover { background: #4f46e5; }
hr { border-color: #2a2d3a; }
</style>
""", unsafe_allow_html=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def load_snapshots():
    snaps = sorted(SNAPSHOTS_DIR.glob('*.json'))
    data = []
    for s in snaps:
        try:
            data.append(json.loads(s.read_text()))
        except Exception:
            pass
    return data

def bubble_score(curr, prev):
    if not prev or prev.get('total', 0) == 0:
        return 0
    s = 0
    wow = (curr.get('total', 0) - prev['total']) / prev['total'] * 100
    if wow < -10: s += 3
    elif wow < -5: s += 2
    elif wow > 5: s -= 1
    if curr.get('gtm_ratio', 0) < prev.get('gtm_ratio', 0) - 3: s += 3
    if curr.get('manager_pct', 0) < prev.get('manager_pct', 0) - 5: s += 1
    return max(s, 0)

def bubble_badge(score):
    if score <= 2:  return "🟢", "#22c55e", "健康"
    if score <= 5:  return "🟡", "#eab308", "关注"
    if score <= 8:  return "🟠", "#f97316", "警告"
    return "🔴", "#ef4444", "危险"

def wow_text(curr, prev_total):
    if not prev_total: return "基线", "#9ca3af"
    d = curr.get('total', 0) - prev_total
    pct = d / prev_total * 100
    color = "#22c55e" if d >= 0 else "#ef4444"
    sign = "+" if d >= 0 else ""
    return f"{sign}{d} ({sign}{pct:.1f}%)", color

COMPANY_NAMES = {
    'openai': 'OpenAI', 'anthropic': 'Anthropic', 'deepmind': 'Google DeepMind',
    'bytedance': 'ByteDance', 'xai': 'xAI', 'mistral': 'Mistral AI',
    'stability': 'Stability AI', 'cohere': 'Cohere',
}

DETECTOR_STYLE = {
    'facepalm':     ('🎭', 'signal-facepalm', '打脸检测'),
    'corpse':       ('💀', 'signal-corpse',    '尸体检测'),
    'history_rhyme':('📜', 'signal-history',   '历史重演'),
    'conflict':     ('⚔️', 'signal-conflict',  '冲突检测'),
    'reversal':     ('🔄', 'signal-reversal',  '反转检测'),
}

# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="main-header">🔍 AI 洞察</div>', unsafe_allow_html=True)
    st.caption("AI Industry Insight System")
    st.divider()

    page = st.radio(
        "导航",
        ["📊 泡沫仪表盘", "📝 内容工作台", "🧠 知识图谱", "⚙️ 系统控制"],
        label_visibility="collapsed"
    )
    st.divider()

    snapshots = load_snapshots()
    if snapshots:
        latest = snapshots[-1]
        total_now = sum(c.get('total', 0) for c in latest.get('companies', {}).values())
        st.metric("最新日期", latest.get('date', 'N/A'))
        st.metric("快照期数", f"{len(snapshots)} 期")
        st.metric("总监测岗位", f"{total_now:,}")
    else:
        st.info("暂无数据")

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — 泡沫仪表盘
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 泡沫仪表盘":
    st.markdown('<div class="main-header">AI 泡沫追踪仪表盘</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">实时监测 8 家顶级 AI 公司的招聘趋势、GitHub 活跃度和泡沫信号</div>', unsafe_allow_html=True)

    if not snapshots:
        st.warning("⚠️ 暂无快照数据。请前往「系统控制」运行数据采集。")
        st.stop()

    current  = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) >= 2 else None
    companies = current.get('companies', {})

    total_now  = sum(c.get('total', 0) for c in companies.values())
    total_prev = sum(c.get('total', 0) for c in (previous or {}).get('companies', {}).values())
    scores = [bubble_score(c, (previous or {}).get('companies', {}).get(k, {})) for k, c in companies.items()]
    avg_sc = sum(scores) / max(len(scores), 1)
    em, color, label = bubble_badge(avg_sc)

    # Top KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        d, dcol = wow_text({'total': total_now}, total_prev)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_now:,}</div>
            <div class="stat-label">总监测岗位</div>
            <div style="color:{dcol};font-size:.85rem;margin-top:4px">{d}</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(companies)}</div>
            <div class="stat-label">监测公司数</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="font-size:2.5rem">{em}</div>
            <div class="stat-label">行业泡沫指数</div>
            <div style="color:{color};font-size:.9rem;font-weight:700">{avg_sc:.1f}/10 · {label}</div>
        </div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="font-size:1.4rem">{current.get('date','N/A')}</div>
            <div class="stat-label">数据截止日期</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # Company list
    st.subheader("各公司详情")
    for key, curr in sorted(companies.items(), key=lambda x: -x[1].get('total', 0)):
        prev_c = (previous or {}).get('companies', {}).get(key, {})
        pt = prev_c.get('total', 0)
        t  = curr.get('total', 0)
        sc = bubble_score(curr, prev_c)
        em2, col2, lbl2 = bubble_badge(sc)
        dtext, dcol = wow_text(curr, pt)
        name = COMPANY_NAMES.get(key, key.upper())

        with st.expander(f"{em2} **{name}** — {t:,} 岗位 &nbsp;&nbsp; `{dtext}` &nbsp;&nbsp; 泡沫分 {sc}/10", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("GTM 占比", f"{curr.get('gtm_ratio',0):.1f}%",
                      f"{curr.get('gtm_ratio',0)-prev_c.get('gtm_ratio',0):+.1f}pp" if pt else None)
            c2.metric("R&D 占比", f"{curr.get('research_ratio',0):.1f}%",
                      f"{curr.get('research_ratio',0)-prev_c.get('research_ratio',0):+.1f}pp" if pt else None)
            c3.metric("Senior 占比", f"{curr.get('senior_pct',0):.1f}%")
            c4.metric("Manager 占比", f"{curr.get('manager_pct',0):.1f}%")

            # Top departments
            depts = curr.get('by_department', {})
            if depts:
                st.markdown("**部门 TOP 5：** " + "  ·  ".join(
                    f"`{d}` {n}" for d, n in list(depts.items())[:5]))

            # GitHub
            gh = current.get('github', {}).get(key, {})
            if gh and not gh.get('error'):
                st.markdown(f"**GitHub:** [{gh.get('org','N/A')}](https://github.com/{gh.get('org','')}) &nbsp;·&nbsp; "
                           f"⭐ {gh.get('total_stars',0):,} &nbsp;·&nbsp; "
                           f"近 4 周 commits: **{gh.get('recent_commits_4w',0)}**")

            # arXiv
            ax = current.get('arxiv', {}).get(key, {})
            if ax and ax.get('total_recent', 0) > 0:
                papers = ax.get('papers', [])
                st.markdown(f"**arXiv:** {ax.get('total_recent',0)} 篇论文")
                if papers:
                    st.caption(f"最新: {papers[0].get('title','')[:80]}...")

    st.divider()

    # Charts
    st.subheader("数据图表")
    chart_dir_glob = sorted(CONTENT_DIR.glob('*/charts/bubble_dashboard.png'))
    if chart_dir_glob:
        c_left, c_right = st.columns(2)
        c_left.image(str(chart_dir_glob[-1]), caption="岗位分布 & 周环比变化", width=640)
        compare = sorted(CONTENT_DIR.glob('*/charts/company_comparison.png'))
        if compare:
            c_right.image(str(compare[-1]), caption="公司对比", width=640)
        trend = sorted(CONTENT_DIR.glob('*/charts/highlight_trend.png'))
        if trend:
            st.image(str(trend[-1]), caption="趋势图", width=900)
    else:
        st.info("暂无图表。请先运行「内容生成 Pipeline」。")

    st.divider()

    # Consistency check
    st.subheader("🎭 CEO 言行一致性检测")
    cc = current.get('consistency', {})
    if cc:
        for key, c_data in cc.items():
            if not c_data: continue
            name = COMPANY_NAMES.get(key, key.upper())
            all_passed = all(ch.get('passed', True) for ch in c_data.get('checks', []))
            header_icon = "✅" if all_passed else "❌"
            with st.expander(f"{header_icon} **{name}** — {c_data.get('narrative','')[:55]}..."):
                for chk in c_data.get('checks', []):
                    icon = "✅" if chk.get('passed') else "❌"
                    st.markdown(f"{icon} {chk.get('check','')} → *{chk.get('message','')}*")
    else:
        st.info("一致性检测数据将在下次运行 monitor.py 后更新。")

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — 内容工作台
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📝 内容工作台":
    st.markdown('<div class="main-header">内容生产工作台</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">从数据到内容的一键生产线</div>', unsafe_allow_html=True)

    # Story insights
    insights_files = sorted(CONTENT_DIR.glob('*/raw_insights.json'))
    if insights_files:
        stories = json.loads(insights_files[-1].read_text())
        st.subheader(f"🔥 本期爆点 ({len(stories)} 个)")

        for i, s in enumerate(stories[:5], 1):
            v = s.get('virality', 0)
            det = s.get('detector', 'other')
            icon, css_cls, det_label = DETECTOR_STYLE.get(det, ('💡', 'signal-box', det))
            virality_bars = '█' * v + '░' * (10 - v)
            border_colors = {
                'facepalm': '#f97316', 'corpse': '#ef4444',
                'history_rhyme': '#eab308', 'conflict': '#3b82f6', 'reversal': '#a855f7'
            }
            bc = border_colors.get(det, '#6366f1')
            st.markdown(f"""
            <div style="background:#1a1d27;border-left:4px solid {bc};border-radius:0 10px 10px 0;
                        padding:14px 18px;margin:8px 0;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="font-size:1.3em">{icon}</span>
                    <span style="color:#9ca3af;font-size:0.8em;background:#2a2d3a;padding:2px 8px;border-radius:4px">{det_label}</span>
                    <span style="color:{bc};font-size:0.85em;font-weight:700">传播力 {v}/10</span>
                    <span style="color:#6366f1;font-size:0.8em;letter-spacing:1px">{virality_bars}</span>
                </div>
                <div style="color:#e4e4e7;font-weight:600;margin-bottom:4px">{s.get('headline_cn','')}</div>
                <div style="color:#9ca3af;font-size:0.85em">{s.get('headline_en','')[:100]}...</div>
                <div style="margin-top:8px;font-size:0.8em;color:#a855f7">{s.get('emotion_cn','')}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # Content output
    content_dirs = sorted(CONTENT_DIR.glob('*/linkedin_post.md'))
    if not content_dirs:
        st.info("暂无生成的内容。请先运行内容 Pipeline。")
    else:
        latest_dir = content_dirs[-1].parent
        st.success(f"✅ 最新内容已生成: {latest_dir.name}")

        tab1, tab2, tab3 = st.tabs(["📋 LinkedIn 帖子（英文）", "🎬 YouTube 脚本（中文）", "🖼 图表素材"])

        with tab1:
            linkedin = (latest_dir / 'linkedin_post.md').read_text()
            st.markdown("**可直接复制发布到 LinkedIn：**")
            st.text_area("LinkedIn Post", linkedin, height=400, key="li_post")
            st.download_button("⬇️ 下载 .md 文件", linkedin,
                              file_name=f"linkedin_{latest_dir.name}.md", mime="text/markdown")

        with tab2:
            yt_path = latest_dir / 'youtube_script.md'
            if yt_path.exists():
                youtube = yt_path.read_text()
                st.markdown(youtube)
                st.download_button("⬇️ 下载脚本", youtube,
                                  file_name=f"youtube_{latest_dir.name}.md", mime="text/markdown")

        with tab3:
            charts_dir = latest_dir / 'charts'
            if charts_dir.exists():
                for img in sorted(charts_dir.glob('*.png')):
                    st.image(str(img), caption=img.stem, width=800)
                    with open(img, 'rb') as f:
                        st.download_button(f"⬇️ 下载 {img.name}", f.read(),
                                          file_name=img.name, mime="image/png",
                                          key=f"dl_{img.name}")
            else:
                st.info("暂无图表文件。")

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — 知识图谱
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 知识图谱":
    st.markdown('<div class="main-header">硅谷 AI 领袖知识图谱</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">9 位顶级 AI 领袖的观点交叉对比 · 基于 Lex Fridman Podcast 逐字稿</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🎯 交互式知识图谱", "📖 独立观察者"])

    with tab1:
        html_path = INTERVIEWS_DIR / '知识图谱.html'
        if html_path.exists():
            html_content = html_path.read_text()
            st.components.v1.html(html_content, height=750, scrolling=True)
        else:
            st.info("知识图谱文件不存在")

    with tab2:
        md_path = INTERVIEWS_DIR / '独立观察者观点汇编.md'
        if md_path.exists():
            st.markdown(md_path.read_text())

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 — 系统控制
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ 系统控制":
    st.markdown('<div class="main-header">系统控制面板</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">数据采集 · 内容生成 · 系统配置</div>', unsafe_allow_html=True)

    col_run, col_cfg = st.columns([1, 1])

    with col_run:
        st.subheader("运行 Pipeline")

        st.markdown("""
        <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;padding:16px;margin-bottom:16px">
            <div style="color:#9ca3af;font-size:.85em">
                <b>Step 1</b> — 爬取 8 家公司最新数据（约 3-5 分钟）<br>
                <b>Step 2</b> — 自动发现爆点 + 生成 LinkedIn/YouTube 内容
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 运行数据采集", type="primary", use_container_width=True):
            with st.spinner("正在采集 8 家公司数据（约 3-5 分钟）..."):
                result = subprocess.run(
                    [sys.executable, 'scripts/monitor.py'],
                    cwd=str(BASE_DIR), capture_output=True, text=True, timeout=600
                )
            if result.returncode == 0:
                st.success("✅ 数据采集完成！")
                with st.expander("查看详细输出"):
                    st.code(result.stdout[-3000:])
            else:
                st.error(f"❌ 出错: {result.stderr[-500:]}")

        if st.button("📝 生成本周内容", use_container_width=True):
            with st.spinner("正在生成内容..."):
                result = subprocess.run(
                    [sys.executable, 'scripts/content_pipeline.py'],
                    cwd=str(BASE_DIR), capture_output=True, text=True, timeout=120
                )
            if result.returncode == 0:
                st.success("✅ 内容生成完成！切换到「内容工作台」查看。")
                with st.expander("查看输出"):
                    st.code(result.stdout[-2000:])
            else:
                st.error(f"❌ 出错: {result.stderr[-500:]}")

        st.markdown("---")
        if st.button("🚀 一键全流程（采集 + 生成）", use_container_width=True):
            progress = st.progress(0, text="准备中...")
            with st.spinner("Step 1/2: 数据采集..."):
                r1 = subprocess.run([sys.executable, 'scripts/monitor.py'],
                    cwd=str(BASE_DIR), capture_output=True, text=True, timeout=600)
            progress.progress(60, text="Step 2/2: 内容生成...")
            with st.spinner("Step 2/2: 生成内容..."):
                r2 = subprocess.run([sys.executable, 'scripts/content_pipeline.py'],
                    cwd=str(BASE_DIR), capture_output=True, text=True, timeout=120)
            progress.progress(100, text="完成!")
            if r1.returncode == 0 and r2.returncode == 0:
                st.success("✅ 全流程完成！请刷新「泡沫仪表盘」和「内容工作台」查看最新结果。")
            else:
                st.error("部分步骤出错，请检查日志。")

    with col_cfg:
        st.subheader("监测配置")
        config_path = BASE_DIR / 'config.json'
        if config_path.exists():
            config = json.loads(config_path.read_text())
            for key, cfg in config.get('companies', {}).items():
                ats = cfg.get('ats', 'unknown')
                ats_colors = {'greenhouse': '#22c55e', 'ashby': '#3b82f6',
                             'lever': '#f97316', 'bytedance': '#a855f7'}
                ats_col = ats_colors.get(ats, '#9ca3af')
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:8px;
                            padding:10px 14px;margin:4px 0;display:flex;justify-content:space-between">
                    <span style="color:#e4e4e7;font-weight:600">{cfg.get('name',key)}</span>
                    <span style="color:{ats_col};font-size:.8em;background:#2a2d3a;
                                padding:2px 8px;border-radius:4px">{ats}</span>
                </div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("数据资产")
    snap_files    = sorted(SNAPSHOTS_DIR.glob('*.json'))
    report_files  = sorted(REPORTS_DIR.glob('*.md'))
    content_files = sorted(CONTENT_DIR.glob('*/linkedin_post.md'))

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("快照期数", f"{len(snap_files)} 期")
    a2.metric("周报文件", f"{len(report_files)} 份")
    a3.metric("已生成内容", f"{len(content_files)} 期")
    a4.metric("数据总大小",
              f"{sum(f.stat().st_size for f in SNAPSHOTS_DIR.glob('*.json'))/1024:.0f} KB")

    if snap_files:
        with st.expander("快照文件列表"):
            for f in reversed(snap_files):
                snap = json.loads(f.read_text())
                total = sum(c.get('total',0) for c in snap.get('companies',{}).values())
                st.markdown(f"📄 `{f.name}` — {total:,} 岗位 ({f.stat().st_size/1024:.1f}KB)")
