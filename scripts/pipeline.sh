#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Arena Trend Dashboard — 数据管线协调器 v1
# 
# 每小时 cron 触发，并行启动各数据源，汇总后构建部署
# ═══════════════════════════════════════════════════════════════
set -e
_TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
echo "╔══ Arena Trend Pipeline — $_TIMESTAMP ══╗"

PROJECT="$(dirname "$0")/.."
cd "$PROJECT"

# ─── Step 1: 讨论苗头检测 (search-notes, 1-2 min) ───
echo "┌─ [1/5] 讨论苗头扫描 ────────┐"
SPROUT_SCRIPT="$(dirname "$0")/../skills/discussion-sprout/scripts/detect_sprouts.py"
if [ -f "$SPROUT_SCRIPT" ]; then
    timeout 180 python3 "$SPROUT_SCRIPT" --output public/discussion_sprouts.json \
        --min-comments 20 --min-ratio 0.08 2>/dev/null && {
        COUNT=$(python3 -c "import json; d=json.load(open('public/discussion_sprouts.json')); print(len(d))")
        echo "  ✅ 检测完成: $COUNT 条讨论苗头"
    } || echo "  ⚠️ 苗头检测超时，跳过"
else
    echo "  ⚠️ 苗头脚本不存在，跳过（P1 集成）"
fi

# ─── Step 2: Hive 评论批量查询 (2-5 min) ───
echo "┌─ [2/5] Hive 评论查询 ────────┐"
SPROUTS_FILE="public/discussion_sprouts.json"

if [ -f "$SPROUTS_FILE" ]; then
    python3 scripts/hive_comments.py "$SPROUTS_FILE" public/comments.json 2>&1 | tail -3
    echo "  ✅ 评论查询完成"
else
    echo "  ⏩ 无苗头数据，跳过"
fi

# ─── Step 3: Hive TGI 性别标签 (2-5 min) ───
echo "┌─ [3/5] Hive TGI 查询 ─────────┐"
if [ -f "$SPROUTS_FILE" ]; then
    python3 scripts/hive_tgi.py "$SPROUTS_FILE" 2>&1 | tail -3
    echo "  ✅ TGI 查询完成"
else
    echo "  ⏩ 跳过"
fi

# ─── Step 4: 汇总 → data.json ───
echo "┌─ [4/5] 数据汇总 ─────────────┐"
python3 scripts/assemble.py
echo "  ✅ data.json 生成完毕"

# ─── Step 5: 构建 + 部署 ───
echo "┌─ [5/5] 构建部署 ─────────────┐"

# 安装依赖（如需要）
[ -d node_modules ] || pnpm install --registry=http://npm.devops.xiaohongshu.com:7001 2>/dev/null

pnpm exec vite build 2>&1 | tail -2

# 部署到 GitHub Pages
if [ -n "$GH_TOKEN" ]; then
    rm -rf docs
    cp -r dist docs
    git add -A
    git commit -m "data refresh: $_TIMESTAMP" 2>/dev/null || true
    git push origin main 2>&1 | tail -2
    echo "  ✅ 已部署: https://thalorien017.github.io/arena-trend-dashboard/"
else
    echo "  ⚠️ GH_TOKEN 未配置，跳过 Git push"
    echo "  dist/ 目录已构建，可手动部署"
fi

echo "╚══ Pipeline 完成 — $(date '+%H:%M') ══╝"