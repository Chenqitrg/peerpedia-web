# Changelog

PeerPedia 遵循[语义版本](https://semver.org/lang/zh-CN/)。0.x 阶段 API 不稳定，每个次版本号代表一个里程碑。

## [0.2.4] — 2026-06-16

架构文档 + 安全审计。

- 四份学习文档（系统地图、core、backend、frontend）
- Git Bundle 同步协议文档
- 发现并记录 7 个架构/安全问题（#85–#92）
- Codecov 94% 覆盖率门禁
- Pre-commit hooks（ruff check + format）
- 版本号从 0.3.0 降回 0.2.4（诚实反映成熟度）

## [0.2.3] — 2026-06

发现 commit hash 安全漏洞。

- 认识到 Git `--author` 可任意伪造
- 评审数据存在作者控制的仓库里，缺少文件级别权限
- 设计 commit GPG 签名方案（#92）

## [0.2.2] — 2026-06

Git bundle "电话模型"同步。

- Pull-before-push 协议
- Hash 一致性保证（客户端和服务器同一份 hash）
- `useAutoSync` + `pushRepo` 离线队列

## [0.2.1] — 2026-06

线上/线下共存。

- Tauri 离线编辑 + 联网同步
- `useDraftPersistence` 双模式 abstraction
- Policy layer 统一权限检查

## [0.2.0] — 2026-06

第一个可运行的版本。

- Tauri 桌面端：本地 Git 写作、离线 Markdown/Typst 编辑
- FastAPI 服务器：REST API + SQLite 缓存
- 五维评分 + 沉淀池 → 发布流程
- Git 作为 Source of Truth，数据库作为缓存/索引
