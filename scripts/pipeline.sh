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

# ═══ Step 1-4: 四看板并行检测 ═══
echo "┌─ [1/6] 讨论苗头扫描 ────────┐"
SPROUT_SCRIPT="$(dirname "$0")/../skills/discussion-sprout/scripts/detect_sprouts.py"
if [ -f "$SPROUT_SCRIPT" ]; then
    timeout 180 python3 "$SPROUT_SCRIPT" --output public/discussion_sprouts.json 2>/dev/null && \
        echo "  ✅ 讨论苗头完成" || echo "  ⚠️ 苗头超时"
fi

echo "┌─ [2/6] 蓝海选题检测 ────────┐"
timeout 180 python3 scripts/detect_blue_ocean.py public/blue_ocean.json 2>/dev/null && \
    echo "  ✅ 蓝海完成" || echo "  ⚠️ 蓝海超时（P1已知）"

echo "┌─ [3/6] 热点看板检测 ────────┐"
timeout 120 python3 scripts/detect_hotspots.py public/hotspots.json 2>/dev/null && \
    echo "  ✅ 热点完成" || echo "  ⚠️ 热点超时"

echo "┌─ [4/6] 赛事中心检测 ────────┐"
timeout 120 python3 scripts/detect_esports.py public/esports.json 2>/dev/null && \
    echo "  ✅ 赛事完成" || echo "  ⚠️ 赛事超时"

# ─── Step 5: 汇总 → data.json ───
echo "┌─ [5/6] 数据汇总 ─────────────┐"
python3 scripts/assemble.py

# ─── Step 6: 构建 + 部署 ───
echo "┌─ [6/6] 构建部署 ─────────────┐"

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