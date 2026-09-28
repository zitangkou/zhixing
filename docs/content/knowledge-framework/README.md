# 知识框架 Markdown 存档

来源：旧库 `zhengkao-tong/server/data/zhengkao.db`（只读导出）。

重导出命令：

```bash
python3 scripts/knowledge_export_from_legacy.py --merge-unique-shenlun-tixing --also-runtime --verify
```

规范见桌面方案《杜衡阁_知识框架思维导图_优化方案_20260929.md》§3.4。

决策（2026-09-29）：

- 删除独立树「申论题型」，其独有子树（作答流程、倡议书等）已合并进「申论」
- 同级重复标题「动宾结构：…」只保留一条
- 删除空分支「言语理解与表达 / 文章阅读」
- 深度按父子关系重算（修复资料分析 17 处 depth 错位）
