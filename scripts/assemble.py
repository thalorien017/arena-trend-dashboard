#!/usr/bin/env python3
"""数据汇总 v2 — 合并 4 看板 → data.json"""
import json, os
from datetime import datetime

PUBLIC = os.path.join(os.path.dirname(__file__), '..', 'public')

def load_json(name):
    path = os.path.join(PUBLIC, name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def main():
    sprouts = load_json('discussion_sprouts.json')
    if isinstance(sprouts, dict):
        sprouts = sprouts.get('sprouts', [])
    
    blue = load_json('blue_ocean.json')
    hotspots = load_json('hotspots.json')
    esports = load_json('esports.json')
    tgi = load_json('tgi.json')
    if isinstance(tgi, list):
        # Convert list to dict by note ID
        tgi = {item.get('sourceNoteId', ''): item for item in tgi if isinstance(item, dict)}
    
    comments = load_json('comments.json')
    if isinstance(comments, list):
        comments = {item.get('sourceNoteId', ''): item.get('comments', []) for item in comments if isinstance(item, dict)}
    
    # Discussion sprouts processing
    trends = []
    for sp in sprouts:
        note_id = sp.get('sourceNoteId', '')
        note_tgi = tgi.get(note_id, {})
        note_comments = comments.get(note_id, [])
        
        trends.append({
            'id': f"ds{len(trends)+1}",
            'title': sp.get('sourceNoteTitle', sp.get('topic', ''))[:30],
            'game': sp.get('game', ''),
            'board': 'discussion',
            'signalType': '讨论苗头',
            'commentToLikeRatio': round(sp.get('commentToLikeRatio', 0), 2),
            'commentCount': sp.get('commentCount', 0),
            'tgi': note_tgi.get('tgi', '均衡'),
            'tgiRatio': note_tgi.get('maleRatio', 0.50),
            'sourceNoteUrl': f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else '',
            'topComments': note_comments[:5] if note_comments else [],
            'generatedAt': datetime.now().isoformat()
        })
    trends.sort(key=lambda t: t['commentToLikeRatio'], reverse=True)
    
    data = {
        'generatedAt': datetime.now().isoformat(),
        'refreshInterval': '1h',
        'nextRefresh': '整点自动刷新',
        'boards': {
            'discussionSprouts': trends[:15],
            'blueOcean': blue[:10],
            'hotspots': hotspots[:12],
            'esports': esports[:10]
        },
        'summary': {
            'discussionSprouts': len(trends),
            'blueOcean': len(blue),
            'hotspots': len(hotspots),
            'esports': len(esports),
            'totalGames': len(set(
                t['game'] for t in trends + blue + hotspots + 
                [e for e in esports if e['game'] != '多游戏']
            ))
        }
    }
    
    out_path = os.path.join(PUBLIC, 'data.json')
    with open(out_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"📊 data.json {len(json.dumps(data))} bytes")
    print(f"  讨论苗头: {len(trends)} | 蓝海: {len(blue)} | 热点: {len(hotspots)} | 赛事: {len(esports)}")
    print(f"  覆盖: {data['summary']['totalGames']} 款游戏")

if __name__ == '__main__':
    main()