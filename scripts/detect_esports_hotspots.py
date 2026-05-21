#!/usr/bin/env python3
"""赛事热点检测 — 按具体事件搜索，不是按联赛归类"""
import json, subprocess, sys, os
from datetime import datetime

HOT_EVENTS = [
    # 王者荣耀 挑战者杯
    {'query': 'AG超玩会 挑战者杯 夺冠', 'game': '王者荣耀', 'tag': '挑战者杯'},
    {'query': 'AG超玩会 狼队 决赛', 'game': '王者荣耀', 'tag': '挑战者杯'},
    {'query': 'AG超玩会 4:3 狼队', 'game': '王者荣耀', 'tag': '挑战者杯-焦点战'},
    # 英雄联盟
    {'query': 'BLG LPL 第一赛段 夺冠', 'game': '英雄联盟', 'tag': 'LPL'},
    {'query': 'LPL 第二赛段 WE LNG', 'game': '英雄联盟', 'tag': 'LPL-赛程'},
    {'query': 'IG TT 虎牙', 'game': '英雄联盟', 'tag': 'LPL-赛程'},
    # 无畏契约
    {'query': 'EDG VCT 夺冠', 'game': '无畏契约', 'tag': 'VCT CN'},
    {'query': 'EDG XLG VCT 决赛', 'game': '无畏契约', 'tag': 'VCT CN'},
    {'query': 'VCT 七城巡回', 'game': '无畏契约', 'tag': 'VCT CN-全国'},
    # 永劫无间
    {'query': 'NBPL 春季赛 冠军', 'game': '永劫无间', 'tag': 'NBPL'},
    {'query': 'IG 永劫无间 NBPL', 'game': '永劫无间', 'tag': 'NBPL-iG'},
    # 三角洲行动
    {'query': 'TES 烽火职业联赛 夺冠', 'game': '三角洲行动', 'tag': '烽火联赛'},
    {'query': '烽火职业联赛 五棵松', 'game': '三角洲行动', 'tag': '烽火联赛'},
    # CSGO
    {'query': 'CS2 IEM', 'game': 'CSGO', 'tag': 'IEM'},
    # DOTA2
    {'query': 'DOTA2 巴西 议员 约战', 'game': 'DOTA2', 'tag': '国际约战'},
    # KPL 常规热点
    {'query': 'KPL 今日赛果', 'game': '王者荣耀', 'tag': 'KPL'},
    
    # 电竞综合热点
    {'query': '电竞世界杯 中国', 'game': '多游戏', 'tag': '电竞世界杯'},
    {'query': '网易520 发布会 电竞', 'game': '多游戏', 'tag': '行业事件'},
]

SCRIPT = os.path.expanduser('~/.openclaw/workspace/skills/note-query/scripts/search-notes.sh')

def search(query, limit=3):
    try:
        r = subprocess.run(['bash', SCRIPT, '--keyword', query, '--sort-by', 'LIKES',
                           '--min-likes', '1000', '--page-size', str(limit)],
                          capture_output=True, text=True, timeout=12)
        if r.returncode == 0:
            return json.loads(r.stdout).get('data', {}).get('note_cards', [])
    except: pass
    return []

if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'public/esports.json'
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    events = []
    seen_titles = set()
    
    for evt in HOT_EVENTS[:15]:
        notes = search(evt['query'], 3)
        
        sample_notes = []
        total_likes = 0
        for n in notes:
            title = n.get('note_base_info', {}).get('title', '').strip()
            if '非公开' in title or title in seen_titles: continue
            seen_titles.add(title)
            nid = n.get('note_id', '')
            likes = n.get('note_count_info', {}).get('like_count', 0)
            total_likes += likes
            sample_notes.append({'title': title[:25], 'url': f'https://www.xiaohongshu.com/explore/{nid}', 'likes': likes})
        
        if not sample_notes: continue
        
        # Generate specific analysis based on content
        titles_text = ' '.join(n['title'] for n in sample_notes)
        if any(k in titles_text for k in ['夺冠', '冠军', '4:3', '战胜']):
            analysis = f"赛事结果讨论 · {evt['query'][:20]}引发热议"
            suggestion = f"促产方向：赛果回顾拆条 / 选手高光剪辑 / 「你怎么看这场」互动投票"
        elif any(k in titles_text for k in ['赛程', '对阵', 'WE', 'LNG', 'IG', 'TT']):
            analysis = f"赛程关注 · {evt['query'][:20]}即将开战"
            suggestion = "促产方向：对阵预测图文 / 战队分析 vlog / 盲猜投票"
        else:
            analysis = f"赛事热点 · {evt['query'][:25]}"
            suggestion = "促产方向：赛事解读图文 / 话题讨论 / 选手专访"
        
        heat = min(int(total_likes / 5000 + 60), 95) if total_likes > 0 else 55
        
        events.append({
            'id': f'e{len(events)+1}',
            'topic': evt['query'][:25],  # Specific topic, not league name
            'game': evt['game'],
            'tag': evt['tag'],
            'heatScore': heat,
            'totalLikes': total_likes,
            'noteCount': len(sample_notes),
            'sampleNotes': sample_notes,
            'analysis': analysis,
            'suggestion': suggestion,
            'generatedAt': datetime.now().isoformat()
        })
    
    events.sort(key=lambda e: e['heatScore'], reverse=True)
    
    with open(output_file, 'w') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    print(f"🏆 赛事热点: {len(events)} 项")
    for e in events:
        print(f"  {e['tag']} | {e['topic']} ({e['game']}) {e['heatScore']} | {e['noteCount']} notes")