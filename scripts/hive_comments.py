#!/usr/bin/env python3
"""Hive 评论批量查询 — 从 dw_soc_discovery_comment_day 提取评论内容"""
import json, subprocess, sys, time, os

SQL_DEV = os.path.expanduser('~/.openclaw/workspace/skills/sql-development/scripts/run.py')
WAIT_INTERVAL = 15  # 轮询间隔
MAX_WAIT = 300  # 最多等 5 分钟

def run_sql(sql, timeout=MAX_WAIT):
    """提交 SQL → 轮询 → 获取结果"""
    # Submit
    r = subprocess.run(
        ['python3', SQL_DEV, 'submit', '--code', sql, '--language', 'HiveSQL'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return None
    
    # Extract msgId
    for line in r.stdout.split('\n'):
        if 'msgId' in line:
            msg_id = line.split('`')[1]
            break
    else:
        return None
    
    # Poll
    elapsed = 0
    while elapsed < timeout:
        time.sleep(WAIT_INTERVAL)
        elapsed += WAIT_INTERVAL
        
        r = subprocess.run(
            ['python3', SQL_DEV, 'status', '--msg-id', msg_id],
            capture_output=True, text=True, timeout=15
        )
        if 'FINISHED' in r.stdout and 'SUCCESS' in r.stdout:
            break
    
    # Get result
    r = subprocess.run(
        ['python3', SQL_DEV, 'result', '--msg-id', msg_id],
        capture_output=True, text=True, timeout=15
    )
    return r.stdout


if __name__ == '__main__':
    sprouts_file = sys.argv[1] if len(sys.argv) > 1 else 'public/discussion_sprouts.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'public/comments.json'
    
    with open(sprouts_file) as f:
        sprouts = json.load(f)
    
    note_ids = [s['sourceNoteId'] for s in sprouts if s.get('sourceNoteId')]
    
    if not note_ids:
        print("  ℹ️ 无笔记ID，跳过")
        json.dump({}, open(output_file, 'w'))
        sys.exit(0)
    
    # Batch all notes into one SQL
    ids_str = ', '.join([f"'{nid}'" for nid in note_ids])
    today = time.strftime('%Y%m%d')
    
    sql = f"""
SELECT discovery_id, id AS comment_id, content AS comment_text,
       comment_level, like_count, create_time
FROM reddw.dw_soc_discovery_comment_day
WHERE discovery_id IN ({ids_str})
  AND dtm >= '{today}'
  AND content IS NOT NULL
ORDER BY discovery_id, like_count DESC
"""
    
    print(f"  📤 提交评论查询 ({len(note_ids)} 笔记)...")
    result = run_sql(sql)
    
    if result and 'comment_text' in result:
        # Parse pipe-delimited output
        comments_by_note = {}
        lines = result.strip().split('\n')
        for line in lines:
            if '|' not in line or 'comment_id' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                note_id = parts[0]
                if note_id not in comments_by_note:
                    comments_by_note[note_id] = []
                comments_by_note[note_id].append(parts[2] if len(parts) > 2 else '')
        
        with open(output_file, 'w') as f:
            json.dump(comments_by_note, f, ensure_ascii=False)
        print(f"  ✅ 评论: {sum(len(v) for v in comments_by_note.values())} 条")
    else:
        # Fallback: empty
        json.dump({}, open(output_file, 'w'))
        print("  ⚠️ 评论查询无结果（表结构需核对，P1修复）")