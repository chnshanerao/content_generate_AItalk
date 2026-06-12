---
name: job-radar
description: "AI 岗位雷达 — 一键式全量岗位爬取 + 画像匹配。输入公司名即可自动检测招聘平台(Greenhouse/Ashby/字节自研)、全量拉取岗位、按用户画像打分排序、输出Excel报告。支持 ByteDance/OpenAI/Anthropic/Stripe/Figma 等数千家公司。触发词：'帮我看XX公司的招聘'、'scrape jobs from XX'、'XX有什么岗位适合我'、'爬取XX的职位'、'job radar'。"
version: 1.0.0
---

# Job Radar — AI 岗位雷达

一键式全量岗位爬取 + 智能画像匹配。输入公司名，自动检测招聘平台，全量拉取，按用户画像排序输出。

## When to use

- 用户想看某家公司的全部在招岗位
- 用户想知道某公司有哪些岗位适合自己
- 需要批量爬取多家公司的职位数据进行对比
- 用户说"帮我看XX的招聘"、"XX有什么岗位"、"scrape XX jobs"

## Step 1: Detect ATS platform

每家公司的招聘页面跑在不同的 ATS（Applicant Tracking System）平台上。先自动检测：

```python
import requests, json, re, sys, time
from pathlib import Path

COMPANY = "{{COMPANY_NAME}}"  # 用户输入的公司名，如 anthropic, openai, stripe, bytedance

def detect_ats(company):
    """自动检测公司使用的 ATS 平台"""
    company_lower = company.lower().replace(' ', '').replace('-', '')
    
    # 1. 已知映射（优先）
    KNOWN = {
        'bytedance': 'bytedance', '字节跳动': 'bytedance', '字节': 'bytedance',
        'openai': 'ashby',
        'anthropic': 'greenhouse',
        'stripe': 'greenhouse',
        'figma': 'greenhouse',
        'notion': 'ashby',
        'ramp': 'ashby',
        'coinbase': 'ashby',
    }
    if company_lower in KNOWN:
        return KNOWN[company_lower], company_lower
    
    # 2. 探测 Greenhouse API
    for slug in [company_lower, company.lower().replace(' ', '-')]:
        try:
            r = requests.get(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs',
                           headers={'Accept': 'application/json'}, timeout=10)
            data = r.json()
            if data.get('jobs') is not None:
                return 'greenhouse', slug
        except: pass
    
    # 3. 探测 Ashby
    for slug in [company_lower, company.lower().replace(' ', '-')]:
        try:
            r = requests.get(f'https://jobs.ashbyhq.com/{slug}',
                           headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}, timeout=10)
            if r.status_code == 200 and 'jobPostings' in r.text:
                return 'ashby', slug
        except: pass
    
    # 4. 探测 Lever
    for slug in [company_lower, company.lower().replace(' ', '-')]:
        try:
            r = requests.get(f'https://api.lever.co/v0/postings/{slug}?mode=json',
                           headers={'Accept': 'application/json'}, timeout=10)
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return 'lever', slug
        except: pass
    
    return 'unknown', company_lower

ats, slug = detect_ats(COMPANY)
print(f"Detected: {COMPANY} → ATS={ats}, slug={slug}")
```

## Step 2: Scrape jobs by platform

### 2a. Greenhouse (Anthropic, Stripe, Figma, etc.)

```python
def scrape_greenhouse(slug):
    """Greenhouse 有公开的 JSON API，直接调用"""
    r = requests.get(
        f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true',
        headers={'Accept': 'application/json'}, timeout=30)
    r.raise_for_status()
    raw_jobs = r.json().get('jobs', [])
    
    jobs = []
    for j in raw_jobs:
        jobs.append({
            'id': str(j.get('id', '')),
            'title': j.get('title', ''),
            'department': ', '.join(d.get('name','') for d in j.get('departments', [])),
            'location': ', '.join(o.get('name','') for o in j.get('offices', [])),
            'description': html_to_text(j.get('content', '')),
            'url': j.get('absolute_url', ''),
            'updated_at': j.get('updated_at', ''),
            'source': 'greenhouse',
        })
    return jobs
```

### 2b. Ashby (OpenAI, Notion, Ramp, etc.)

```python
def scrape_ashby(slug):
    """Ashby 把职位数据嵌入在 HTML 的 JSON 中，需要从 HTML 提取"""
    r = requests.get(
        f'https://jobs.ashbyhq.com/{slug}',
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html',
        }, timeout=30)
    r.raise_for_status()
    html = r.text
    
    # 从 HTML 中提取 jobPostings JSON 数组
    idx = html.find('"jobPostings":[')
    if idx < 0:
        raise ValueError("Cannot find jobPostings in Ashby HTML")
    
    start = idx + len('"jobPostings":')
    bracket_count = 0
    end = start
    for i in range(start, min(start + 10_000_000, len(html))):
        if html[i] == '[': bracket_count += 1
        elif html[i] == ']': bracket_count -= 1
        if bracket_count == 0:
            end = i + 1
            break
    
    raw_jobs = json.loads(html[start:end])
    
    jobs = []
    for j in raw_jobs:
        jobs.append({
            'id': j.get('id', ''),
            'title': j.get('title', ''),
            'department': j.get('departmentName', ''),
            'location': j.get('locationName', ''),
            'description': html_to_text(j.get('descriptionPlain', '') or j.get('descriptionHtml', '') or ''),
            'url': f"https://jobs.ashbyhq.com/{slug}/{j.get('id','')}",
            'updated_at': j.get('updatedAt', ''),
            'source': 'ashby',
        })
    return jobs
```

### 2c. ByteDance (字节跳动自研平台)

```python
def scrape_bytedance(keyword='', location_codes=None):
    """字节跳动使用自研招聘系统，需要 9 个特殊 Header"""
    HEADERS = {
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',  # 必须精确匹配，否则 405
        'website-path': 'society',   # 必须，值=society（社招），来自 HTML 嵌入的 js-websiteInfo
        'portal-channel': 'office',
        'portal-platform': 'pc',
        'env': 'undefined',
        'atsx-portal-from': 'career',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://jobs.bytedance.com/experienced/position',
        'Origin': 'https://jobs.bytedance.com',
    }
    URL = 'https://jobs.bytedance.com/api/v1/search/job/posts'
    
    all_jobs = []
    offset = 0
    while True:
        body = {'keyword': keyword, 'limit': 100, 'offset': offset, 'portal_type': 2}
        if location_codes:
            body['location_code_list'] = location_codes
        # 注意: 不要传 job_hot_flag（必须是 int64 或不传，传空字符串会 400）
        r = requests.post(URL, headers=HEADERS, json=body, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get('code') != 0:
            break
        batch = data['data']['job_post_list']
        total = data['data']['count']
        all_jobs.extend(batch)
        if not batch or len(batch) < 100 or len(all_jobs) >= total:
            break
        offset += 100
        time.sleep(0.3)
    
    jobs = []
    for j in all_jobs:
        cities = ', '.join(c.get('name','') for c in (j.get('city_list') or []))
        cat = (j.get('job_category') or {}).get('name', '')
        jobs.append({
            'id': str(j.get('id', '')),
            'title': j.get('title', ''),
            'department': cat,
            'location': cities,
            'description': j.get('description', '') or '',
            'requirement': j.get('requirement', '') or '',
            'url': f"https://jobs.bytedance.com/experienced/position/{j.get('id','')}/detail",
            'updated_at': '',
            'source': 'bytedance',
        })
    return jobs
```

### 2d. Lever (Cloudflare, Twitch, etc.)

```python
def scrape_lever(slug):
    """Lever 有公开 JSON API"""
    r = requests.get(
        f'https://api.lever.co/v0/postings/{slug}?mode=json',
        headers={'Accept': 'application/json'}, timeout=30)
    r.raise_for_status()
    raw_jobs = r.json()
    
    jobs = []
    for j in raw_jobs:
        cats = j.get('categories', {})
        jobs.append({
            'id': j.get('id', ''),
            'title': j.get('text', ''),
            'department': cats.get('department', '') or cats.get('team', ''),
            'location': cats.get('location', ''),
            'description': j.get('descriptionPlain', ''),
            'url': j.get('hostedUrl', ''),
            'updated_at': '',
            'source': 'lever',
        })
    return jobs
```

### 2e. Universal dispatcher

```python
def scrape_company(company_name, keyword=''):
    ats, slug = detect_ats(company_name)
    print(f"Detected: {company_name} → {ats} (slug={slug})")
    
    if ats == 'greenhouse':
        return scrape_greenhouse(slug)
    elif ats == 'ashby':
        return scrape_ashby(slug)
    elif ats == 'bytedance':
        return scrape_bytedance(keyword=keyword)
    elif ats == 'lever':
        return scrape_lever(slug)
    else:
        print(f"WARNING: Unknown ATS for {company_name}. Try web search as fallback.")
        return []
```

## Step 3: Profile matching

```python
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return ' '.join(self.text)

def html_to_text(html_str):
    if not html_str: return ''
    p = HTMLTextExtractor()
    try: p.feed(str(html_str)); return p.get_text()
    except: return re.sub(r'<[^>]+>', ' ', str(html_str))

# 用户画像关键词配置（权重 1-10）
# 根据用户实际背景调整
PROFILE_KEYWORDS = {
    # 示例：销售运营背景
    'sales operations': 10, 'GTM': 10, 'go-to-market': 10,
    'strategy': 8, 'competitive analysis': 9, 'product marketing': 9,
    'enterprise': 6, 'B2B': 6, 'SaaS': 5,
    'data analysis': 5, 'pricing': 7, 'pipeline': 5,
    'AI': 3, 'cloud': 5, 'international': 6,
    # 添加你自己的关键词...
}

EXCLUDE_CATEGORIES = {'后端', '前端', '客户端', '硬件', '基础架构', '运维', '测试', '安全'}

def score_job(job):
    text = f"{job.get('title','')} {job.get('description','')} {job.get('requirement','')}".lower()
    s, hits = 0, []
    for kw, w in PROFILE_KEYWORDS.items():
        if kw.lower() in text:
            s += w; hits.append(kw)
    return s, hits

def tier_label(sc):
    if sc >= 50: return 'Tier1-强烈推荐'
    if sc >= 30: return 'Tier2-值得关注'
    if sc >= 15: return 'Tier3-可考虑'
    return ''
```

## Step 4: Output Excel

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def export_excel(jobs, company_name, output_path):
    """输出 Excel 报告"""
    wb = Workbook()
    
    # Styles
    hdr_font = Font(name='Arial', bold=True, size=11, color='FFFFFF')
    hdr_fill = PatternFill(start_color='2B579A', end_color='2B579A', fill_type='solid')
    t1_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    t2_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    border = Border(left=Side(style='thin',color='D9D9D9'), right=Side(style='thin',color='D9D9D9'),
                    top=Side(style='thin',color='D9D9D9'), bottom=Side(style='thin',color='D9D9D9'))
    
    # Sheet 1: 全量明细
    ws = wb.active
    ws.title = f'{company_name} 全量'
    headers = ['序号','职位','部门','地点','匹配分','等级','命中词','链接','描述']
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = hdr_font; c.fill = hdr_fill; c.border = border
    
    scored = []
    for j in jobs:
        sc, hits = score_job(j)
        scored.append((sc, hits, j))
    scored.sort(key=lambda x: -x[0])
    
    for idx, (sc, hits, j) in enumerate(scored, 1):
        t = tier_label(sc)
        row = [idx, j['title'], j['department'], j['location'], sc, t,
               ', '.join(hits), j.get('url',''), j.get('description','')[:300]]
        for col, val in enumerate(row, 1):
            c = ws.cell(row=idx+1, column=col, value=val)
            c.border = border
            if 'Tier1' in t: c.fill = t1_fill
            elif 'Tier2' in t: c.fill = t2_fill
    
    widths = [6,40,25,25,8,16,30,50,50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.auto_filter.ref = f'A1:I{len(scored)+1}'
    ws.freeze_panes = 'A2'
    
    wb.save(output_path)
    return len(scored), sum(1 for s,_,_ in scored if s >= 30)
```

## Step 5: Full pipeline

```python
# 完整流程
companies = ["anthropic"]  # 可以传多家: ["anthropic", "openai", "stripe"]

for company in companies:
    print(f"\n{'='*60}")
    print(f"Processing: {company}")
    print(f"{'='*60}")
    
    jobs = scrape_company(company)
    print(f"  Scraped: {len(jobs)} jobs")
    
    out_path = f'{company}_jobs_report.xlsx'
    total, matched = export_excel(jobs, company, out_path)
    print(f"  Output: {out_path}")
    print(f"  Total: {total} | Matched(Tier1+2): {matched}")
```

## Pitfalls

| 问题 | 原因 | 解决 |
|---|---|---|
| ByteDance API 返回 405 | 缺少 `Accept: application/json, text/plain, */*` 头（必须精确匹配） | 使用完整的 9 个 Header |
| ByteDance API 返回 400 | `job_hot_flag` 字段传了空字符串（必须是 int64 或不传） | 从请求体中删除该字段 |
| ByteDance API 返回 200 但是 HTML | 用了 GET 请求（GET 走 SPA 路由，POST 才是 API） | 改用 POST |
| Ashby 页面无 jobPostings | 公司可能不用 Ashby，或 slug 错误 | 检查 slug 拼写 |
| Greenhouse 返回 404 | slug 不匹配（如 `open-ai` vs `openai`） | 尝试多种 slug 变体 |
| OpenAI/Anthropic 页面 403 | Cloudflare 反爬保护 | 用 Greenhouse/Ashby API 而不是直接访问官网 |
| `limit > 100` 无效 | ByteDance API 静默截断为 100 | 始终用 100 + 分页 |
| openpyxl 安装失败 | Python 环境限制 | `pip install openpyxl --break-system-packages` |

## Location codes (ByteDance)

| 城市 | 代码 | 城市 | 代码 |
|---|---|---|---|
| 北京 | CT_1 | 上海 | CT_2 |
| 深圳 | CT_128 | 杭州 | CT_3 |
| 广州 | CT_124 | 成都 | CT_5 |
| Singapore | CT_92 | 全部 | 不传 |

## Known company → ATS mappings

| Company | ATS | Slug | Notes |
|---|---|---|---|
| ByteDance/字节跳动 | bytedance | bytedance | 自研，需9个Header |
| OpenAI | ashby | openai | HTML内嵌JSON |
| Anthropic | greenhouse | anthropic | 公开API |
| Stripe | greenhouse | stripe | 公开API |
| Figma | greenhouse | figma | 公开API |
| Notion | ashby | notion | HTML内嵌JSON |
| Ramp | ashby | ramp | HTML内嵌JSON |
| Coinbase | ashby | coinbase | HTML内嵌JSON |
| Cloudflare | lever | cloudflare | 公开API |
| Twitch | lever | twitch | 公开API |

## Verification

1. 运行后检查 Excel 文件是否生成，行数 > 0
2. 抽查一个 Tier1 岗位的链接是否能打开
3. 对比 Excel 中的总数与网站上显示的岗位数（允许 ±5% 误差）
4. 检查匹配分 > 0 的岗位是否确实包含命中关键词

## Output convention

- `{company}_jobs_report.xlsx` — 主报告（全量明细 + 匹配排序）
- `{company}_raw.json` — 原始 API 返回数据（可选保存）
