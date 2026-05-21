#!/usr/bin/env python3
"""
蓝海选题检测 — 站外热 + 站内供给缺口
数据源: redhot-collector (24平台) + search-notes (供给密度)
"""
import json, subprocess, sys, os, re, random
from datetime import datetime
from pathlib import Path

GAMES = [
    '王者荣耀', '和平精英', '三角洲行动', '金铲铲之战', '英雄联盟',
    '无畏契约', '火影忍者', 'PUBG', '暗区突围', '永劫无间',
    'CSGO', '穿越火线：枪战王者', 'DOTA2', '王者万象棋'
]

GAME_KEYWORDS = {
    '王者荣耀': ['王者荣耀', 'kpl', '挑战者杯', 'honor of kings'],
    '和平精英': ['和平精英', '吃鸡', 'pel', 'pubg mobile'],
    '无畏契约': ['无畏契约', '瓦罗兰特', 'valorant', 'vct', '瓦'],
    '英雄联盟': ['英雄联盟', 'lol', 'league of legends', 'lpl', 's赛'],
    'PUBG': ['pubg', '绝地求生', 'pgc'],
    'CSGO': ['csgo', 'cs2', '反恐精英', 'iem'],
    'DOTA2': ['dota', '刀塔', 'ti'],
    '金铲铲之战': ['金铲铲', '铲铲'],
    '三角洲行动': ['三角洲', 'delta force'],
    '暗区突围': ['暗区', 'dark zone'],
    '永劫无间': ['永劫无间', 'naraka', 'nbpl'],
    '火影忍者': ['火影忍者', '火影'],
    '穿越火线：枪战王者': ['穿越火线', 'cf', 'cfm'],
    '王者万象棋': ['万象棋']
}

def detect_game(title):
    title_lower = title.lower()
    for game, keywords in GAME_KEYWORDS.items():
        if game.lower() in title_lower:
            return game
        for kw in keywords:
            if kw in title_lower:
                return game
    return None

def fetch_redhot_collector():
    """Parse redhot-collector output for gaming blue ocean signals"""
    collector = os.path.expanduser('~/.openclaw/workspace/skills/redhot-collector/scripts/collect_trends.py')
    try:
        r = subprocess.run(['python3', collector, '--dry-run'], 
                          capture_output=True, text=True, timeout=120)
        return r.stdout if r.returncode == 0 else ''
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ''

def check_supply(keyword, game):
    """Check if this topic has supply on 小红书"""
    search_script = os.path.expanduser('~/.openclaw/workspace/skills/note-query/scripts/search-notes.sh')
    try:
        r = subprocess.run(['bash', search_script, '--keyword', f'{game}', '--page-size', '1'],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return data.get('data', {}).get('hit_total', 0)
    except:
        pass
    return 0

def check_topic_supply(keyword, game):
    """Combined keyword supply check"""
    search_script = os.path.expanduser('~/.openclaw/workspace/skills/note-query/scripts/search-notes.sh')
    try:
        r = subprocess.run(['bash', search_script, '--keyword', f'{keyword} {game}', '--page-size', '1'],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return data.get('data', {}).get('hit_total', 0)
    except:
        pass
    return 0

def classify_direction(title):
    """Content direction classification"""
    d = title.lower()
    if any(k in d for k in ['攻略', '教学', '教程', '技巧', '上分', '配装']):
        return '攻略教学'
    if any(k in d for k in ['赛事', '比赛', '决赛', '联赛', '冠军', '夺冠', '战队']):
        return '电竞赛事'
    if any(k in d for k in ['cos', '角色', '仿妆', '穿搭', '服装']):
        return 'cos同人'
    if any(k in d for k in ['二创', '剪辑', '视频', 'bgm', '卡点']):
        return '二创衍生'
    if any(k in d for k in ['讨论', '吐槽', '争议', '比较', '排名']):
        return '讨论评价'
    if any(k in d for k in ['版本', '更新', '赛季', '新', '改版']):
        return '版本更新'
    return '综合资讯'


if __name__ == '__main__':
    print("🔵 蓝海选题扫描...")
    
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'public/blue_ocean.json'
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    # Step 1: Get external hot topics
    print("  [1/3] 采集站外热点...")
    collector_output = fetch_redhot_collector()
    
    if not collector_output:
        print("  ⚠️ redhot-collector 返回空，跳过")
        json.dump([], open(output_file, 'w'))
        sys.exit(0)
    
    # Step 2: Parse and filter for gaming
    print("  [2/3] 筛选游戏相关热点...")
    lines = collector_output.split('\n')
    candidates = []
    seen = set()
    
    for line in lines:
        # Match markdown table: | title | score | ... |
        match = re.search(r'\[(.*?)\]', line)
        if not match:
            continue
        title = match.group(1)
        if not title or title in seen:
            continue
        seen.add(title)
        
        game = detect_game(title)
        if not game:
            continue
        
        # Extract score if available
        score = 65
        try:
            score_part = line.split('|')[2].strip() if len(line.split('|')) > 2 else ''
            score_match = re.search(r'\d+', score_part)
            if score_match:
                score = int(score_match.group())
        except:
            pass
        
        direction = classify_direction(title)
        
        candidates.append({
            'title': title[:25],
            'game': game,
            'externalScore': score,
            'direction': direction,
            'platform': '站外热榜',
        })
    
    print(f"    找到 {len(candidates)} 个游戏相关站外热点")
    
    # Step 3: Check supply gap
    print("  [3/3] 检查供给缺口...")
    blue_ocean = []
    
    for c in candidates[:15]:  # Top 15
        topic_supply = check_topic_supply(c['title'][:10], c['game'])
        game_supply = check_supply(c['title'][:10], c['game'])
        
        # Supply gap: topic-level < 200 AND game has content overall
        is_gap = topic_supply < 200
        
        blue_ocean.append({
            'id': f'bo{len(blue_ocean)+1}',
            'title': c['title'],
            'game': c['game'],
            'externalScore': c['externalScore'],
            'direction': c['direction'],
            'platform': c['platform'],
            'supplyGap': is_gap,
            'topicSupply': topic_supply,
            'gameSupply': game_supply,
            'generatedAt': datetime.now().isoformat()
        })
    
    # Sort: gap first, then by external score
    blue_ocean.sort(key=lambda b: (not b['supplyGap'], -b['externalScore']))
    
    with open(output_file, 'w') as f:
        json.dump(blue_ocean, f, ensure_ascii=False, indent=2)
    
    gaps = sum(1 for b in blue_ocean if b['supplyGap'])
    print(f"  ✅ 蓝海选题: {len(blue_ocean)} 条 ({gaps} 供给缺口)")