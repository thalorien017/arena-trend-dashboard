# 竞技游戏趋势看板 · Arena Trend Dashboard

> 运营自动化趋势发现工具 — 4 看板覆盖「该补什么 + 该追什么」

## 四个看板

| 看板 | 定位 | 数据源 |
|------|------|--------|
| 🔵 蓝海选题 | 站外火了但站内还没人做 → 抢第一波 | redhot-collector + Hive 供给密度 |
| 💬 讨论苗头 | 评论区炸了但没对应内容 → 隐藏需求 | search-notes 评论增速 + LLM 提炼 |
| 🔥 热点 | 已经在持续产出 → 持续关注 | redhot-xhs + redhot-agent |
| 🏆 赛事 | 当前电竞赛事一览 → 赛事运营 | 赛事关键词 + 站内外扫描 |

## 技术栈

- Vue 3 + Vite + TypeScript + Delight Design System
- 数据管线: Python (每6h自动刷新)
- 部署: GitHub Pages

## 覆盖游戏

14 款竞技游戏: 王者荣耀 / 和平精英 / 三角洲行动 / 金铲铲之战 / 英雄联盟 / 无畏契约 / 火影忍者 / PUBG / 暗区突围 / 永劫无间 / CSGO / 穿越火线：枪战王者 / DOTA2 / 王者万象棋

## 相关文档

- PRD: https://docs.xiaohongshu.com/doc/35bc82ef2a1244eb7b6b113cecf50e80
