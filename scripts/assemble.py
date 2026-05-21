#!/usr/bin/env python3
"""数据汇总 — 合并讨论苗头 + 评论 + TGI → data.json"""
import json, os, sys
from datetime import datetime

PUBLIC = os.path.join(os.path.dirname(__file__), '..', 'public')

def load_json(filename):
    path = os.path.join(PUBLIC, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return [] if filename.endswith('sprouts') else {}

def main():
    raw = load_json('discussion_sprouts.json')
    # Handle both dict wrapper and flat list
    if isinstance(raw, dict):
        sprouts = raw.get('sprouts', raw.get('data', []))
    else:
        sprouts = raw if isinstance(raw, list) else []
    
    comments = load_json('comments.json')
    tgi = load_json('tgi.json')
    
    trends = []
    hots = []
    
    for sp in sprouts:
        note_id = sp.get('sourceNoteId', '')
        note_comments = comments.get(note_id, [])
        note_tgi = tgi.get(note_id, {})
        
        entry = {
            'id': f"ds{len(trends)+1}",
            'title': sp.get('topic', sp.get('sourceNoteTitle', ''))[:30],
            'game': sp.get('game', ''),
            'board': 'discussion',  # 讨论苗头
            'signalType': '讨论苗头',
            'commentToLikeRatio': round(sp.get('commentToLikeRatio', 0), 2),
            'commentCount': sp.get('commentCount', 0),
            'likeCount': sp.get('likeCount', 0),
            'tgi': note_tgi.get('tgi', '均衡'),
            'tgiRatio': note_tgi.get('maleRatio', 0.50),
            'tgiSource': note_tgi.get('source', 'inferred'),
            'sourceNoteId': note_id,
            'sourceNoteTitle': sp.get('sourceNoteTitle', ''),
            'sourceNoteUrl': f"https://www.xiaohongshu.com/explore/{note_id}",
            'taxonomy': sp.get('taxonomy', ''),
            'topComments': note_comments[:5] if note_comments else [],  # Top 5 hot comments
            'supplyDensity': sp.get('supplyDensity', 0),
            'supplyGap': sp.get('supplyGap', True),
            'generatedAt': datetime.now().isoformat()
        }
        trends.append(entry)
    
    # Sort by discussion intensity (comment/like ratio)
    trends.sort(key=lambda t: t['commentToLikeRatio'], reverse=True)
    
    data = {
        'generatedAt': datetime.now().isoformat(),
        'refreshInterval': '1h',
        'boards': {
            'discussionSprouts': trends[:15],
            'blueOcean': [],      # P1: redhot-collector 集成
            'hotspots': [],       # P1: redhot-xhs 集成  
            'esports': []         # P1: 赛事配置集成
        }
    }
    
    out_path = os.path.join(PUBLIC, 'data.json')
    with open(out_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  📊 data.json: {len(trends)} 讨论苗头")
    print(f"  📁 文件: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == '__main__':
    main()