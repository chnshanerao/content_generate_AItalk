---
name: talent-intel
description: "AI 人才情报 — 跨公司招聘数据战略洞察。输入 2-5 家公司名，自动爬取全量岗位，从招聘数据反推各公司的战略方向、商业化阶段、全球化布局、技术押注、GTM密度，输出对比报告。面向 VC/企业战略/猎头。触发词：'对比XX和YY的招聘'、'从招聘数据看XX的战略'、'talent intelligence'、'人才情报'、'招聘战略分析'、'compare hiring between'。"
version: 1.0.0
---

# Talent Intel — AI 人才情报

从招聘数据反推公司战略。输入多家公司名，自动爬取 → 标准化 → 多维度对比 → 输出战略洞察报告。

## When to use

- 投资人想从招聘数据判断目标公司的真实战略方向
- 企业战略部想跟踪竞对的组织扩张和技术布局
- 猎头想理解多家公司的人才需求差异
- 用户说"对比XX和YY的招聘"、"从招聘看XX在干什么"

## Step 1: Multi-company scrape

使用 `job-radar` Skill 的 `scrape_company()` 函数批量爬取。将所有公司的数据统一为标准 schema：

```python
# 标准 schema（所有平台统一转换到这个格式）
STANDARD_SCHEMA = {
    'id': str,
    'title': str,
    'department': str,
    'location': str,
    'description': str,
    'url': str,
    'company': str,       # 新增：公司名
    'source': str,        # ATS平台名
}

# 批量爬取
companies = ["openai", "anthropic", "bytedance"]  # 用户输入
all_data = {}
for company in companies:
    jobs = scrape_company(company)
    for j in jobs:
        j['company'] = company
    all_data[company] = jobs
    print(f"  {company}: {len(jobs)} jobs")
```

## Step 2: Analysis dimensions

以下是 8 个核心分析维度，每个维度都用关键词扫描 + 统计计数实现。

### 2.1 组织规模与商业化阶段

```python
from collections import Counter

# 技术 vs 非技术分类（中英文兼容）
TECH_CATEGORIES = {
    '后端', '前端', '客户端', '研发', '算法', '基础架构', '硬件', '测试', '运维',
    '安全', '机器学习', '大数据', 'DBA',
    'Engineering', 'Research', 'Infrastructure', 'Security', 'Applied AI',
    'Scaling', 'Compute', 'Safety Systems',
}

NON_TECH_CATEGORIES = {
    '运营', '销售', '市场', '产品', '商务', '战略', '设计', '财务', '法务', '人力',
    'Sales', 'Go To Market', 'Marketing', 'Finance', 'People', 'Legal',
    'Communications', 'Data Science', 'Revenue Operations', 'Partnerships',
    'Growth', 'User Operations', 'Product Management',
}

def classify_tech_nontech(job):
    dept = job.get('department', '')
    title = job.get('title', '')
    text = f"{dept} {title}"
    if any(cat.lower() in text.lower() for cat in TECH_CATEGORIES):
        return 'tech'
    if any(cat.lower() in text.lower() for cat in NON_TECH_CATEGORIES):
        return 'non_tech'
    return 'other'

def analyze_maturity(company, jobs):
    tech = sum(1 for j in jobs if classify_tech_nontech(j) == 'tech')
    non_tech = len(jobs) - tech
    ratio = non_tech / len(jobs) * 100 if jobs else 0
    if ratio > 50: stage = "商业化成熟期"
    elif ratio > 35: stage = "商业化加速期"
    else: stage = "技术积累期"
    return {'total': len(jobs), 'tech': tech, 'non_tech': non_tech,
            'non_tech_pct': ratio, 'stage': stage}
```

### 2.2 战略方向信号扫描（15+ 维度）

```python
STRATEGY_DIMENSIONS = {
    'AI Agent':          ['agent', 'agentic', '智能体'],
    'LLM/大模型':         ['LLM', '大模型', 'large language model', 'foundation model'],
    'AI Coding':         ['coding', 'code generation', 'AI编程', '代码生成', 'codex'],
    'AI Safety':         ['safety', 'alignment', 'trust', '安全', '对齐', '可信'],
    'Multimodal':        ['multimodal', 'multi-modal', '多模态'],
    'RAG':               ['RAG', 'retrieval', '检索增强'],
    'Robotics':          ['robotics', 'robot', '机器人', '具身'],
    'Enterprise/ToB':    ['enterprise', 'B2B', 'ToB', '企业', '行业解决'],
    'GTM':               ['GTM', 'go-to-market', 'go to market', '商业化'],
    'International':     ['international', 'global', 'APAC', 'EMEA', '海外', '国际化'],
    'Ads/Monetization':  ['ads', 'advertising', '广告', 'monetization', '变现'],
    'Government':        ['government', 'gov', '政府', 'public sector'],
    'Consumer':          ['consumer', 'user', '用户', '消费'],
    'Search':            ['search', '搜索', 'AI search'],
    'AI for Science':    ['scientific', 'biology', 'AI for science', '科学计算'],
    'Data Labeling':     ['annotation', 'labeling', '标注', 'human data'],
}

def scan_strategy(company, jobs):
    results = {}
    for dim, keywords in STRATEGY_DIMENSIONS.items():
        count = sum(1 for j in jobs
                   if any(kw.lower() in f"{j.get('title','')} {j.get('description','')}".lower()
                         for kw in keywords))
        results[dim] = {'count': count, 'pct': count/len(jobs)*100 if jobs else 0}
    return results
```

### 2.3 GTM/Sales 组织拆解

```python
def analyze_gtm(company, jobs):
    sales_kw = ['sales', '销售', 'account executive', 'AE']
    gtm_kw = ['GTM', 'go to market', 'go-to-market']
    mkt_kw = ['marketing', '市场', '营销']
    se_kw = ['solutions engineer', '解决方案']
    cs_kw = ['customer success', '客户成功']
    partner_kw = ['partner', 'partnership', '渠道']
    
    def count(keywords):
        return sum(1 for j in jobs
                  if any(kw.lower() in f"{j['title']} {j['department']}".lower() for kw in keywords))
    
    return {
        'sales': count(sales_kw),
        'gtm': count(gtm_kw),
        'marketing': count(mkt_kw),
        'solutions_engineer': count(se_kw),
        'customer_success': count(cs_kw),
        'partnerships': count(partner_kw),
        'total_commercial': count(sales_kw + gtm_kw + mkt_kw),
    }
```

### 2.4 全球化布局

```python
def analyze_geography(company, jobs):
    loc_counter = Counter()
    for j in jobs:
        loc = j.get('location', '')
        if loc:
            loc_counter[loc] += 1
    
    # 地区聚合
    regions = {'North America': 0, 'APAC': 0, 'Europe': 0, 'China': 0, 'Other': 0}
    na_kw = ['San Francisco', 'New York', 'Seattle', 'Washington', 'US', 'Remote']
    apac_kw = ['Singapore', 'Tokyo', 'Seoul', 'Sydney', 'India']
    eu_kw = ['London', 'Dublin', 'Paris', 'Munich', 'Zürich', 'Berlin']
    cn_kw = ['北京', '上海', '深圳', '杭州', '成都', '广州']
    
    for loc, cnt in loc_counter.items():
        if any(k in loc for k in cn_kw): regions['China'] += cnt
        elif any(k in loc for k in na_kw): regions['North America'] += cnt
        elif any(k in loc for k in apac_kw): regions['APAC'] += cnt
        elif any(k in loc for k in eu_kw): regions['Europe'] += cnt
        else: regions['Other'] += cnt
    
    sg_count = sum(v for k, v in loc_counter.items() if 'Singapore' in k)
    
    return {'by_location': dict(loc_counter.most_common(15)),
            'by_region': regions, 'singapore': sg_count}
```

### 2.5 技术栈需求

```python
TECH_STACKS = {
    'Python': ['python'],
    'Go': ['golang', ' go '],
    'Rust': ['rust'],
    'C++': ['c++'],
    'PyTorch': ['pytorch'],
    'CUDA/GPU': ['cuda', 'gpu'],
    'Kubernetes': ['kubernetes', 'k8s'],
    'Distributed': ['distributed', '分布式'],
    'Transformer': ['transformer'],
    'RLHF': ['rlhf'],
    'Fine-tuning': ['fine-tun', 'sft', '微调'],
    'Prompt Eng': ['prompt engineering', 'prompt', '提示词'],
}
```

### 2.6 人才画像（职级分布）

```python
def analyze_seniority(company, jobs):
    senior = sum(1 for j in jobs if any(k in j['title'].lower()
                for k in ['senior', 'staff', 'principal', 'lead', 'head', '高级', '资深']))
    manager = sum(1 for j in jobs if any(k in j['title'].lower()
                 for k in ['manager', 'director', '经理', '总监']))
    return {'senior_plus': senior, 'manager_director': manager,
            'senior_pct': senior/len(jobs)*100 if jobs else 0,
            'manager_pct': manager/len(jobs)*100 if jobs else 0}
```

## Step 3: Generate report

```python
def generate_report(all_data):
    """生成 Markdown 战略洞察报告"""
    companies = list(all_data.keys())
    report = []
    report.append("# AI 公司招聘战略洞察报告\n")
    report.append(f"对比公司: {', '.join(companies)}\n")
    
    # 1. 商业化阶段
    report.append("\n## 一、组织规模与商业化阶段\n")
    report.append("| 公司 | 总岗位 | 技术岗 | 非技术岗 | 非技术占比 | 阶段 |")
    report.append("|---|---|---|---|---|---|")
    for c in companies:
        m = analyze_maturity(c, all_data[c])
        report.append(f"| {c} | {m['total']} | {m['tech']} | {m['non_tech']} | {m['non_tech_pct']:.1f}% | {m['stage']} |")
    
    # 2. 战略方向
    report.append("\n## 二、战略方向信号矩阵\n")
    header = "| 方向 | " + " | ".join(companies) + " | 领先者 |"
    report.append(header)
    report.append("|---|" + "---|" * (len(companies) + 1))
    for dim in STRATEGY_DIMENSIONS:
        row = f"| {dim} |"
        scores = {}
        for c in companies:
            r = scan_strategy(c, all_data[c])
            cnt = r[dim]['count']
            pct = r[dim]['pct']
            row += f" {cnt}({pct:.1f}%) |"
            scores[c] = pct
        leader = max(scores, key=scores.get) if max(scores.values()) > 1 else '-'
        row += f" {leader} |"
        report.append(row)
    
    # 3. GTM拆解
    report.append("\n## 三、GTM/Sales 组织深度拆解\n")
    for c in companies:
        g = analyze_gtm(c, all_data[c])
        report.append(f"\n**{c}:** Sales={g['sales']}, GTM={g['gtm']}, Marketing={g['marketing']}, "
                     f"SE={g['solutions_engineer']}, CS={g['customer_success']}, 合作伙伴={g['partnerships']}")
    
    # 4. 全球化
    report.append("\n## 四、全球化布局\n")
    for c in companies:
        geo = analyze_geography(c, all_data[c])
        report.append(f"\n**{c}:** {geo['by_region']} | 新加坡: {geo['singapore']}")
    
    # 5. 人才画像
    report.append("\n## 五、人才画像\n")
    report.append("| 公司 | Senior+ 占比 | Manager/Director 占比 |")
    report.append("|---|---|---|")
    for c in companies:
        s = analyze_seniority(c, all_data[c])
        report.append(f"| {c} | {s['senior_pct']:.1f}% | {s['manager_pct']:.1f}% |")
    
    return '\n'.join(report)

# 执行
report_md = generate_report(all_data)
Path('talent_intel_report.md').write_text(report_md)
print(report_md)
```

## Step 4: Output Excel comparison

```python
def export_comparison_excel(all_data, output_path):
    """输出跨公司对比 Excel"""
    wb = Workbook()
    
    # Sheet 1: 汇总对比
    ws = wb.active
    ws.title = '战略对比总览'
    # ... (参考 job-radar 的 Excel 输出模板)
    
    # Sheet 2+: 每家公司一个 Sheet（全量明细）
    for company, jobs in all_data.items():
        ws_c = wb.create_sheet(f'{company}({len(jobs)})')
        # 写入该公司全量岗位...
    
    wb.save(output_path)

export_comparison_excel(all_data, 'talent_intel_comparison.xlsx')
```

## Analysis framework reference

### 关键判断规则

| 信号 | 如何判断 | 含义 |
|---|---|---|
| 非技术占比 > 50% | `non_tech / total > 0.5` | 公司已进入商业化成熟期 |
| GTM 是最大部门 | GTM 岗数 > 其他任何单一部门 | 公司第一优先级是卖产品 |
| Agent 岗位 > 20% | Agent 关键词命中数 / 总岗位 > 0.2 | 公司 All-in AI Agent 方向 |
| 新加坡岗 > 20 | Singapore 岗位计数 | 公司在建设 APAC 商业化总部 |
| Safety 部门独立存在 | Safety/Safeguards 作为独立部门 | 公司将安全作为品牌差异化 |
| Manager 占比 > 20% | Manager/Director title 占比 | 公司在快速搭建管理层骨架 |

## Pitfalls

- 各平台 JD 格式不同：Greenhouse 返回 HTML content，Ashby 返回 plain text，字节返回中文。关键词匹配需兼容中英文
- 部门分类不统一：Greenhouse 用 departments，Ashby 用 departmentName，字节用 job_category。需要在标准化层处理
- 小公司岗位少：当岗位数 < 50 时，百分比统计意义下降，应注明"样本量不足"

## Output convention

- `talent_intel_report.md` — 战略洞察报告（Markdown）
- `talent_intel_comparison.xlsx` — 数据对比表（Excel）
- `{company}_raw.json` — 各公司原始数据（可选）
