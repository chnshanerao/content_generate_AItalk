#!/usr/bin/env python3
"""图表生成器 — 自动生成泡沫仪表盘、对比图、趋势图（暗色主题 PNG）"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'

# Dark theme colors matching 知识图谱.html
COLORS = {
    'bg': '#0f1117', 'card': '#1a1d27', 'border': '#2a2d3a',
    'text': '#e4e4e7', 'muted': '#9ca3af',
    'accent': '#6366f1', 'green': '#22c55e', 'yellow': '#eab308',
    'red': '#ef4444', 'orange': '#f97316', 'blue': '#3b82f6', 'purple': '#a855f7',
    'bars': ['#6366f1', '#3b82f6', '#22c55e', '#eab308', '#f97316', '#ef4444', '#a855f7', '#06b6d4'],
}

def setup_style():
    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'],
        'axes.facecolor': COLORS['card'],
        'axes.edgecolor': COLORS['border'],
        'axes.labelcolor': COLORS['text'],
        'text.color': COLORS['text'],
        'xtick.color': COLORS['muted'],
        'ytick.color': COLORS['muted'],
        'grid.color': COLORS['border'],
        'grid.alpha': 0.3,
        'font.size': 11,
    })

def bubble_color(score):
    if score <= 2: return COLORS['green']
    if score <= 5: return COLORS['yellow']
    if score <= 8: return COLORS['orange']
    return COLORS['red']

def generate_dashboard(snapshot, prev_snapshot, output_path):
    """泡沫仪表盘 — 8 家公司的岗位数 + 泡沫分数"""
    setup_style()
    companies = snapshot.get('companies', {})
    if not companies:
        return

    sorted_companies = sorted(companies.items(), key=lambda x: -x[1].get('total', 0))
    names = [k.upper() for k, _ in sorted_companies]
    totals = [v.get('total', 0) for _, v in sorted_companies]

    # Calculate bubble scores
    from story_detector import load_snapshots
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    prev_companies = (prev_snapshot or {}).get('companies', {})
    deltas = []
    bar_colors = []
    for key, curr in sorted_companies:
        prev = prev_companies.get(key, {})
        pt = prev.get('total', 0)
        d = curr.get('total', 0) - pt if pt > 0 else 0
        deltas.append(d)
        if d > 0: bar_colors.append(COLORS['green'])
        elif d < 0: bar_colors.append(COLORS['red'])
        else: bar_colors.append(COLORS['muted'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={'width_ratios': [3, 2]})

    # Left: Job counts
    bars = ax1.barh(names[::-1], totals[::-1], color=COLORS['bars'][:len(names)][::-1], height=0.6)
    ax1.set_xlabel('Job Postings')
    ax1.set_title(f'AI Company Job Postings — {snapshot.get("date","")}', fontsize=14, fontweight='bold', pad=15)
    for bar, total in zip(bars, totals[::-1]):
        ax1.text(bar.get_width() + max(totals)*0.01, bar.get_y() + bar.get_height()/2,
                f'{total:,}', va='center', fontsize=10, color=COLORS['text'])
    ax1.set_xlim(0, max(totals) * 1.15)
    ax1.grid(axis='x', alpha=0.2)

    # Right: Week-over-week changes
    colors_rev = bar_colors[::-1]
    ax2.barh(names[::-1], deltas[::-1], color=colors_rev, height=0.6)
    ax2.set_xlabel('Week-over-Week Change')
    ax2.set_title('WoW Change', fontsize=14, fontweight='bold', pad=15)
    ax2.axvline(x=0, color=COLORS['muted'], linewidth=0.5)
    for i, (d, name) in enumerate(zip(deltas[::-1], names[::-1])):
        ax2.text(d + (1 if d >= 0 else -1), i, f'{d:+d}' if d != 0 else '0',
                va='center', ha='left' if d >= 0 else 'right', fontsize=9, color=COLORS['text'])
    ax2.grid(axis='x', alpha=0.2)

    plt.tight_layout(pad=2)
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print(f"  Dashboard chart: {output_path}")

def generate_comparison(snapshot, company_a, company_b, output_path):
    """对比图 — 两家公司的 GTM vs R&D 比率对比"""
    setup_style()
    ca = snapshot.get('companies', {}).get(company_a, {})
    cb = snapshot.get('companies', {}).get(company_b, {})

    if not ca or not cb:
        return

    categories = ['Total Jobs', 'GTM %', 'R&D %', 'Senior %', 'Manager %']
    vals_a = [ca.get('total',0)/100, ca.get('gtm_ratio',0), ca.get('research_ratio',0),
              ca.get('senior_pct',0), ca.get('manager_pct',0)]
    vals_b = [cb.get('total',0)/100, cb.get('gtm_ratio',0), cb.get('research_ratio',0),
              cb.get('senior_pct',0), cb.get('manager_pct',0)]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(categories))
    w = 0.35
    ax.bar([i - w/2 for i in x], vals_a, w, label=company_a.upper(), color=COLORS['accent'], alpha=0.85)
    ax.bar([i + w/2 for i in x], vals_b, w, label=company_b.upper(), color=COLORS['orange'], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(fontsize=12)
    ax.set_title(f'{company_a.upper()} vs {company_b.upper()} — Hiring Profile Comparison',
                fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print(f"  Comparison chart: {output_path}")

def generate_trend(snapshots_data, company_key, output_path):
    """趋势图 — 某公司岗位数的时序变化（需要 3+ 周数据）"""
    setup_style()
    dates = []
    totals = []
    gtm_ratios = []

    for snap in snapshots_data:
        d = snap.get('date', '')
        comp = snap.get('companies', {}).get(company_key, {})
        if comp.get('total', 0) > 0:
            dates.append(d[5:])  # MM-DD
            totals.append(comp['total'])
            gtm_ratios.append(comp.get('gtm_ratio', 0))

    if len(dates) < 2:
        print(f"  Trend chart skipped (need 2+ data points, have {len(dates)})")
        return

    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.plot(dates, totals, 'o-', color=COLORS['accent'], linewidth=2, markersize=8, label='Total Jobs')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Total Jobs', color=COLORS['accent'])
    ax1.tick_params(axis='y', labelcolor=COLORS['accent'])

    ax2 = ax1.twinx()
    ax2.plot(dates, gtm_ratios, 's--', color=COLORS['orange'], linewidth=2, markersize=6, label='GTM %')
    ax2.set_ylabel('GTM Ratio %', color=COLORS['orange'])
    ax2.tick_params(axis='y', labelcolor=COLORS['orange'])

    ax1.set_title(f'{company_key.upper()} — Job Trend', fontsize=14, fontweight='bold', pad=15)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    ax1.grid(axis='y', alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    plt.close()
    print(f"  Trend chart: {output_path}")

def run(snapshot, prev_snapshot, stories, output_dir):
    output_dir = Path(output_dir) / 'charts'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dashboard
    generate_dashboard(snapshot, prev_snapshot, output_dir / 'bubble_dashboard.png')

    # 2. Comparison — pick the top story's companies
    if stories:
        top = stories[0]
        company = top.get('company', '')
        if ' vs ' in company:
            a, b = company.split(' vs ')
            generate_comparison(snapshot, a.strip(), b.strip(), output_dir / 'company_comparison.png')
        elif company in snapshot.get('companies', {}):
            ref = 'openai' if company != 'openai' else 'anthropic'
            generate_comparison(snapshot, company, ref, output_dir / 'company_comparison.png')

    # 3. Trend — load all snapshots
    snaps = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if len(snaps) >= 2:
        all_snaps = [json.loads(s.read_text()) for s in snaps]
        biggest = max(snapshot.get('companies', {}).items(), key=lambda x: x[1].get('total', 0))
        generate_trend(all_snaps, biggest[0], output_dir / 'highlight_trend.png')

if __name__ == '__main__':
    snaps = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if snaps:
        current = json.loads(snaps[-1].read_text())
        previous = json.loads(snaps[-2].read_text()) if len(snaps) >= 2 else None
        run(current, previous, [], Path(BASE_DIR / 'content_output' / 'test'))
