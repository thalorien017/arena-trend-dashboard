#!/usr/bin/env python3
"""讨论苗头检测脚本 v1
扫描站内笔记的高评论/点赞比信号 → 供给密度判定 → TGI 标注
"""

import json, subprocess, sys, argparse, math
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────

GAMES = [
    '王者荣耀', '和平精英', '三角洲行动', '金铲铲之战', '英雄联盟',
    '无畏契约', '火影忍者', 'PUBG', '暗区突围', '永劫无间',
    'CSGO', '穿越火线：枪战王者', 'DOTA2', '王者万象棋'
]

# Discussion sprout detection thresholds
MIN_COMMENT_TO_LIKE_RATIO = 0.08  # 8% — TIME-sorted notes naturally have fewer comments
MIN_COMMENT_COUNT = 20  # lowered for recent notes
SUPPLY_GAP_THRESHOLD = 10000  # game-level proxy (P0 limitation)
# Taxonomy filter: must match gaming-related categories
TAXONOMY_GAME_FILTER = ['游戏', '电竞', '二次元', '动漫']  # 火影/永劫归在二次元动漫下

# TGI inference based on taxonomy keywords
FEMALE_TAXONOMY_KWS = ['同人', 'cos', '仿妆', '养成', '恋爱', '女性', 'cp', '穿搭', '时尚', '情感', '萌娃']
MALE_TAXONOMY_KWS = ['电竞', '攻略', '赛事', '技术', '排位', '上分', '对战', '数据', '机械', '军事']

SEARCH_SCRIPT = str(Path.home() / '.openclaw/workspace/skills/note-query/scripts/search-notes.sh')
COMMENT_SCRIPT = str(Path.home() / '.openclaw/workspace/skills/note-query/scripts/query-note-clinic.sh')

def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except:
        return "", -1

def search_notes(keyword, sort_by='TIME', min_likes=200, page_size=8):
    out, code = run_cmd([
        'bash', SEARCH_SCRIPT,
        '--keyword', keyword,
        '--sort-by', sort_by,
        '--min-likes', str(min_likes),
        '--page-size', str(page_size)
    ], timeout=15)
    if code != 0 or not out:
        return []
    try:
        return json.loads(out).get('data', {}).get('note_cards', [])
    except:
        return []

def check_supply_density(topic, game):
    """
    Query supply density for this discussion topic.
    
    P0 limitation: search-notes uses exact keyword match, so topic-level queries
    often return 0 even when related content exists. Uses game name as broad proxy.
    P1: replace with taxonomy-level density or embedding-based similarity.
    """
    out, code = run_cmd([
        'bash', SEARCH_SCRIPT,
        '--keyword', game,
        '--page-size', '1'
    ], timeout=10)
    if code != 0 or not out:
        return -1
    try:
        return json.loads(out).get('data', {}).get('hit_total', 0)
    except:
        return -1

def infer_tgi(title, taxonomy):
    """Infer gender orientation from taxonomy + title keywords"""
    combined = (title + ' ' + taxonomy).lower()
    female_score = sum(1 for kw in FEMALE_TAXONOMY_KWS if kw in combined)
    male_score = sum(1 for kw in MALE_TAXONOMY_KWS if kw in combined)
    
    if female_score > male_score:
        return '女性向'
    elif male_score > female_score:
        return '男性向'
    else:
        return '均衡'

def extract_top_comments(note_id, count=10):
    """Extract top comments for a note using query-note-clinic."""
    out, code = run_cmd([
        'bash', COMMENT_SCRIPT,
        '--action', 'comments',
        '--note-id', note_id,
        '--comment-order', '1',  # APP default (hot sort)
        '--page-num', '1',
        '--page-size', str(count)
    ], timeout=15)
    if code != 0 or not out:
        return []
    try:
        data = json.loads(out)
        comments = data.get('data', {}).get('comments', [])
        return [{
            'content': c.get('content', ''),
            'likeCount': c.get('like_count', 0),
            'userId': c.get('user_id', '')
        } for c in comments if c.get('content', '').strip()]
    except:
        return []


def detect_sprouts(games=None, verbose=True):
    if games is None:
        games = GAMES
    
    sprouts = []
    seen_nids = set()
    
    for game in games:
        if verbose:
            print(f"  {game}...", end=' ', flush=True)
        
        notes = search_notes(game, 'TIME', 200, 8)
        found = 0
        
        for n in notes:
            nid = n.get('note_id', '')
            if nid in seen_nids:
                continue
            seen_nids.add(nid)
            
            title = n.get('note_base_info', {}).get('title', '').strip()
            taxonomy = n.get('note_base_info', {}).get('taxonomy', '')
            
            if not title or '非公开' in title:
                continue
            
            # ── Taxonomy filter: must be gaming-related ──
            if not any(tf in taxonomy for tf in TAXONOMY_GAME_FILTER):
                continue
            
            counts = n.get('note_count_info', {})
            likes = counts.get('like_count', 0)
            comments = counts.get('comment_count', 0)
            
            if likes < 1:
                continue
            
            ratio = comments / likes
            
            # Check thresholds
            if ratio < MIN_COMMENT_TO_LIKE_RATIO and comments < MIN_COMMENT_COUNT:
                continue
            
            # Supply density check
            density = check_supply_density(title, game)
            
            tgi = infer_tgi(title, taxonomy)
            
            sprout = {
                'id': f'ds{len(sprouts)+1}',
                'title': title[:30],
                'game': game,
                'commentToLikeRatio': round(ratio, 2),
                'commentCount': comments,
                'likeCount': likes,
                'supplyDensity': density,
                'supplyGap': density < SUPPLY_GAP_THRESHOLD and density >= 0,
                'tgi': tgi,
                'sourceNoteId': nid,
                'sourceNoteTitle': title,
                'sourceNoteUrl': f'https://www.xiaohongshu.com/explore/{nid}',
                'taxonomy': taxonomy
            }
            sprouts.append(sprout)
            found += 1
        
        if verbose:
            print(f'{found} candidates')
    
    # Sort: highest comment-to-like ratio first
    sprouts.sort(key=lambda s: -s['commentToLikeRatio'])
    
    return sprouts[:15]


def enrich_sprouts(sprouts, comment_extract=True):
    """Enrich sprouts with comment text and topic summarization."""
    for s in sprouts:
        if comment_extract and s.get('sourceNoteId'):
            comments = extract_top_comments(s['sourceNoteId'], 10)
            s['topComments'] = comments
            # Simple topic signal from top comment content
            if comments:
                comment_texts = [c['content'][:60] for c in comments[:3]]
                s['commentSamples'] = comment_texts
    return sprouts
    if games is None:
        games = GAMES
    
    sprouts = []
    seen_nids = set()
    
    for game in games:
        if verbose:
            print(f"  {game}...", end=' ', flush=True)
        
        notes = search_notes(game, 'TIME', 200, 8)
        found = 0
        
        for n in notes:
            nid = n.get('note_id', '')
            if nid in seen_nids:
                continue
            seen_nids.add(nid)
            
            title = n.get('note_base_info', {}).get('title', '').strip()
            taxonomy = n.get('note_base_info', {}).get('taxonomy', '')
            
            if not title or '非公开' in title:
                continue
            
            counts = n.get('note_count_info', {})
            likes = counts.get('like_count', 0)
            comments = counts.get('comment_count', 0)
            
            if likes < 1:
                continue
            
            ratio = comments / likes
            
            # ── Taxonomy filter: must be gaming ──
            if not any(tf in taxonomy for tf in TAXONOMY_GAME_FILTER):
                continue
            if ratio < MIN_COMMENT_TO_LIKE_RATIO and comments < MIN_COMMENT_COUNT:
                continue
            
            # Supply density check
            density = check_supply_density(title, game)
            
            tgi = infer_tgi(title, taxonomy)
            
            sprout = {
                'id': f'ds{len(sprouts)+1}',
                'title': title[:30],
                'game': game,
                'commentToLikeRatio': round(ratio, 2),
                'commentCount': comments,
                'likeCount': likes,
                'supplyDensity': density,
                'supplyGap': density < SUPPLY_GAP_THRESHOLD and density >= 0,
                'tgi': tgi,
                'sourceNoteId': nid,
                'sourceNoteTitle': title,
                'sourceNoteUrl': f'https://www.xiaohongshu.com/explore/{nid}',
                'taxonomy': taxonomy
            }
            sprouts.append(sprout)
            found += 1
        
        if verbose:
            print(f'{found} candidates')
    
    # Sort: supply gap first, then highest ratio
    sprouts.sort(key=lambda s: (-s['supplyGap'], -s['commentToLikeRatio']))
    
    return sprouts[:15]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--games', help='Comma-separated game list')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--no-comments', action='store_true', help='Skip comment extraction')
    args = parser.parse_args()
    
    games = args.games.split(',') if args.games else GAMES
    
    print(f"🔍 讨论苗头检测 | {len(games)} games | {datetime.now().isoformat()}")
    
    sprouts = detect_sprouts(games, verbose=True)
    
    print(f"\n  → {len(sprouts)} discussion sprouts detected")
    
    # Enrich with comment text
    if not args.no_comments:
        print("  Extracting comment text...")
        sprouts = enrich_sprouts(sprouts)
    
    has_comments = sum(1 for s in sprouts if s.get('topComments'))
    for s in sprouts[:10]:
        icon = '🔴' if s['supplyGap'] else '🟡'
        print(f"  {icon} [{s['tgi']}] {s['title']} | {s['commentCount']}评/{s['likeCount']}赞 r={s['commentToLikeRatio']} | supply={s['supplyDensity']}")
    
    if args.output:
        data = {'generated_at': datetime.now().isoformat(), 'sprouts': sprouts}
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Written to {args.output}")
    else:
        print(json.dumps({'sprouts': sprouts}, ensure_ascii=False, indent=2))