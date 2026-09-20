---
feature: deskcomm-unique-integrate
status: in-progress
updated: 2026-09-20
branch: feat/deskcomm-unique-integrate
commits: 
---

# Deskcomm 不重叠能力深度并入优丁（智能取舍）

## Report

## [S1] Problem
主理人要求：DeskcommCRM 与优丁/GoodJob **重叠的能力不再引入**；**不重叠能力全部并入并深度整合**；代码/性能有差异时**智能判断取舍**。Deskcomm 是 Next.js+Supabase 的巴西「AI 销售 OS」，与优丁技术栈/硬锁（唯一 `/login`、Hermes 调度主权、PG 真相、SYSTEM-LOCK-02）冲突时不能整仓照搬。

## [S2] Design

### 取舍总原则（智能判断）
1. **能力并入，不并第二运行时**：吸收行为/契约/数据形状，落在优丁 Python 服务 + Hermes/UJ API；**不**并入 Next.js/Supabase/RLS/HostGator 安装器。
2. **重叠即复用**：已有 GoodJob/TradeAI/UJ 能力处只做桥接与契约对齐，禁止平行实现第二套 CRM/WhatsApp。
3. **求真**：无 AI Key/无外发时诚实 degraded/failed；Agent 操作必须审计；禁止假 lead/假 sent。
4. **硬锁优先**：LOGIN-LOCK、ROLE-SHELL、DESIGN-TOKEN、SYSTEM-LOCK-02、Hermes 任务面主权不可破。

### 能力矩阵（核心）

| Deskcomm 能力 | 与优丁/GoodJob | 取舍 | 落点 |
|---------------|----------------|------|------|
| 客户/商机/跟进基础 CRM | 重叠 GoodJob/UJ | **不引入** | 继续 GoodJob 功能域 |
| WhatsApp 收发基础 | 重叠插件/TradeAI | **不引入第二栈** | GoodJob plugin + TradeAI 适配 |
| 多租户 Auth / 自托管安装器 | 重叠 UJ | **不引入** | 唯一 `/login` + 现有部署 |
| Nuvemshop / 巴西电商 | 非主链 | **舍** | 不进优丁主叙事 |
| **MCP 操作 CRM（tools）** | 不重叠 | **并入** | `crm_sales_os` MCP 工具 + Hermes MCP manifest |
| **AI Agent 一等 assignee** | 不重叠 | **并入** | sales_task/inquiry 可 `agent:*` + 预算闸 + handoff 审计 |
| **自动化 QUANDO/IF/THEN** | 不重叠 | **并入** | `automation_rules` 评估器 → 派 Hermes/销售任务 |
| **Pipeline 词汇可配** | 不重叠 | **并入** | 租户 pipeline_vocabulary 配置 |
| **对话闭环 → RAG 飞轮** | 部分重叠 knowledge_queue | **并入钩子** | resolved 会话写入知识队列（诚实 pending） |
| **WhatsApp STOP→人接手** | 不重叠 | **并入** | TradeAI/触达路径 STOP 检测 → handoff 任务 |
| **租户级 AI budget** | 部分 ai_usage | **并入闸** | Agent 动作前 `agent_budget.allow` |
| LGPD redact/export | 不完全同构 | **P1 文档/复用审计** | 先接 append-only 审计，法务流程后置 |
| 分数索引 Kanban / 情感 worker / 多号反封 | 不重叠但工程重 | **P2** | 规格登记，本轮不实现 UI 全量 |

### 本轮代码契约
- `app/services/deskcomm/capability_matrix.py`：矩阵真相源（唯一列表，测试锁定）。
- `app/services/deskcomm/crm_sales_os_tools.py`：MCP 工具集——`inquiry.list` `sales_task.create` `sales_task.assign` `followup.schedule` `pipeline.get/set_vocabulary` `agent.handoff_note`；只读/写优丁 PG，**不**调 Deskcomm。
- `app/services/deskcomm/agent_assignee.py`：`normalize_assignee`（`user:` / `agent:`）；`agent_budget.allow(tenant)`；`record_agent_action` 审计。
- `app/services/deskcomm/automation_rules.py`：规则 `when(event)+if(cond)+then(action)`；动作 ∈ {create_sales_task, hermes_intent, handoff}；评估失败不静默。
- `app/services/deskcomm/stop_handoff.py`：文本 STOP/unsubscribe → `handoff` 结果，不自动外发。
- `app/services/deskcomm/pipeline_vocabulary.py`：默认建材外贸阶段 + 租户覆盖。
- API：`/api/v1/deskcomm-bridge/*`（矩阵、工具清单、规则 CRUD/试运行、vocabulary）。
- Hermes MCP：`get_tool_manifest` 追加 crm tools 的 schema 摘要；`call_tool` 路由到 crm 工具（有 db 才写）。

### 测试
- 矩阵：重叠项 `introduce=False`；unique 项 `introduce=True`。
- 预算闸：超额 → allow=False + reason。
- 自动化：匹配规则 → 产出 sales_task/hermes 意图（可 mock dispatch）。
- STOP：`stop`/`退订` → handoff=True，且 `sent=False`。

## [S3] Out of Scope
- 整仓拷贝 Deskcomm Next/Supabase/前端；
- Nuvemshop、HostGator kit、葡萄牙语全站；
- 真实多号 WAHA 反封运营面板（P2）；
- LGPD 完整法务工单流（P1 后）；
- 远端 push（Finish 另定）。

## Tasks
- [ ] T1: 能力矩阵 + 取舍文档化 — acceptance: capability_matrix 可导入且测试锁定重叠/不引入项（covers: S2）
- [ ] T2: CRM MCP 工具 + Hermes manifest 桥 — acceptance: 工具清单可查；list/create 在 db 可用时真读写；无 db 诚实 not_configured（covers: S2）
- [ ] T3: Agent assignee + budget + 审计 — acceptance: agent:* 归一化；超额拒绝；动作落审计（covers: S2）
- [ ] T4: 自动化规则引擎 — acceptance: CRUD + 试运行；命中则创建销售任务/hermes 意图（covers: S2）
- [ ] T5: STOP handoff + pipeline 词汇 — acceptance: STOP→handoff 不外发；vocabulary get/set（covers: S2）
- [ ] T6: API 挂载 + pytest + 假交付扫描 — acceptance: 路由可探；pytest 绿；validate-no-fake-delivery P0=0（covers: S2）
- [ ] T7: Review + Finalize — acceptance: 无 critical；spec delivered（covers: S2; depends: T1–T6）
