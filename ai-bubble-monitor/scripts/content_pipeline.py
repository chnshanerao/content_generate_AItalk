#!/usr/bin/env python3
"""内容生产 Pipeline — 一键从数据到内容"""

import json, sys
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'
OUTPUT_DIR = BASE_DIR / 'content_output'

sys.path.insert(0, str(Path(__file__).parent))
import story_detector
import content_writer
import chart_generator

def run(today_str=None):
    today = today_str or date.today().isoformat()
    output_dir = OUTPUT_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"  内容生产 Pipeline — {today}")
    print(f"{'='*60}\n")

    # Load snapshots
    snaps = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if not snaps:
        print("ERROR: No snapshots found. Run monitor.py first.")
        return
    current = json.loads(snaps[-1].read_text())
    previous = json.loads(snaps[-2].read_text()) if len(snaps) >= 2 else None
    print(f"[1/4] 数据加载完成: {snaps[-1].name}" + (f" vs {snaps[-2].name}" if previous else " (首期，无对比)"))

    # Step 2: Story detection
    print(f"\n[2/4] 爆点发现...")
    stories = story_detector.run(current, previous)
    print(f"  发现 {len(stories)} 个故事线索")
    for i, s in enumerate(stories[:3], 1):
        print(f"  [{i}] 传播力 {s['virality']}/10 | {s['detector']} | {s['headline_cn'][:50]}...")

    # Save raw insights
    (output_dir / 'raw_insights.json').write_text(
        json.dumps(stories, ensure_ascii=False, indent=2))

    # Step 3: Content writing
    print(f"\n[3/4] 内容撰写...")
    content = content_writer.run(stories, current, previous, output_dir)

    # Step 4: Chart generation
    print(f"\n[4/4] 图表生成...")
    chart_generator.run(current, previous, stories, output_dir)

    # Summary
    files = list(output_dir.rglob('*'))
    print(f"\n{'='*60}")
    print(f"  Pipeline 完成!")
    print(f"  输出目录: {output_dir}")
    print(f"  生成文件:")
    for f in sorted(files):
        if f.is_file():
            size = f.stat().st_size
            print(f"    {f.relative_to(output_dir)} ({size:,} bytes)")
    print(f"{'='*60}")

    # Print LinkedIn preview
    print(f"\n{'='*60}")
    print(f"  LinkedIn 帖子预览 (前 500 字):")
    print(f"{'='*60}")
    print(content['linkedin'][:500])
    print("...\n")

    # Print YouTube title
    print(f"  YouTube 标题: {content.get('title', 'N/A')}")

    return {
        'stories': stories,
        'content': content,
        'output_dir': str(output_dir),
    }

if __name__ == '__main__':
    today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    run(today)
