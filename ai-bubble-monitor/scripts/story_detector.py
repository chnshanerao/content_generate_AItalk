#!/usr/bin/env python3
"""爆点发现器 — 从周度 snapshot diff 中找出最有故事性的异常信号"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'

# Cisco 2000 baseline for historical comparison
DOTCOM_BENCHMARKS = {
    'revenue_capex_ratio': 0.17,
    'cisco_ps_ratio': 30,
    'nasdaq_peak_date': '2000-03-10',
}

def load_snapshots():
    snaps = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if len(snaps) < 1:
        return None, None
    current = json.loads(snaps[-1].read_text())
    previous = json.loads(snaps[-2].read_text()) if len(snaps) >= 2 else None
    return current, previous

def detect_facepalm(current, previous, config=None):
    """打脸检测 — CEO 叙事 vs 数据出现矛盾"""
    stories = []
    consistency = current.get('consistency', {})
    prev_consistency = (previous or {}).get('consistency', {})

    NARRATIVES = {
        'openai': {
            'ceo': 'Sam Altman',
            'claim': 'AGI will arrive within a decade — compute is the most precious commodity',
            'claim_cn': 'Sam Altman 说算力是未来最珍贵的商品，AGI 十年内到来',
        },
        'anthropic': {
            'ceo': 'Dario Amodei',
            'claim': 'Safety is our core mission, and Scaling Laws still hold',
            'claim_cn': 'Dario Amodei 说安全是核心，Scaling Laws 仍在生效',
        },
        'deepmind': {
            'ceo': 'Demis Hassabis',
            'claim': 'We are a pure research lab — commercialization is Google Cloud\'s job',
            'claim_cn': 'Demis Hassabis 说 DeepMind 是纯研究院',
        },
        'stability': {
            'ceo': 'Former leadership',
            'claim': 'We are the leader in open-source generative AI',
            'claim_cn': '曾宣称是开源生成式 AI 的领导者',
        },
    }

    for key, cc in consistency.items():
        if not cc:
            continue
        narr = NARRATIVES.get(key, {})
        for check in cc.get('checks', []):
            if not check.get('passed', True):
                prev_cc = prev_consistency.get(key, {})
                was_passing = True
                if prev_cc:
                    for pc in prev_cc.get('checks', []):
                        if pc.get('check') == check.get('check') and not pc.get('passed'):
                            was_passing = False

                stories.append({
                    'detector': 'facepalm',
                    'virality': 9 if was_passing else 7,
                    'company': key,
                    'headline_en': f"{narr.get('ceo','CEO')} says \"{narr.get('claim','...')[:60]}\" — but the data shows: {check['message']}",
                    'headline_cn': f"{narr.get('claim_cn','...')}，但数据显示：{check['message']}",
                    'data_points': [check],
                    'emotion': 'confirmation_bias',
                    'emotion_cn': '确认偏差 — 观众一直怀疑这是营销话术',
                    'is_new': was_passing,
                })
    return stories

def detect_corpse(current, previous, config=None):
    """尸体检测 — 某公司岗位暴跌或趋近于零"""
    stories = []
    for key, curr in current.get('companies', {}).items():
        total = curr.get('total', 0)
        prev = (previous or {}).get('companies', {}).get(key, {})
        prev_total = prev.get('total', 0)

        if total <= 10 and total > 0:
            stories.append({
                'detector': 'corpse',
                'virality': 10,
                'company': key,
                'headline_en': f"{key.upper()} has only {total} job postings left. The AI bubble has its first body.",
                'headline_cn': f"{key.upper()} 只剩 {total} 个岗位了。AI 泡沫已经有尸体了。",
                'data_points': {'current': total, 'previous': prev_total},
                'emotion': 'shock',
                'emotion_cn': '冲击 — "AI 公司居然真的会死"',
                'is_new': prev_total > 10 if prev_total else False,
            })

        if prev_total > 0 and total < prev_total * 0.85:
            wow = (total - prev_total) / prev_total * 100
            stories.append({
                'detector': 'corpse',
                'virality': 8,
                'company': key,
                'headline_en': f"{key.upper()} jobs dropped {wow:.0f}% in one week. Hiring freeze or stealth layoff?",
                'headline_cn': f"{key.upper()} 岗位一周暴跌 {wow:.0f}%，招聘冻结还是隐性裁员？",
                'data_points': {'current': total, 'previous': prev_total, 'wow': wow},
                'emotion': 'anxiety',
                'emotion_cn': '焦虑 — "我投的那家公司是不是也这样？"',
                'is_new': True,
            })
    return stories

def detect_reversal(current, previous, config=None):
    """反转检测 — 某公司从扩张突然转为收缩（或反之）"""
    stories = []
    if not previous:
        return stories

    for key, curr in current.get('companies', {}).items():
        prev = previous.get('companies', {}).get(key, {})
        if not prev or prev.get('total', 0) == 0:
            continue

        curr_total = curr.get('total', 0)
        prev_total = prev.get('total', 0)
        curr_gtm = curr.get('gtm_ratio', 0)
        prev_gtm = prev.get('gtm_ratio', 0)

        if curr_gtm < prev_gtm - 5 and curr.get('research_ratio', 0) >= prev.get('research_ratio', 0) - 2:
            stories.append({
                'detector': 'reversal',
                'virality': 8,
                'company': key,
                'headline_en': f"{key.upper()} froze GTM hiring but kept R&D going. Revenue trouble?",
                'headline_cn': f"{key.upper()} GTM 招聘冻结但研发不变 — 收入出问题了？",
                'data_points': {'gtm_prev': prev_gtm, 'gtm_curr': curr_gtm,
                               'rd_prev': prev.get('research_ratio',0), 'rd_curr': curr.get('research_ratio',0)},
                'emotion': 'anxiety',
                'emotion_cn': '焦虑 — 商业化遇阻的信号',
                'is_new': True,
            })
    return stories

def detect_conflict(current, previous, config=None):
    """冲突检测 — 两家竞对在同一维度出现反向变化"""
    stories = []
    if not previous:
        return stories

    companies = list(current.get('companies', {}).keys())
    for i, a in enumerate(companies):
        for b in companies[i+1:]:
            ca = current['companies'].get(a, {})
            cb = current['companies'].get(b, {})
            pa = previous.get('companies', {}).get(a, {})
            pb = previous.get('companies', {}).get(b, {})

            if not pa or not pb or pa.get('total',0) == 0 or pb.get('total',0) == 0:
                continue

            a_delta = (ca.get('total',0) - pa.get('total',0)) / pa['total'] * 100
            b_delta = (cb.get('total',0) - pb.get('total',0)) / pb['total'] * 100

            if (a_delta > 5 and b_delta < -5) or (a_delta < -5 and b_delta > 5):
                grower = a if a_delta > b_delta else b
                shrinker = b if grower == a else a
                g_delta = a_delta if grower == a else b_delta
                s_delta = b_delta if shrinker == b else a_delta

                stories.append({
                    'detector': 'conflict',
                    'virality': 8,
                    'company': f"{grower} vs {shrinker}",
                    'headline_en': f"{grower.upper()} is hiring (+{g_delta:.0f}%) while {shrinker.upper()} is shrinking ({s_delta:.0f}%). Who's right?",
                    'headline_cn': f"{grower.upper()} 在扩招（+{g_delta:.0f}%），{shrinker.upper()} 在收缩（{s_delta:.0f}%）。谁判断对了？",
                    'data_points': {grower: g_delta, shrinker: s_delta},
                    'emotion': 'curiosity',
                    'emotion_cn': '好奇 — 两家做出了相反的判断',
                    'is_new': True,
                })
    return stories

def detect_history_rhyme(current, previous, config=None):
    """历史重演检测 — 当前指标与互联网泡沫某时间点相似"""
    stories = []
    total_jobs = sum(c.get('total', 0) for c in current.get('companies', {}).values())

    ai_revenue_estimate = 1000  # $1000 亿
    ai_capex_estimate = 5600    # $5600 亿
    current_ratio = ai_revenue_estimate / ai_capex_estimate if ai_capex_estimate else 0

    diff = abs(current_ratio - DOTCOM_BENCHMARKS['revenue_capex_ratio'])
    if diff < 0.05:
        stories.append({
            'detector': 'history_rhyme',
            'virality': 9,
            'company': 'industry',
            'headline_en': f"AI's revenue/capex ratio ({current_ratio:.2f}) is almost identical to the dot-com bubble in 1999 ({DOTCOM_BENCHMARKS['revenue_capex_ratio']}). History doesn't repeat, but it rhymes.",
            'headline_cn': f"AI 行业的收入/投入比（{current_ratio:.2f}）与 1999 年互联网泡沫（{DOTCOM_BENCHMARKS['revenue_capex_ratio']}）几乎一模一样。历史不会重复，但会押韵。",
            'data_points': {'ai_ratio': current_ratio, 'dotcom_ratio': DOTCOM_BENCHMARKS['revenue_capex_ratio']},
            'emotion': 'anxiety',
            'emotion_cn': '焦虑 — "这次真的不一样吗？"',
            'is_new': False,
        })
    return stories

def run(current=None, previous=None):
    if current is None:
        current, previous = load_snapshots()
    if current is None:
        print("No snapshots found")
        return []

    all_stories = []
    for detector in [detect_facepalm, detect_corpse, detect_reversal, detect_conflict, detect_history_rhyme]:
        all_stories.extend(detector(current, previous))

    all_stories.sort(key=lambda x: -x.get('virality', 0))
    return all_stories

if __name__ == '__main__':
    stories = run()
    print(f"\n=== 爆点发现器 — 发现 {len(stories)} 个故事线索 ===\n")
    for i, s in enumerate(stories[:5], 1):
        print(f"[{i}] 传播力: {s['virality']}/10 | {s['detector']} | {s.get('company','')}")
        print(f"    EN: {s['headline_en']}")
        print(f"    CN: {s['headline_cn']}")
        print(f"    情绪: {s['emotion_cn']}")
        print()
