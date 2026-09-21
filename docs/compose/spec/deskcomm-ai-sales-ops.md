---
feature: deskcomm-ai-sales-ops
status: in-progress
updated: 2026-09-20
branch: feat/deskcomm-ai-sales-ops
commits: 
---

# Deskcomm 非重叠能力并入优丁（AI Sales Ops）

## Report

## [S1] Problem
DeskcommCRM 与 GoodJob/优丁在客户、漏斗、WhatsApp 收发、跟进提醒上**功能重叠**；但 Deskcomm 独有一层 **AI 销售操作面**（资格门禁、handoff 闸门、AI 预算、STOP/反封、知识飞轮、事件日志工作流、pipeline 词汇表）。主理人要求：**重叠去掉，不重叠全部并入并深度整合**；代码/性能有差异时智能取舍。

## [S2] Design

### 智能取舍（明确）

| Deskcomm 能力 | 裁决 | 理由 |
|---------------|------|------|
| 客户/商机/跟进/看板/导入导出 | **丢弃（重叠）** | GoodJob + 优丁询盘/销售任务已有；不再叠第二套 CRM UI |
| WhatsApp 收发会话 UI | **丢弃（重叠）** | GoodJob whatsapp-plugin / TradeAI 已有通道；优丁只吸收**守卫与策略** |
| Next.js + Supabase + HostGator 安装包 | **丢弃** | 技术栈冲突；优丁真相=FastAPI+PG |
| 独立 Auth / 多租户 SaaS 壳 | **丢弃** | 破 LOGIN-LOCK / 双产品壳 |
| Nuvemshop 电商、LGPD 全套 | **丢弃/降级** | 非建材外贸主链；隐私导出降级为租户数据请求接口（PIPL 向） |
| **AI 资格门禁 elegibilidade** | **并入** | WhatsApp AI 是否应接管会话；优丁缺统一 deny/open 规则 |
| **Handoff 闸门 G1–G4** | **并入** | 关键词/情感/低置信/阶段强制人工；优丁仅有零散 handoff_history |
| **AI 预算 / 熔断** | **并入（接 wallet_guard）** | 复用 token_ledger，不另建第二账本 |
| **STOP 检测 + 出站节流** | **并入** | 拓客外发合规硬需求；TradeAI 缺统一闸 |
| **知识飞轮**（解决会话→知识） | **并入** | 挂 acquisition knowledge_queue + experience |
| **事件日志 + worker 契约** | **并入（轻量）** | `ai_sales_events` 表 + 处理器钩子，Postgres trigger 不做 HTTP |
| **Pipeline 词汇表** | **并入** | 多场景阶段中文标签，不改表结构默认值 |
| **MCP 全量 CRM tools** | **部分并入** | 优丁已有 MCP 基建；新增 ai_sales_ops tools，不复制 Deskcomm 全表 |

### 架构落点（优丁）
```
WhatsApp/社媒 inbound
  → ai_sales_ops.eligibility（deny/open/allowlist）
  → handoff_triggers.evaluate（G1–G4）
  → wallet_guard + ai_budget.check（硬拦诚实）
  → 通过才允许 agent/Hermes 执行回复或触达
  → outbound 前 whatsapp_guard（STOP + throttle）
  → 事件写入 ai_sales_events → worker/flywheel
```

### 模块契约
- `services/ai_sales_ops/eligibility.py`：纯函数 `decide_eligibility(state) -> {allowed, reason}`；`open|allowlist`；force_human / bot_silenced / assignee=user → 拒绝。
- `handoff_triggers.py`：`G1` 用户要人工（中英）；`G2` 情感分低于阈值；`G3` 置信度低或不确定话术；`G4` 阶段 requires_human / 法务词。
- `ai_budget.py`：`check_ai_budget(tenant_id)` → 调 `wallet_guard`；可选月消耗上限 `AI_SALES_MONTHLY_TOKEN_CAP`；超限 `blocked=true` 不编造余额。
- `whatsapp_guard.py`：STOP/退订关键词 → `suppress`；`throttle_outbound` 固定窗口限速。
- `knowledge_flywheel.py`：`record_resolved_conversation` → knowledge_queue 待办（诚实 pending）。
- `event_log.py`：`append_ai_sales_event` 幂等 `event_key`。
- `pipeline_vocab.py`：默认中英阶段词表，租户可覆盖。
- API：`/api/v1/ai-sales-ops/eligibility|handoff|budget|guard|flywheel|vocab|events`（JWT）。
- Hermes：executor `ai_sales_ops`，capability：`eligibility.check` / `handoff.evaluate` / `budget.check` / `guard.outbound` / `flywheel.resolved`。
- MCP：在既有 Agent Hub 工具目录追加 `ai_sales_ops.*`（不复制 Deskcomm Next 路由）。

### 性能取舍
- 资格/handoff/STOP 为**纯函数 + 本地常量**，单次 <1ms，不先打 LLM。
- 情感 G2：无外部情感模型时诚实 `degraded`（不假打分）；有配置再接。
- 预算只读 ledger，不写第二余额表。

### 硬锁
- 不新建登录；不改薄荷主色；不引入第二 SaaS 壳；SYSTEM-LOCK 仍含 GoodJob/TradeAI。

## [S3] Out of Scope
- 整仓复制 Deskcomm Next/Supabase/HostGator；
- 替换 GoodJob/TradeAI 主 UI；
- 生产 WhatsApp 真实群发联调（需通道 Key）；
- 全量 166 路 CRM MCP 对等实现。

## Tasks
- [ ] T1: Spec + 取舍表 — acceptance: 本文档（covers: S2）
- [ ] T2: ai_sales_ops 服务包（eligibility/handoff/budget/guard/flywheel/event/vocab） — acceptance: 纯函数单测绿（covers: S2）
- [ ] T3: API 路由 + Hermes executor — acceptance: 路由可鉴权访问；executor 能力注册（covers: S2; depends: T2）
- [ ] T4: MCP 工具目录挂接 — acceptance: agent_hub catalog 含 ai_sales_ops（covers: S2; depends: T3）
- [ ] T5: Verify + Review + Finalize — acceptance: pytest/typecheck/live；spec delivered（covers: S2; depends: T1–T4）
