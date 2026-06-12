#!/usr/bin/env python3
"""AI 泡沫探测器 v2.0 — 招聘 + GitHub + 论文 + 裁员 + 言行一致性"""

import json, time, re, sys, requests, urllib.parse
from pathlib import Path
from datetime import datetime, date
from collections import Counter
from html.parser import HTMLParser

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / 'config.json'
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'
REPORTS_DIR = BASE_DIR / 'reports' / 'weekly'
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return ' '.join(self.text)

def html_to_text(s):
    if not s: return ''
    p = HTMLTextExtractor()
    try: p.feed(str(s)); return p.get_text()
    except: return re.sub(r'<[^>]+>', ' ', str(s))

# =====================================================================
# MODULE 1: JOB SCRAPERS (unchanged from v1)
# =====================================================================

def scrape_greenhouse(slug):
    r = requests.get(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true',
                     headers={'Accept': 'application/json'}, timeout=30)
    r.raise_for_status()
    return [{'title': j.get('title',''),
             'department': ', '.join(d.get('name','') for d in j.get('departments',[])),
             'location': ', '.join(o.get('name','') for o in j.get('offices',[])),
             'description': html_to_text(j.get('content',''))}
            for j in r.json().get('jobs',[])]

def scrape_ashby(slug):
    r = requests.get(f'https://jobs.ashbyhq.com/{slug}',
                     headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                              'Accept':'text/html'}, timeout=30)
    r.raise_for_status()
    html = r.text
    idx = html.find('"jobPostings":[')
    if idx < 0: return []
    start = idx + len('"jobPostings":')
    bc = 0; end = start
    for i in range(start, min(start+10_000_000, len(html))):
        if html[i] == '[': bc += 1
        elif html[i] == ']': bc -= 1
        if bc == 0: end = i+1; break
    return [{'title': j.get('title',''), 'department': j.get('departmentName',''),
             'location': j.get('locationName',''),
             'description': html_to_text(j.get('descriptionPlain','') or '')}
            for j in json.loads(html[start:end])]

def scrape_lever(slug):
    r = requests.get(f'https://api.lever.co/v0/postings/{slug}?mode=json',
                     headers={'Accept':'application/json'}, timeout=30)
    r.raise_for_status()
    raw = r.json()
    if not isinstance(raw, list): return []
    return [{'title': j.get('text',''),
             'department': j.get('categories',{}).get('department','') or j.get('categories',{}).get('team',''),
             'location': j.get('categories',{}).get('location',''),
             'description': j.get('descriptionPlain','')}
            for j in raw]

def scrape_bytedance(keyword='AI'):
    HEADERS = {
        'Content-Type':'application/json;charset=UTF-8',
        'Accept':'application/json, text/plain, */*',
        'website-path':'society','portal-channel':'office','portal-platform':'pc',
        'env':'undefined','atsx-portal-from':'career',
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer':'https://jobs.bytedance.com/experienced/position',
        'Origin':'https://jobs.bytedance.com',
    }
    URL = 'https://jobs.bytedance.com/api/v1/search/job/posts'
    all_jobs, offset, seen = [], 0, set()
    while True:
        try:
            r = requests.post(URL, headers=HEADERS, json={'keyword':keyword,'limit':100,'offset':offset,'portal_type':2}, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get('code') != 0: break
            batch = data['data']['job_post_list']
            total = data['data']['count']
            for j in batch:
                jid = j.get('id','')
                if jid not in seen:
                    seen.add(jid)
                    all_jobs.append({
                        'title': j.get('title',''),
                        'department': (j.get('job_category') or {}).get('name',''),
                        'location': ', '.join(c.get('name','') for c in (j.get('city_list') or [])),
                        'description': (j.get('description','') or '')[:200],
                    })
            if not batch or len(batch) < 100 or len(all_jobs) >= total: break
            offset += 100; time.sleep(0.3)
        except Exception as e:
            print(f"    ByteDance error at offset {offset}: {e}"); break
    return all_jobs

SCRAPERS = {'greenhouse': scrape_greenhouse, 'ashby': scrape_ashby,
            'lever': scrape_lever, 'bytedance': lambda slug: scrape_bytedance('AI')}

# =====================================================================
# MODULE 2: GITHUB ACTIVITY
# =====================================================================

GITHUB_ORGS = {
    'openai': 'openai', 'anthropic': 'anthropics', 'deepmind': 'google-deepmind',
    'bytedance': None, 'xai': 'xai-org', 'mistral': 'mistralai',
    'stability': 'stability-ai', 'cohere': 'cohere-ai', 'meta': 'meta-llama',
}

def fetch_github(company_key):
    org = GITHUB_ORGS.get(company_key)
    if not org:
        return {'org': None, 'public_repos': 0, 'total_stars': 0, 'top_repos': [], 'recent_commits_4w': 0}
    try:
        r = requests.get(f'https://api.github.com/orgs/{org}/repos?sort=stars&per_page=10',
                        headers={'Accept':'application/vnd.github.v3+json'}, timeout=15)
        if r.status_code != 200:
            return {'org': org, 'error': f'HTTP {r.status_code}'}
        repos = r.json()
        if not isinstance(repos, list):
            return {'org': org, 'error': str(repos)[:100]}

        total_stars = sum(r.get('stargazers_count',0) for r in repos)
        top_repos = [{'name': r['name'], 'stars': r.get('stargazers_count',0),
                      'updated': r.get('updated_at','')[:10],
                      'language': r.get('language','')}
                     for r in repos[:5]]

        # Get commit activity for top repo
        recent_commits = 0
        if repos:
            top_repo = repos[0]['full_name']
            try:
                cr = requests.get(f'https://api.github.com/repos/{top_repo}/stats/commit_activity',
                                 headers={'Accept':'application/vnd.github.v3+json'}, timeout=10)
                if cr.status_code == 200:
                    weeks = cr.json()
                    if isinstance(weeks, list) and len(weeks) >= 4:
                        recent_commits = sum(w.get('total',0) for w in weeks[-4:])
            except: pass

        return {'org': org, 'public_repos': len(repos), 'total_stars': total_stars,
                'top_repos': top_repos, 'recent_commits_4w': recent_commits}
    except Exception as e:
        return {'org': org, 'error': str(e)}

# =====================================================================
# MODULE 3: ARXIV PAPERS
# =====================================================================

ARXIV_QUERIES = {
    'openai': 'au:OpenAI OR ti:GPT-5 OR ti:ChatGPT',
    'anthropic': 'au:Anthropic OR ti:Claude OR ti:Constitutional+AI',
    'deepmind': 'au:DeepMind OR ti:Gemini+model OR ti:AlphaFold',
    'bytedance': 'au:ByteDance OR ti:doubao OR au:Seed',
    'xai': 'au:xAI OR ti:Grok+model',
    'mistral': 'au:Mistral+AI OR ti:Mistral+model',
    'stability': 'au:Stability+AI OR ti:Stable+Diffusion',
    'cohere': 'au:Cohere OR ti:Command+R',
    'meta': 'au:Meta+AI OR ti:LLaMA OR ti:Llama+model',
}

def fetch_arxiv(company_key):
    query = ARXIV_QUERIES.get(company_key, '')
    if not query:
        return {'total_recent': 0, 'papers': []}
    try:
        encoded = urllib.parse.quote(query)
        url = f'http://export.arxiv.org/api/query?search_query={encoded}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending'
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        xml = r.text

        total_match = re.search(r'<opensearch:totalResults[^>]*>(\d+)</opensearch:totalResults>', xml)
        total = int(total_match.group(1)) if total_match else 0

        papers = []
        entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
        for entry in entries[:5]:
            title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            published = re.search(r'<published>(.*?)</published>', entry)
            papers.append({
                'title': title.group(1).strip().replace('\n',' ') if title else '',
                'date': published.group(1)[:10] if published else '',
            })

        return {'total_recent': total, 'papers': papers}
    except Exception as e:
        return {'total_recent': 0, 'error': str(e)}

# =====================================================================
# MODULE 4: LAYOFF DETECTION (via web search keywords in job data)
# =====================================================================

LAYOFF_SIGNALS_IN_JOBS = {
    'restructuring': ['restructur', 'reorg', '重组'],
    'cost_cutting': ['cost optim', 'efficiency', '降本增效'],
    'hiring_freeze_proxy': [],
}

def detect_layoff_signals(company_key, current, previous):
    signals = []
    if not previous or previous.get('total',0) == 0:
        return signals

    curr_total = current.get('total', 0)
    prev_total = previous.get('total', 0)
    wow = (curr_total - prev_total) / prev_total * 100 if prev_total else 0

    if wow < -10:
        signals.append(f"岗位暴跌 {wow:.1f}%（可能裁员或招聘冻结）")
    elif wow < -5:
        signals.append(f"岗位显著下降 {wow:.1f}%")

    # Senior/Manager ratio drop = layoff precursor
    curr_mgr = current.get('manager_pct', 0)
    prev_mgr = previous.get('manager_pct', 0)
    if prev_mgr > 0 and curr_mgr < prev_mgr - 3:
        signals.append(f"Manager占比下降 {prev_mgr:.1f}%→{curr_mgr:.1f}%（管理层精简信号）")

    # GTM freeze while R&D continues = revenue pressure
    curr_gtm = current.get('gtm_ratio', 0)
    prev_gtm = previous.get('gtm_ratio', 0)
    curr_rd = current.get('research_ratio', 0)
    prev_rd = previous.get('research_ratio', 0)
    if prev_gtm > 0 and curr_gtm < prev_gtm - 5 and curr_rd >= prev_rd - 2:
        signals.append(f"GTM冻结但R&D不变（收入不达预期信号）")

    return signals

# =====================================================================
# MODULE 5: CONSISTENCY CHECK (言行一致性)
# =====================================================================

CEO_CLAIMS = {
    'openai': {
        'narrative': 'Sam Altman: "算力是未来最珍贵的商品，AGI十年内到来"',
        'checks': [
            ('GTM是否是最大部门？', lambda d: d.get('gtm_ratio',0) > 20,
             '是 → 商业化确实是第一优先级', '否 → 嘴上说AGI，实际在卖产品'),
            ('研发占比是否 >30%？', lambda d: d.get('research_ratio',0) > 30,
             '是 → 研发投入匹配AGI叙事', '否 → 研发占比低于叙事预期'),
        ]
    },
    'anthropic': {
        'narrative': 'Dario Amodei: "安全是我们的核心，Scaling Laws仍在生效"',
        'checks': [
            ('Safety相关岗位是否 >10%？', lambda d: True, '需要部门数据验证', ''),
            ('研发占比是否 >25%？', lambda d: d.get('research_ratio',0) > 25,
             '是 → Scaling投入匹配叙事', '否 → 研发占比低于安全优先的叙事'),
        ]
    },
    'deepmind': {
        'narrative': 'Demis Hassabis: "纯研究导向，商业化由Google Cloud负责"',
        'checks': [
            ('GTM占比是否 ≈0%？', lambda d: d.get('gtm_ratio',0) < 3,
             '是 → 确实是纯研究院', '否 → 开始自建商业化团队（叙事偏移）'),
            ('研发占比是否 >40%？', lambda d: d.get('research_ratio',0) > 40,
             '是 → 研究优先一致', '否 → 研发占比下降'),
        ]
    },
    'stability': {
        'narrative': '曾宣称"开源生成式AI的领导者"',
        'checks': [
            ('总岗位是否 >50？', lambda d: d.get('total',0) > 50,
             '是 → 仍在扩张', '否 → 严重萎缩（泡沫破裂典型案例）'),
        ]
    },
}

def check_consistency(company_key, analysis):
    claim = CEO_CLAIMS.get(company_key)
    if not claim:
        return None
    results = {'narrative': claim['narrative'], 'checks': []}
    for desc, check_fn, pass_msg, fail_msg in claim['checks']:
        passed = check_fn(analysis)
        results['checks'].append({
            'check': desc,
            'passed': passed,
            'message': pass_msg if passed else fail_msg,
        })
    return results

# =====================================================================
# MODULE 6: ENHANCED ANALYSIS
# =====================================================================

GTM_KW = ['sales','go to market','gtm','marketing','revenue','partnership',
           'account executive','customer success','solutions engineer','销售','商务','GTM','市场','商业化']
RD_KW = ['research','algorithm','ml','ai research','frontier','scaling','training','inference','safety',
          '算法','研究','研发','模型']
SR_KW = ['senior','staff','principal','lead','head','director','vp','高级','资深','专家','负责人']
MGR_KW = ['manager','director','经理','总监']

def analyze_company(key, jobs):
    total = len(jobs)
    if total == 0:
        return {'total':0,'gtm':0,'research':0,'gtm_ratio':0,'research_ratio':0,
                'senior_pct':0,'manager_pct':0,'by_department':{},'by_location':{}}
    gtm = sum(1 for j in jobs if any(k in f"{j['title']} {j['department']}".lower() for k in GTM_KW))
    research = sum(1 for j in jobs if any(k in f"{j['title']} {j['department']}".lower() for k in RD_KW))
    senior = sum(1 for j in jobs if any(k in j['title'].lower() for k in SR_KW))
    manager = sum(1 for j in jobs if any(k in j['title'].lower() for k in MGR_KW))
    dept_c = Counter(j['department'] for j in jobs if j['department'])
    loc_c = Counter(j['location'] for j in jobs if j['location'])
    return {
        'total': total, 'gtm': gtm, 'research': research,
        'gtm_ratio': round(gtm/total*100,1), 'research_ratio': round(research/total*100,1),
        'senior_pct': round(senior/total*100,1), 'manager_pct': round(manager/total*100,1),
        'by_department': dict(dept_c.most_common(10)), 'by_location': dict(loc_c.most_common(10)),
    }

def compute_bubble_score(current, previous, layoff_signals=None, github=None):
    if not previous or previous.get('total',0) == 0:
        return 0, []
    score, signals = 0, []
    prev_total, curr_total = previous['total'], current.get('total',0)
    wow = (curr_total - prev_total) / prev_total * 100 if prev_total else 0

    if wow < -10: score += 3; signals.append(f"岗位暴跌 {wow:+.1f}%")
    elif wow < -5: score += 2; signals.append(f"岗位下降 {wow:+.1f}%")
    elif wow > 5: score -= 1; signals.append(f"岗位增长 {wow:+.1f}%")

    if current.get('gtm_ratio',0) < previous.get('gtm_ratio',0) - 3:
        score += 3; signals.append("GTM占比下降 >3pp")
    if current.get('manager_pct',0) < previous.get('manager_pct',0) - 5:
        score += 1; signals.append("Manager占比下降 >5pp")

    new_locs = set(current.get('by_location',{}).keys()) - set(previous.get('by_location',{}).keys())
    lost_locs = set(previous.get('by_location',{}).keys()) - set(current.get('by_location',{}).keys())
    if new_locs: score -= 1; signals.append(f"新增城市: {', '.join(list(new_locs)[:3])}")
    if lost_locs: score += 1; signals.append(f"撤出城市: {', '.join(list(lost_locs)[:3])}")

    # v2: GitHub signals
    if github and not github.get('error'):
        if github.get('recent_commits_4w', 0) == 0 and github.get('total_stars',0) > 1000:
            score += 1; signals.append("GitHub 近4周零commit（开源投入停滞）")

    # v2: Layoff signals
    if layoff_signals:
        score += len(layoff_signals)
        signals.extend(layoff_signals)

    return max(score, 0), signals

def bubble_emoji(score):
    if score <= 2: return '🟢'
    if score <= 5: return '🟡'
    if score <= 8: return '🟠'
    return '🔴'

# =====================================================================
# MAIN
# =====================================================================

def run(today_str=None):
    config = json.loads(CONFIG_PATH.read_text())
    today = today_str or date.today().isoformat()

    snapshots = sorted(SNAPSHOTS_DIR.glob('*.json'))
    prev_snapshot = json.loads(snapshots[-1].read_text()) if snapshots else None

    print(f"=== AI 泡沫探测器 v2.0 — {today} ===\n")
    snapshot = {'date': today, 'version': '2.0', 'companies': {}, 'github': {}, 'arxiv': {}, 'consistency': {}}

    # Phase 1: Scrape jobs
    print("── Phase 1: 招聘数据 ──")
    for key, cfg in config['companies'].items():
        ats, slug, name = cfg['ats'], cfg['slug'], cfg['name']
        print(f"  {name} ({ats})...", end=' ', flush=True)
        try:
            jobs = SCRAPERS[ats](slug)
            analysis = analyze_company(key, jobs)
            snapshot['companies'][key] = analysis
            print(f"✓ {analysis['total']} 岗 (GTM:{analysis['gtm']}, R&D:{analysis['research']})")
        except Exception as e:
            print(f"✗ {e}")
            snapshot['companies'][key] = {'total':0, 'error':str(e)}

    # Phase 2: GitHub activity
    print("\n── Phase 2: GitHub 活跃度 ──")
    for key in config['companies']:
        name = config['companies'][key]['name']
        print(f"  {name}...", end=' ', flush=True)
        gh = fetch_github(key)
        snapshot['github'][key] = gh
        if gh.get('error'):
            print(f"✗ {gh['error'][:50]}")
        elif gh.get('org') is None:
            print("- (无公开 GitHub org)")
        else:
            print(f"✓ {gh['total_stars']}⭐ {gh['public_repos']} repos, {gh['recent_commits_4w']} commits/4w")
        time.sleep(0.5)

    # Phase 3: arXiv papers
    print("\n── Phase 3: arXiv 论文 ──")
    for key in config['companies']:
        name = config['companies'][key]['name']
        print(f"  {name}...", end=' ', flush=True)
        arxiv = fetch_arxiv(key)
        snapshot['arxiv'][key] = arxiv
        if arxiv.get('error'):
            print(f"✗ {arxiv['error'][:50]}")
        else:
            papers = arxiv.get('papers', [])
            latest = papers[0]['title'][:50] if papers else 'N/A'
            print(f"✓ {arxiv['total_recent']} 篇 | 最新: {latest}...")
        time.sleep(1)

    # Phase 4: Layoff signals + Bubble score
    print("\n── Phase 4: 泡沫指数计算 ──")
    company_scores = {}
    for key, curr in snapshot['companies'].items():
        prev = (prev_snapshot or {}).get('companies',{}).get(key,{})
        layoff_sigs = detect_layoff_signals(key, curr, prev)
        gh = snapshot['github'].get(key, {})
        sc, sigs = compute_bubble_score(curr, prev, layoff_sigs, gh)
        company_scores[key] = (sc, sigs)
        name = config['companies'][key]['name']
        print(f"  {name}: {bubble_emoji(sc)} {sc}/10" + (f" ⚠ {'; '.join(sigs)}" if sigs else ""))

    # Phase 5: Consistency check
    print("\n── Phase 5: 言行一致性检测 ──")
    for key, curr in snapshot['companies'].items():
        cc = check_consistency(key, curr)
        if cc:
            snapshot['consistency'][key] = cc
            name = config['companies'][key]['name']
            print(f"  {name} — {cc['narrative'][:40]}...")
            for c in cc['checks']:
                icon = '✅' if c['passed'] else '❌'
                print(f"    {icon} {c['check']} → {c['message']}")

    # Save snapshot
    snap_path = SNAPSHOTS_DIR / f'{today}.json'
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"\n快照已保存: {snap_path}")

    # Generate report
    report = generate_report(snapshot, prev_snapshot, config, company_scores)
    report_path = REPORTS_DIR / f'{today}.md'
    report_path.write_text(report)
    print(f"报告已保存: {report_path}")

    # Dingtalk summary
    summary = generate_dingtalk(snapshot, prev_snapshot, company_scores, config)
    print(f"\n{'='*60}")
    print(summary)
    print(f"{'='*60}")
    return snapshot, report, summary

# =====================================================================
# REPORT GENERATION
# =====================================================================

def generate_report(snapshot, prev_snapshot, config, company_scores):
    today = snapshot['date']
    L = [f"# AI 泡沫探测器周报 v2.0 — {today}\n"]

    total_jobs = sum(c.get('total',0) for c in snapshot['companies'].values())
    prev_total = sum(c.get('total',0) for c in (prev_snapshot or {}).get('companies',{}).values()) if prev_snapshot else 0
    wow = ((total_jobs-prev_total)/prev_total*100) if prev_total else 0
    scores = [s for s,_ in company_scores.values()]
    avg = sum(scores)/max(len(scores),1)

    L.append("## 行业总览\n")
    L.append(f"- 监测公司: {len(snapshot['companies'])} 家")
    L.append(f"- 总岗位数: {total_jobs:,}" + (f" (上期 {prev_total:,}, {wow:+.1f}%)" if prev_total else " (首次基线)"))
    L.append(f"- 行业泡沫指数: {bubble_emoji(avg)} {avg:.1f}/10\n")

    # Company dashboard
    L.append("## 各公司仪表盘\n")
    L.append("| 公司 | 岗位数 | 变化 | GTM% | R&D% | GitHub⭐ | 论文数 | 泡沫分 | 状态 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for key, curr in sorted(snapshot['companies'].items(), key=lambda x:-x[1].get('total',0)):
        name = config['companies'].get(key,{}).get('name',key)
        total = curr.get('total',0)
        prev = (prev_snapshot or {}).get('companies',{}).get(key,{})
        pt = prev.get('total',0)
        ch = f"{total-pt:+d} ({(total-pt)/pt*100:+.1f}%)" if pt else "基线"
        gh = snapshot['github'].get(key,{})
        stars = gh.get('total_stars',0)
        arxiv = snapshot['arxiv'].get(key,{})
        papers = arxiv.get('total_recent',0)
        sc,_ = company_scores.get(key,(0,[]))
        L.append(f"| {name} | {total:,} | {ch} | {curr.get('gtm_ratio',0):.1f}% | {curr.get('research_ratio',0):.1f}% | {stars:,} | {papers} | {sc} | {bubble_emoji(sc)} |")

    # Anomaly signals
    L.append("\n## 异常信号\n")
    has = False
    for key,(sc,sigs) in company_scores.items():
        if sigs:
            name = config['companies'].get(key,{}).get('name',key)
            for s in sigs: L.append(f"- **{name}**: {s}"); has=True
    if not has: L.append("- 本期无异常信号")

    # GitHub insights
    L.append("\n## GitHub 开源活跃度\n")
    L.append("| 公司 | Org | 总⭐ | Repos | 近4周Commits | Top Repo |")
    L.append("|---|---|---|---|---|---|")
    for key in snapshot['companies']:
        name = config['companies'].get(key,{}).get('name',key)
        gh = snapshot['github'].get(key,{})
        org = gh.get('org','N/A') or 'N/A'
        stars = gh.get('total_stars',0)
        repos = gh.get('public_repos',0)
        commits = gh.get('recent_commits_4w',0)
        top = gh.get('top_repos',[{}])[0].get('name','') if gh.get('top_repos') else ''
        L.append(f"| {name} | {org} | {stars:,} | {repos} | {commits} | {top} |")

    # arXiv insights
    L.append("\n## 最新论文\n")
    for key in snapshot['companies']:
        name = config['companies'].get(key,{}).get('name',key)
        arxiv = snapshot['arxiv'].get(key,{})
        papers = arxiv.get('papers',[])
        if papers:
            L.append(f"**{name}** ({arxiv.get('total_recent',0)} 篇):")
            for p in papers[:3]:
                L.append(f"- [{p.get('date','')}] {p.get('title','')}")
            L.append("")

    # Consistency check
    L.append("\n## 言行一致性检测\n")
    for key, cc in snapshot.get('consistency',{}).items():
        if cc:
            name = config['companies'].get(key,{}).get('name',key)
            L.append(f"**{name}** — {cc['narrative']}")
            for c in cc['checks']:
                icon = '✅' if c['passed'] else '❌'
                L.append(f"- {icon} {c['check']} → {c['message']}")
            L.append("")

    L.append(f"\n---\n*Generated by AI Bubble Monitor v2.0 — 招聘+GitHub+论文+裁员+言行一致性*")
    return '\n'.join(L)

def generate_dingtalk(snapshot, prev_snapshot, company_scores, config):
    today = snapshot['date']
    total = sum(c.get('total',0) for c in snapshot['companies'].values())
    prev_total = sum(c.get('total',0) for c in (prev_snapshot or {}).get('companies',{}).values()) if prev_snapshot else 0
    scores = [s for s,_ in company_scores.values()]
    avg = sum(scores)/max(len(scores),1)

    L = [f"🔍 AI 泡沫探测器 v2.0 — {today}\n"]
    if prev_total:
        L.append(f"📊 总岗位: {total:,} (上期 {prev_total:,}, {(total-prev_total)/prev_total*100:+.1f}%)")
    else:
        L.append(f"📊 总岗位: {total:,} (首次基线)")
    L.append(f"🎯 泡沫指数: {bubble_emoji(avg)} {avg:.1f}/10\n")

    L.append("📈 各公司:")
    for key,curr in sorted(snapshot['companies'].items(), key=lambda x:-x[1].get('total',0)):
        name = config['companies'].get(key,{}).get('name',key)
        t = curr.get('total',0)
        prev = (prev_snapshot or {}).get('companies',{}).get(key,{})
        pt = prev.get('total',0)
        sc,_ = company_scores.get(key,(0,[]))
        if pt:
            L.append(f"  {name}: {t} ({t-pt:+d}) {bubble_emoji(sc)}")
        else:
            L.append(f"  {name}: {t} (新) {bubble_emoji(sc)}")

    # Highlight anomalies
    anomalies = []
    for key,(sc,sigs) in company_scores.items():
        if sigs:
            name = config['companies'].get(key,{}).get('name',key)
            anomalies.extend(f"  ⚠ {name}: {s}" for s in sigs)
    if anomalies:
        L.append("\n⚠️ 异常信号:")
        L.extend(anomalies)

    # Consistency highlights
    fails = []
    for key, cc in snapshot.get('consistency',{}).items():
        if cc:
            for c in cc['checks']:
                if not c['passed']:
                    name = config['companies'].get(key,{}).get('name',key)
                    fails.append(f"  ❌ {name}: {c['check']}")
    if fails:
        L.append("\n🔍 言行不一致:")
        L.extend(fails[:5])

    return '\n'.join(L)

if __name__ == '__main__':
    today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    run(today)
