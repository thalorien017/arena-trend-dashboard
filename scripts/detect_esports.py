#!/usr/bin/env python3
"""
赛事中心检测 — 已知电竞赛事关键词 + 站内笔记搜索
数据源: 静态赛事配置 + search-notes
"""
import json, subprocess, sys, os, random
from datetime import datetime

# Static tournament configuration (updated manually or via API P1)
TOURNAMENTS = [
    # 王者荣耀
    {'keyword': '挑战者杯', 'game': '王者荣耀', 'type': '总决赛', 'date': '2026-05-23', 'venue': '线上', 'priority': 10},
    {'keyword': 'AG超玩会 狼队', 'game': '王者荣耀', 'type': '焦点战', 'date': '2026-05-23', 'venue': '线上', 'priority': 9},
    # 英雄联盟
    {'keyword': 'LPL', 'game': '英雄联盟', 'type': '第二赛段', 'date': '2026-05-24', 'venue': '上海', 'priority': 9},
    {'keyword': 'BLG', 'game': '英雄联盟', 'type': '第一赛段冠军', 'date': 'ongoing', 'venue': '线上', 'priority': 7},
    # 无畏契约
    {'keyword': 'VCT EDG', 'game': '无畏契约', 'type': '第一赛段', 'date': '2026-05-10', 'venue': '全国七城', 'priority': 8},
    {'keyword': 'VCT CN', 'game': '无畏契约', 'type': '联赛', 'date': 'ongoing', 'venue': '全国七城', 'priority': 7},
    # 永劫无间
    {'keyword': 'NBPL', 'game': '永劫无间', 'type': '春季赛', 'date': '2026-05-17', 'venue': '西安', 'priority': 8},
    # 三角洲行动
    {'keyword': '烽火职业联赛', 'game': '三角洲行动', 'type': '春季赛', 'date': '2026-05-16', 'venue': '北京五棵松', 'priority': 8},
    # PUBG
    {'keyword': 'PEL', 'game': '和平精英', 'type': '联赛', 'date': 'ongoing', 'venue': '线上', 'priority': 6},
    # CSGO
    {'keyword': 'IEM', 'game': 'CSGO', 'type': '大师赛', 'date': 'ongoing', 'venue': '线上', 'priority': 6},
    {'keyword': 'CS Major', 'game': 'CSGO', 'type': 'Major', 'date': 'ongoing', 'venue': '线上', 'priority': 5},
    # DOTA2
    {'keyword': 'TI', 'game': 'DOTA2', 'type': '国际邀请赛', 'date': 'ongoing', 'venue': '线上', 'priority': 5},
    # 火影忍者
    {'keyword': '火影忍者 联赛', 'game': '火影忍者', 'type': '联赛', 'date': 'ongoing', 'venue': '线上', 'priority': 4},
    # KPL
    {'keyword': 'KPL', 'game': '王者荣耀', 'type': '联赛', 'date': 'ongoing', 'venue': '线上', 'priority': 7},
    # 国际电竞  
    {'keyword': '电竞世界杯', 'game': '多游戏', 'type': '综合赛事', 'date': 'pending', 'priority': 6},
]

SEARCH_SCRIPT = os.path.expanduser('~/.openclaw/workspace/skills/note-query/scripts/search-notes.sh')

def search_esports_notes(keyword, limit=3):
    """Search for esports-related notes"""
    try:
        r = subprocess.run(
            ['bash', SEARCH_SCRIPT, '--keyword', keyword,
             '--sort-by', 'LIKES', '--min-likes', '2000', '--page-size', str(limit)],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return data.get('data', {}).get('note_cards', [])
    except:
        pass
    return []


if __name__ == '__main__':
    print("🏆 赛事中心扫描...")
    
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'public/esports.json'
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    events = []
    seen_keywords = set()
    
    # Search each tournament keyword
    print(f"  [1/1] 搜索 {len(TOURNAMENTS)} 项赛事...")
    
    for t in sorted(TOURNAMENTS, key=lambda x: x['priority'], reverse=True)[:10]:
        kw = t['keyword']
        if kw in seen_keywords:
            continue
        seen_keywords.add(kw)
        
        notes = search_esports_notes(kw, 2)
        
        sample_notes = []
        total_likes = 0
        for n in notes:
            title = n.get('note_base_info', {}).get('title', '').strip()
            if '非公开' in title:
                continue
            nid = n.get('note_id', '')
            likes = n.get('note_count_info', {}).get('like_count', 0)
            total_likes += likes
            sample_notes.append({
                'title': title[:20],
                'url': f'https://www.xiaohongshu.com/explore/{nid}',
                'likes': likes
            })
        
        heat = min(int(total_likes / 10000 * 30 + 60), 95) if total_likes > 0 else t['priority'] * 6
        
        events.append({
            'id': f'e{len(events)+1}',
            'tournament': kw,
            'game': t['game'],
            'type': t['type'],
            'date': t['date'],
            'venue': t['venue'],
            'heatScore': heat,
            'noteCount': len(sample_notes),
            'totalLikes': total_likes,
            'sampleNotes': sample_notes,
            'priority': t['priority'],
            'generatedAt': datetime.now().isoformat()
        })
        
        if sample_notes:
            print(f"    {kw} ({t['game']}): {len(sample_notes)} notes, {heat} heat")
    
    events.sort(key=lambda e: e['heatScore'], reverse=True)
    
    with open(output_file, 'w') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    with_data = sum(1 for e in events if e['sampleNotes'])
    print(f"  ✅ 赛事: {len(events)} 项 ({with_data} 有站内数据)")