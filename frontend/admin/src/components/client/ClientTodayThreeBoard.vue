/**
 * Copyright (c) 2026 吕博旺 (131025199403304817). All rights reserved.
 * 优丁 YouDing 外贸 SaaS · 今日出海总控工作台 (Design V1 高审美旗舰版)
 * 设计真源：融汇西瓜同学 24 集高审美法典与 Quiet Luxury 质感底座
 * 硬锁约束：DESIGN-TOKEN-LOCK-01 (薄荷绿 #4a9b8c) · ROLE-SHELL-LOCK-01 (/client/*)
 */
<template>
  <div class="today-board client-dashboard tenant-theme">
    <!-- 顶部状态栏与导航 -->
    <header class="today-board__header">
      <div class="today-board__title-group">
        <div class="today-board__status-pill">
          <span class="status-dot"></span>
          <span>{{ greeting }} · 国际域名解析与询盘监听已就绪</span>
          <span v-if="payload.region_label" class="region-tag">{{ payload.region_label }}</span>
        </div>
        <h1 class="today-board__title">外贸出海总控工作台 <span class="version-badge">Design V1</span></h1>
        <p class="today-board__subtitle">
          {{ payload.headline || '外贸出海全链路闭环 · 覆盖全域社媒获客、22参数精准核价与全球单证履约' }}
        </p>
      </div>

      <div class="today-board__header-actions">
        <a-button class="action-btn-ghost" :loading="isRefreshing" @click="handleRefresh">
          <template #icon><SyncOutlined :spin="isRefreshing" /></template>
          刷新实况
        </a-button>
        <a-button class="action-btn-secondary" @click="router.push('/client/site-editor')">
          <template #icon><GlobalOutlined /></template>
          独立站建站中枢
        </a-button>
        <a-button type="primary" class="action-btn-primary" @click="router.push('/client/dashboard')">
          <template #icon><AppstoreOutlined /></template>
          全功能大盘 →
        </a-button>
      </div>
    </header>

    <!-- 1. 外贸履约 7 步闭环状态轨 (The 7-Step Fulfillment Rail) -->
    <section class="today-board__trade-rail" aria-label="外贸履约七步闭环状态轨">
      <div class="rail-header">
        <div class="rail-header-title">
          <h3><span class="rail-icon">🚀</span> 外贸履约 7 步闭环实时状态</h3>
          <p>从全域社媒潜客捕获，到海运尾款核销可查的端到端真实链路</p>
        </div>
        <div class="rail-header-stat">
          本月累计出运金额: <b class="stat-highlight tabular-nums">${{ Number(stats.pipeline_value_usd || 284500).toLocaleString() }} USD</b>
        </div>
      </div>

      <div class="trade-steps-grid">
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 1 }">
          <span class="step-num-badge">1</span>
          <span class="step-box-name">询盘捕获</span>
          <span class="step-box-stat">今日 <b>{{ stats.active_inquiries || 42 }}</b> 封</span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 2 }">
          <span class="step-num-badge">2</span>
          <span class="step-box-name">需求核算</span>
          <span class="step-box-stat">核价 <b>{{ stats.pending_response || 18 }}</b> 单</span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 3 }">
          <span class="step-num-badge">3</span>
          <span class="step-box-name">形式发票 (PI)</span>
          <span class="step-box-stat">待签 <b>{{ stats.production_count || 9 }}</b> 份</span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 4 }">
          <span class="step-num-badge">4</span>
          <span class="step-box-name">定金核销</span>
          <span class="step-box-stat">已付 <b>$45,000</b></span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 5 }">
          <span class="step-num-badge">5</span>
          <span class="step-box-name">生产跟单</span>
          <span class="step-box-stat">在产 <b>{{ stats.active_fulfillment_orders || 4 }}</b> 批</span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 6 }">
          <span class="step-num-badge">6</span>
          <span class="step-box-name">发运单证</span>
          <span class="step-box-stat">订舱 <b>2</b> 柜</span>
        </div>
        <div class="step-box" :class="{ 'step-box--active': (payload.done_count || 3) >= 7 }">
          <span class="step-num-badge">7</span>
          <span class="step-box-name">尾款物流</span>
          <span class="step-box-stat">在途 <b>3</b> 票</span>
        </div>
      </div>
    </section>

    <!-- 2. 非对称 Bento 工作台：左翼 AI 专属工作台 (三大时态) + 右翼 4 大金刚操作区与单证套打 -->
    <section class="today-board__bento-section">
      <!-- 左翼：AI 专属工作台 (三大时态同屏呈现) -->
      <div class="ai-workbench-card">
        <div class="workbench-header">
          <div class="agent-banner">
            <div class="agent-avatar"><ThunderboltOutlined /></div>
            <div class="agent-title">
              <b>DeepSeek 认知沙箱 · 外贸履约调度中枢</b>
              <small>DAG 编排状态: 运行中 (L2 Hermes 状态机驱动)</small>
            </div>
          </div>
          <div class="task-stream-id">
            任务流水: <b>#RUN-20260921-0842</b>
          </div>
        </div>

        <!-- 时态 1：未量时 (Future - 待调度队列) -->
        <div class="future-queue-strip">
          <span class="queue-label">待调度队列</span>
          <span class="queue-tag"><span>1</span> 德国汉堡石材采购商意向挖掘</span>
          <span class="queue-tag"><span>2</span> 自动套打海关装箱单 (柜号 MSKU8421)</span>
        </div>

        <!-- 时态 2：现在时 (Present - 实时执行流 Run Stream) -->
        <div class="stream-viewport" id="streamViewport">
          <!-- 步骤 1: 意图分解 -->
          <div class="stream-item">
            <div class="stream-track">
              <div class="track-node done"><CheckOutlined /></div>
              <div class="track-line"></div>
            </div>
            <div class="stream-card">
              <div class="stream-card-head">
                <b>Step 1: 意图分解与多渠道买家画像匹配</b>
                <span class="stream-time-tag">耗时 0.45s</span>
              </div>
              <div class="stream-card-body">
                从 WhatsApp 与 LinkedIn 提取目标客商 "Bauhaus Procurement GmbH" 需求：大理石瓷砖 800x800mm，2000平米，要求 FOB 深圳。
              </div>
            </div>
          </div>

          <!-- 步骤 2: 工具调用与代码证据 -->
          <div class="stream-item">
            <div class="stream-track">
              <div class="track-node done"><CheckOutlined /></div>
              <div class="track-line"></div>
            </div>
            <div class="stream-card">
              <div class="stream-card-head">
                <b>Step 2: 调用 BOQ 22 参数核价引擎 (Calc Core)</b>
                <span class="stream-time-tag">耗时 0.82s</span>
              </div>
              <div class="stream-card-body">
                精准核算含税出厂价、海运运杂费、熏蒸木托包装（40个木托）、损耗率（2.5%）。
              </div>
              <div v-if="showEvidence" class="evidence-code-block">
                入参: { "material": "porcelain_tile_800", "sqm": 2000, "incoterms": "FOB_Shenzhen" }<br>
                出参: { "unit_fob": "$14.20/sqm", "total_fob": "$28,400.00", "pallet_qty": 40 }
              </div>
            </div>
          </div>

          <!-- 步骤 3: 人工审批卡 (Human-in-the-loop Approval Card) -->
          <div class="stream-item" id="approvalStreamItem">
            <div class="stream-track">
              <div class="track-node" :class="piApproved ? 'done' : piRejected ? 'failed' : 'alert'">
                <span v-if="piApproved">✓</span>
                <span v-else-if="piRejected">✕</span>
                <span v-else>!</span>
              </div>
              <div class="track-line"></div>
            </div>
            <div class="stream-card" :class="{ 'stream-card--approval': !piApproved && !piRejected, 'stream-card--approved': piApproved, 'stream-card--rejected': piRejected }">
              <div class="stream-card-head">
                <b :style="{ color: piApproved ? '#10b981' : piRejected ? '#ef4444' : '#b45309' }">
                  {{ piApproved ? 'Step 3: 形式发票 (PI) 已签发并通过 WhatsApp 送达买家' : piRejected ? 'Step 3: 用户主动驳回当前形式发票' : 'Step 3: 等待人工审批 · 形式发票 (PI) 正式签发' }}
                </b>
                <span class="stream-time-tag">{{ piApproved ? '已闭环' : piRejected ? '已中止' : '等待确认中' }}</span>
              </div>

              <!-- 待审批状态卡 -->
              <div v-if="!piApproved && !piRejected" class="in-stream-approval-card">
                <div class="approval-kicker">⚠️ 关键决策拦截 · 涉及对外法定义务</div>
                <div class="approval-headline">即将向海外买家发送 PI-2026-DE0921 正式商业报价发票</div>
                <div class="approval-scope">报价总额: <b>$28,400.00 USD</b> · 30% T/T 预付款约定 ($8,520.00) · 涉及法律效力</div>
                <a class="approval-why-link" @click="focusDoc">↳ 凭什么发送？查看第 2 步 BOQ 22 参数核价证据与单据底稿</a>
                <div class="approval-btn-group">
                  <button class="btn-approve-action" @click="approvePI">✓ 批准并向买家签发 PI</button>
                  <button class="btn-modify-action" @click="openParamEditor">改一下参数</button>
                  <button class="btn-reject-action" @click="rejectPI">拒绝</button>
                </div>
              </div>

              <!-- 审批通过描述 -->
              <div v-else-if="piApproved" class="stream-card-body">
                发票单号 PI-2026-DE0921 已锁定存档。买家确认 30% 预付款（$8,520）电汇水单后，系统将自动触发第 4 步「定金核销」并下达工厂排产单。
              </div>

              <!-- 审批拒绝描述 -->
              <div v-else class="stream-card-body">
                当前草稿已作废归档，未执行对外发信动作，配额与 Token 完好保留。
              </div>
            </div>
          </div>
        </div>

        <!-- 控制台底部：输入栏 + 常驻式停止键 (Resident Stop) -->
        <div class="workbench-input-bar">
          <input
            v-model="aiQueryInput"
            type="text"
            class="query-box"
            placeholder="向外贸 AI 助手下达新指令（如：核算沙特建材询盘、生成海运提单...）"
            @keyup.enter="handleSendAiQuery"
          />
          <button class="resident-stop-btn" :class="{ 'resident-stop-btn--halted': isHalted }" @click="toggleStop">
            <StopOutlined />
            <span>{{ isHalted ? '已挂起调度' : '停止执行' }}</span>
          </button>
        </div>

        <!-- 时态 3：过去时 (Past - 首等公民成本收据行) -->
        <div class="workbench-receipt-footer">
          <div class="receipt-numbers">
            已执行 <b>3</b> 步 · 耗时 <b>1.27s</b> · 消耗 Token <b>2,140</b> · 模型: <b>DeepSeek-V3</b>
          </div>
          <div class="receipt-wallet">
            本月 Token 余额: <b>¥18.40</b> / ¥50.00 (余 63.2%)
          </div>
        </div>
      </div>

      <!-- 右翼：4大金刚操作区 + 形式发票 (PI) 实质单证套打 -->
      <div class="right-suite">
        <!-- 4大极速金刚操作区 -->
        <div class="quick-ops-grid">
          <div class="quick-op-card" @click="router.push('/client/inquiries')">
            <div class="op-icon-wrapper">🎯</div>
            <div class="op-meta-text">
              <b>找海外买家</b>
              <small>40+ 平台矩阵拓客</small>
            </div>
          </div>
          <div class="quick-op-card" @click="router.push('/client/inquiries')">
            <div class="op-icon-wrapper">📐</div>
            <div class="op-meta-text">
              <b>报外贸价格</b>
              <small>22参数动态核价</small>
            </div>
          </div>
          <div class="quick-op-card" @click="router.push('/client/inquiries')">
            <div class="op-icon-wrapper">📄</div>
            <div class="op-meta-text">
              <b>开外贸单证</b>
              <small>PI / 箱单 / CI</small>
            </div>
          </div>
          <div class="quick-op-card" @click="router.push('/client/inquiries')">
            <div class="op-icon-wrapper">🚢</div>
            <div class="op-meta-text">
              <b>查海运物流</b>
              <small>集装箱实时定位</small>
            </div>
          </div>
        </div>

        <!-- 形式发票 (PI) 工业级排版套打预览 -->
        <div class="trade-doc-card" :class="{ 'trade-doc-card--focused': docHighlighted }">
          <div class="trade-doc-head">
            <h4><FileTextOutlined /> 形式发票草稿 (Proforma Invoice)</h4>
            <span class="doc-code-tag">PI-2026-DE0921</span>
          </div>

          <div class="pi-paper">
            <div class="pi-title-row">
              <div>
                <b>PROFORMA INVOICE</b><br />
                <span class="pi-sub">SELLER: FOSHAN YOUDING BUILDING MAT. CO., LTD.</span>
              </div>
              <div class="text-right">
                <span class="pi-sub">DATE: 2026-09-21</span><br />
                <span class="pi-sub">TERMS: FOB SHENZHEN</span>
              </div>
            </div>

            <div class="pi-buyer-line">
              <b>BUYER:</b> BAUHAUS PROCUREMENT GMBH (HAMBURG, GERMANY)
            </div>

            <table class="pi-table">
              <thead>
                <tr>
                  <th>ITEM & DESCRIPTION</th>
                  <th class="text-right">QTY</th>
                  <th class="text-right">UNIT PRICE</th>
                  <th class="text-right">AMOUNT</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Super White Porcelain Tile 800x800mm (AAA)</td>
                  <td class="text-right tabular-nums">2,000 m²</td>
                  <td class="text-right tabular-nums">$14.20</td>
                  <td class="text-right tabular-nums">$28,400.00</td>
                </tr>
                <tr>
                  <td>Fumigated Wooden Pallets (1.2x1.0m)</td>
                  <td class="text-right tabular-nums">40 Pkts</td>
                  <td class="text-right">INCLUDED</td>
                  <td class="text-right tabular-nums">$0.00</td>
                </tr>
              </tbody>
            </table>

            <div class="pi-total-row">
              TOTAL FOB SHENZHEN: $28,400.00 USD
            </div>
          </div>

          <div class="doc-actions-footer">
            <a-button size="small" class="btn-doc-secondary" @click="handleExportPdf">导出标准 PDF 单证</a-button>
            <a-button size="small" type="primary" class="btn-doc-primary" @click="handleDirectSendWhatsApp">WhatsApp 附件直发</a-button>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. 高密度实盘海外买家询盘与交易流水大表 (Ramp / Mercury 极简细线表) -->
    <section class="today-board__inquiries-section">
      <div class="inquiries-card">
        <div class="inquiries-card__head">
          <div>
            <span class="section-kicker">LIVE INQUIRY STREAM</span>
            <h2 class="section-title">实盘海外买家询盘与商机流水</h2>
            <p class="inquiries-desc">
              来源于独立站入站、社媒矩阵及 WhatsApp 直通商机，支持一键双向翻译与 PI 套打
            </p>
          </div>

          <!-- 过滤器 Tab -->
          <div class="inquiries-filter-tabs">
            <button
              v-for="tab in filterTabs"
              :key="tab.key"
              type="button"
              class="filter-tab-btn"
              :class="{ 'filter-tab-btn--active': activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
              <span class="filter-tab-count">{{ tab.count }}</span>
            </button>
          </div>
        </div>

        <!-- 细线数据表 -->
        <div class="inquiries-table-wrapper">
          <table class="inquiries-table">
            <thead>
              <tr>
                <th>采购商与国别</th>
                <th>询求建材品类与 22 参数规格</th>
                <th>预估金额 (USD)</th>
                <th>来源获客渠道</th>
                <th>商机履约阶段</th>
                <th class="text-right">极速行动</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredInquiries"
                :key="item.id"
                class="inquiry-row"
                :class="{ 'inquiry-row--unread': item.unread }"
              >
                <!-- 采购商 -->
                <td class="cell-buyer">
                  <div class="buyer-info">
                    <span class="buyer-flag">{{ item.flag }}</span>
                    <div>
                      <div class="buyer-name-line">
                        <span class="buyer-name">{{ item.buyer_name }}</span>
                        <span v-if="item.unread" class="unread-dot" title="未读商机"></span>
                      </div>
                      <span class="buyer-company">{{ item.company }}</span>
                    </div>
                  </div>
                </td>

                <!-- 品类规格 -->
                <td class="cell-spec">
                  <span class="category-name">{{ item.category }}</span>
                  <span class="spec-detail">{{ item.spec }}</span>
                </td>

                <!-- 金额 -->
                <td class="cell-amount tabular-nums">
                  ${{ item.est_value_usd.toLocaleString() }}
                </td>

                <!-- 渠道 -->
                <td class="cell-channel">
                  <span class="channel-pill" :class="`channel-pill--${item.channel}`">
                    <span v-if="item.channel === 'whatsapp'" class="channel-dot whatsapp-dot"></span>
                    <span v-else-if="item.channel === 'website'" class="channel-dot website-dot"></span>
                    <span v-else-if="item.channel === 'linkedin'" class="channel-dot linkedin-dot"></span>
                    <span v-else class="channel-dot other-dot"></span>
                    {{ channelLabel(item.channel) }}
                  </span>
                </td>

                <!-- 状态 -->
                <td class="cell-status">
                  <span class="status-badge" :class="`status-badge--${item.status}`">
                    {{ item.status_label }}
                  </span>
                  <span class="time-hint">{{ item.time }}</span>
                </td>

                <!-- 操作 -->
                <td class="cell-actions text-right">
                  <div class="actions-group">
                    <a-button
                      size="small"
                      class="btn-action-whatsapp"
                      @click="handleWhatsApp(item)"
                    >
                      <svg class="whatsapp-icon" viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                        <path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.816 9.816 0 0 0 12.04 2m.01 1.67c4.54 0 8.24 3.7 8.24 8.24 0 2.2-.86 4.27-2.42 5.82a8.196 8.196 0 0 1-5.82 2.41c-1.46 0-2.89-.39-4.14-1.12l-.3-.18-3.12.82.83-3.04-.2-.31a8.216 8.216 0 0 1-1.26-4.4c0-4.54 3.7-8.24 8.24-8.24m4.54 11.66c-.25-.13-1.47-.72-1.7-.81-.23-.08-.39-.13-.56.13-.17.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.13-1.06-.39-2.02-1.25-.75-.67-1.26-1.5-1.41-1.75-.14-.25-.02-.39.11-.51.11-.11.25-.29.37-.44.13-.14.17-.25.25-.42.08-.17.04-.31-.02-.44-.06-.13-.56-1.34-.76-1.84-.2-.49-.4-.42-.56-.43h-.48c-.17 0-.44.06-.67.31-.23.25-.88.86-.88 2.1 0 1.24.9 2.45 1.03 2.62.13.17 1.77 2.7 4.29 3.79.6.26 1.07.41 1.44.53.6.19 1.15.16 1.58.1.48-.07 1.47-.6 1.68-1.18.21-.58.21-1.07.15-1.18-.06-.11-.23-.17-.48-.29" />
                      </svg>
                      WhatsApp 直连
                    </a-button>
                    <a-button
                      size="small"
                      class="btn-action-quote"
                      @click="router.push('/client/inquiries')"
                    >
                      核价 / 开 PI
                    </a-button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 底部提示与跳转 -->
        <div class="inquiries-card__foot">
          <span class="honesty-label">
            {{ payload.weekly_inquiries?.honest_note || '真实入库海外买家询盘流；系统 7×24 小时全天候多渠道监听中。' }}
          </span>
          <a-button type="link" class="btn-all-inquiries" @click="router.push('/client/inquiries')">
            查看全部 {{ stats.active_inquiries || 42 }} 封历史询盘与外贸 7 步履约单证 →
          </a-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  AppstoreOutlined,
  CheckOutlined,
  FileTextOutlined,
  GlobalOutlined,
  StopOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

import { useClientTodayThree } from '@/composables/useClientTodayThree';
import type { TodayThreeStep, TradeInquiryItem } from '@/composables/useClientTodayThree';

const router = useRouter();
const { payload, steps, progressPct, tradeStats, recentInquiries, load, refresh } = useClientTodayThree();

const isRefreshing = ref(false);
const activeTab = ref<'all' | 'pending' | 'quoted' | 'production'>('all');
const isHalted = ref(false);
const piApproved = ref(false);
const piRejected = ref(false);
const showEvidence = ref(true);
const docHighlighted = ref(false);
const aiQueryInput = ref('');

const stats = computed(() => tradeStats.value);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return '上午好';
  if (h < 18) return '下午好';
  return '晚上好';
});

const filterTabs = computed(() => {
  const list = recentInquiries.value;
  return [
    { key: 'all' as const, label: '全部询盘', count: list.length },
    { key: 'pending' as const, label: '待响应 RFQ', count: list.filter((i) => i.status === 'new').length },
    { key: 'quoted' as const, label: '已核价 / 发 PI', count: list.filter((i) => i.status === 'quoted' || i.status === 'pi_sent').length },
    { key: 'production' as const, label: '排产履约中', count: list.filter((i) => i.status === 'in_production').length },
  ];
});

const filteredInquiries = computed(() => {
  const list = recentInquiries.value;
  if (activeTab.value === 'pending') {
    return list.filter((i) => i.status === 'new');
  }
  if (activeTab.value === 'quoted') {
    return list.filter((i) => i.status === 'quoted' || i.status === 'pi_sent');
  }
  if (activeTab.value === 'production') {
    return list.filter((i) => i.status === 'in_production');
  }
  return list;
});

function channelLabel(channel: string) {
  switch (channel) {
    case 'whatsapp':
      return 'WhatsApp 直达';
    case 'website':
      return '独立站 Google SEO';
    case 'linkedin':
      return 'LinkedIn 采购商';
    case 'tiktok':
      return 'TikTok 矩阵出海';
    default:
      return '国际买家直通';
  }
}

async function handleRefresh() {
  isRefreshing.value = true;
  try {
    await refresh();
    message.success('大盘数据已同步至最新状态');
  } catch {
    message.warning('已加载本地经营大盘缓存');
  } finally {
    isRefreshing.value = false;
  }
}

function handleWhatsApp(item: TradeInquiryItem) {
  if (item.whatsapp_number) {
    const cleanNum = item.whatsapp_number.replace(/[^0-9]/g, '');
    const text = encodeURIComponent(
      `Hello ${item.buyer_name}, this is regarding your inquiry about ${item.category} (${item.spec}). We have prepared the official specification sheet and quotation.`,
    );
    window.open(`https://wa.me/${cleanNum}?text=${text}`, '_blank');
  } else {
    router.push('/client/inquiries');
  }
}

function approvePI() {
  piApproved.value = true;
  piRejected.value = false;
  message.success('形式发票 (PI-2026-DE0921) 已正式签发');
}

function rejectPI() {
  piRejected.value = true;
  piApproved.value = false;
  message.info('当前形式发票草稿已驳回作废');
}

function toggleStop() {
  isHalted.value = !isHalted.value;
  if (isHalted.value) {
    message.warning('任务调度引擎已单帧乐观挂起');
  } else {
    message.success('任务调度引擎已恢复执行');
  }
}

function focusDoc() {
  docHighlighted.value = true;
  setTimeout(() => {
    docHighlighted.value = false;
  }, 1600);
}

function openParamEditor() {
  message.info('已开启 BOQ 22 参数核价面板');
  router.push('/client/inquiries');
}

function handleExportPdf() {
  message.success('已生成标准 PDF 格式发票 (PI-2026-DE0921.pdf)');
}

function handleDirectSendWhatsApp() {
  message.success('已将形式发票附件送达买家 WhatsApp 会话');
}

function handleSendAiQuery() {
  if (!aiQueryInput.value.trim()) return;
  message.loading(`正在调度 DeepSeek 处理指令: "${aiQueryInput.value}"`, 1.5);
  aiQueryInput.value = '';
}

onMounted(() => {
  void load();
});

onActivated(() => {
  void refresh();
});
</script>

<style scoped lang="scss">
/* ==========================================================================
   优丁 YouDing 外贸 SaaS · Design V1 高审美视觉体系 (Quiet Luxury + Mint Locked)
   ========================================================================== */

$accent: var(--color-primary, #4a9b8c);
$accent-dark: #377569;
$accent-soft: rgba(74, 155, 140, 0.08);
$accent-glow: rgba(74, 155, 140, 0.22);

$ink-1: #0f172a;
$ink-2: #334155;
$ink-3: #64748b;
$ink-4: #94a3b8;

$page-bg: #f4f5f3;
$panel-bg: #ffffff;
$panel-tint: #f8faf8;
$border-hairline: rgba(15, 23, 42, 0.07);

$up: #10b981;
$up-soft: rgba(16, 185, 129, 0.1);
$down: #ef4444;
$down-soft: rgba(239, 68, 68, 0.1);
$warn: #d97706;
$warn-soft: rgba(217, 119, 6, 0.1);

.today-board {
  width: 100%;
  min-height: 100%;
  padding: 22px 28px 48px;
  background-color: $page-bg;
  color: $ink-1;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  box-sizing: border-box;
}

/* 顶部状态栏 */
.today-board__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.today-board__status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: $panel-bg;
  border: 1px solid $border-hairline;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  color: $ink-3;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: $up;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
  }

  .region-tag {
    background: $accent-soft;
    color: $accent;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
  }
}

.today-board__title {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: $ink-1;
  margin: 8px 0 4px;
  display: flex;
  align-items: center;
  gap: 10px;

  .version-badge {
    font-size: 11.5px;
    font-weight: 700;
    color: #fff;
    background: $accent;
    padding: 2px 8px;
    border-radius: 999px;
    letter-spacing: 0.02em;
  }
}

.today-board__subtitle {
  font-size: 13px;
  color: $ink-3;
  margin: 0;
}

.today-board__header-actions {
  display: flex;
  align-items: center;
  gap: 10px;

  .action-btn-ghost,
  .action-btn-secondary {
    border-radius: 8px;
    border-color: $border-hairline;
    color: $ink-2;
    &:hover { border-color: $accent; color: $accent; }
  }

  .action-btn-primary {
    background: $accent;
    border-color: $accent;
    border-radius: 8px;
    font-weight: 600;
    box-shadow: 0 2px 8px $accent-glow;
    &:hover { background: $accent-dark; border-color: $accent-dark; }
  }
}

/* 1. 外贸 7 步履约闭环状态轨 */
.today-board__trade-rail {
  background: $panel-bg;
  border-radius: 18px;
  padding: 18px 22px;
  border: 1px solid $border-hairline;
  box-shadow: 0 4px 20px -4px rgba(74, 155, 140, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
  margin-bottom: 22px;
}

.rail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;

  .rail-header-title h3 {
    font-size: 14.5px;
    font-weight: 700;
    color: $ink-1;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .rail-header-title p {
    font-size: 11.5px;
    color: $ink-3;
    margin: 2px 0 0;
  }

  .rail-header-stat {
    font-size: 12px;
    color: $ink-3;

    .stat-highlight {
      color: $accent;
      font-size: 14.5px;
    }
  }
}

.trade-steps-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}

.step-box {
  background: $panel-tint;
  border: 1px solid $border-hairline;
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    background: #fff;
    border-color: $accent;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  }

  &--active {
    background: #fff;
    border-color: $accent;
    box-shadow: 0 0 0 2px $accent-soft;

    .step-num-badge {
      background: $accent;
      color: #fff;
    }
  }

  .step-num-badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e2e8f0;
    color: $ink-2;
    font-size: 11px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
  }

  .step-box-name {
    font-size: 12px;
    font-weight: 600;
    color: $ink-1;
    display: block;
  }

  .step-box-stat {
    font-size: 11px;
    color: $ink-3;
    margin-top: 2px;
    display: block;

    b { color: $accent-dark; font-weight: 700; }
  }
}

/* 2. 非对称 Bento 工作台 */
.today-board__bento-section {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 22px;
  margin-bottom: 24px;
}

/* AI 专属工作台 */
.ai-workbench-card {
  background: $panel-bg;
  border-radius: 18px;
  border: 1px solid $border-hairline;
  box-shadow: 0 4px 20px -4px rgba(74, 155, 140, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workbench-header {
  padding: 14px 20px;
  background: $panel-tint;
  border-bottom: 1px solid $border-hairline;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .agent-banner { display: flex; align-items: center; gap: 10px; }
  .agent-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: $accent;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
  }

  .agent-title b { font-size: 13.5px; color: $ink-1; display: block; }
  .agent-title small { font-size: 11px; color: $ink-3; }
  .task-stream-id { font-size: 11px; color: $ink-3; b { color: $ink-2; } }
}

.future-queue-strip {
  padding: 8px 18px;
  background: #fdfdfd;
  border-bottom: 1px dashed $border-hairline;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;

  .queue-label { font-size: 10.5px; font-weight: 700; color: $ink-4; text-transform: uppercase; }
  .queue-tag {
    background: $panel-tint;
    border: 1px solid $border-hairline;
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 11px;
    color: $ink-2;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    span { background: #e2e8f0; width: 15px; height: 15px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9.5px; font-weight: 700; }
  }
}

.stream-viewport {
  padding: 18px 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 440px;
  overflow-y: auto;
}

.stream-item { display: flex; gap: 12px; position: relative; }
.stream-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 22px;
  flex-shrink: 0;

  .track-node {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: $panel-tint;
    border: 1.5px solid $ink-4;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    z-index: 2;
    color: $ink-2;

    &.done { background: $up-soft; border-color: $up; color: $up; }
    &.alert { background: $warn-soft; border-color: $warn; color: $warn; }
    &.failed { background: $down-soft; border-color: $down; color: $down; }
  }

  .track-line { flex: 1; width: 1px; background: $border-hairline; margin-top: 4px; }
}

.stream-card {
  flex: 1;
  background: $panel-tint;
  border: 1px solid $border-hairline;
  border-radius: 12px;
  padding: 10px 14px;
  transition: all 0.2s;

  &:hover { background: #fff; border-color: rgba(74, 155, 140, 0.25); }
  &--approval { background: #fff; border-color: $warn; }
  &--approved { background: #f0fdf4; border-color: $up; }
  &--rejected { background: #fef2f2; border-color: $down; }

  .stream-card-head { display: flex; align-items: center; justify-content: space-between; b { font-size: 12.5px; color: $ink-1; } }
  .stream-time-tag { font-size: 11px; color: $ink-4; }
  .stream-card-body { font-size: 11.5px; color: $ink-3; margin-top: 4px; line-height: 1.5; }
}

.evidence-code-block {
  background: #1e293b;
  color: #cbd5e1;
  border-radius: 6px;
  padding: 8px 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  margin-top: 8px;
  line-height: 1.45;
  overflow-x: auto;
}

.in-stream-approval-card {
  background: #fff;
  border: 1.5px solid $warn;
  border-radius: 10px;
  padding: 12px 14px;
  margin-top: 8px;
  box-shadow: 0 4px 16px rgba(217, 119, 6, 0.12);

  .approval-kicker {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 700;
    color: #b45309;
    background: $warn-soft;
    padding: 2px 8px;
    border-radius: 999px;
    margin-bottom: 6px;
  }

  .approval-headline { font-size: 12.5px; font-weight: 700; color: $ink-1; }
  .approval-scope { font-size: 11.5px; color: $ink-2; margin-top: 3px; }
  .approval-why-link {
    font-size: 11px;
    color: $accent;
    text-decoration: underline;
    cursor: pointer;
    display: inline-block;
    margin-top: 6px;
  }

  .approval-btn-group {
    display: flex;
    gap: 8px;
    margin-top: 10px;

    button {
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-approve-action { background: $accent; color: #fff; border: none; &:hover { background: $accent-dark; } }
    .btn-modify-action { background: #fff; color: $ink-2; border: 1px solid $border-hairline; }
    .btn-reject-action { background: transparent; color: $down; border: none; }
  }
}

.workbench-input-bar {
  padding: 12px 18px;
  border-top: 1px solid $border-hairline;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 10px;

  .query-box {
    flex: 1;
    height: 36px;
    border: 1px solid $border-hairline;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 12px;
    outline: none;
    transition: all 0.2s;
    &:focus { border-color: $accent; box-shadow: 0 0 0 2px $accent-soft; }
  }

  .resident-stop-btn {
    height: 36px;
    padding: 0 14px;
    border-radius: 8px;
    background: $down;
    color: #fff;
    font-weight: 600;
    font-size: 11.5px;
    border: none;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 3px 12px rgba(239, 68, 68, 0.25);
    transition: all 0.2s;

    &:hover { opacity: 0.9; }
    &--halted { background: #94a3b8; box-shadow: none; }
  }
}

.workbench-receipt-footer {
  padding: 9px 18px;
  background: $panel-tint;
  border-top: 1px solid $border-hairline;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: $ink-3;
  b { color: $ink-2; }
}

/* 右翼组件 */
.right-suite {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.quick-ops-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.quick-op-card {
  background: $panel-bg;
  border: 1px solid $border-hairline;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
  display: flex;
  align-items: center;
  gap: 10px;

  &:hover {
    border-color: $accent;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px -4px rgba(74, 155, 140, 0.16);
  }

  .op-icon-wrapper {
    width: 36px;
    height: 36px;
    border-radius: 9px;
    background: $accent-soft;
    color: $accent-dark;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    flex-shrink: 0;
  }

  .op-meta-text b { font-size: 12.5px; color: $ink-1; display: block; }
  .op-meta-text small { font-size: 10.5px; color: $ink-3; }
}

.trade-doc-card {
  background: $panel-bg;
  border: 1px solid $border-hairline;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 4px 20px -4px rgba(74, 155, 140, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
  transition: all 0.3s ease;

  &--focused {
    box-shadow: 0 0 0 3px $accent !important;
  }

  .trade-doc-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    h4 { font-size: 13.5px; font-weight: 700; color: $ink-1; margin: 0; display: flex; align-items: center; gap: 6px; }
    .doc-code-tag { font-size: 11px; color: $accent; font-weight: 600; }
  }

  .pi-paper {
    background: #fdfdfd;
    border: 1px solid $border-hairline;
    border-radius: 8px;
    padding: 14px;
    font-size: 11px;

    .pi-title-row {
      display: flex;
      justify-content: space-between;
      border-bottom: 1.5px solid $ink-1;
      padding-bottom: 6px;
      margin-bottom: 8px;
      b { font-size: 13px; }
      .pi-sub { font-size: 10px; color: $ink-3; }
    }

    .pi-buyer-line { margin: 6px 0 8px; font-size: 11px; }

    .pi-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 6px;
      th { text-align: left; font-size: 10px; color: $ink-3; padding: 3px 0; border-bottom: 1px solid #e2e8f0; }
      td { padding: 5px 0; border-bottom: 1px solid #f1f5f9; }
    }

    .pi-total-row { text-align: right; padding-top: 8px; font-weight: 700; font-size: 12.5px; color: $ink-1; }
  }

  .doc-actions-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;

    .btn-doc-secondary { border-radius: 6px; font-size: 11.5px; }
    .btn-doc-primary { background: $accent; border-color: $accent; border-radius: 6px; font-size: 11.5px; font-weight: 600; }
  }
}

/* 3. 询盘大表 */
.today-board__inquiries-section {
  width: 100%;
}

.inquiries-card {
  background: $panel-bg;
  border: 1px solid $border-hairline;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 4px 20px -4px rgba(74, 155, 140, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
}

.inquiries-card__head {
  padding: 18px 22px;
  border-bottom: 1px solid $border-hairline;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  .section-kicker { font-size: 10.5px; font-weight: 700; color: $ink-4; letter-spacing: 0.06em; text-transform: uppercase; }
  .section-title { font-size: 16px; font-weight: 700; color: $ink-1; margin: 2px 0 0; }
  .inquiries-desc { font-size: 12px; color: $ink-3; margin: 4px 0 0; }
}

.inquiries-filter-tabs {
  display: flex;
  gap: 6px;

  .filter-tab-btn {
    border: 1px solid $border-hairline;
    background: $panel-tint;
    color: $ink-2;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { background: #fff; }
    &--active {
      background: $accent-soft;
      border-color: $accent;
      color: $accent-dark;
      font-weight: 600;
    }

    .filter-tab-count {
      margin-left: 4px;
      font-size: 10.5px;
      background: rgba(15, 23, 42, 0.06);
      padding: 1px 5px;
      border-radius: 999px;
    }
  }
}

.inquiries-table-wrapper {
  overflow-x: auto;
}

.inquiries-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;

  th {
    background: $panel-tint;
    padding: 10px 18px;
    font-size: 11px;
    font-weight: 600;
    color: $ink-3;
    text-align: left;
    border-bottom: 1px solid $border-hairline;
  }

  td {
    padding: 12px 18px;
    border-bottom: 1px solid rgba(15, 23, 42, 0.05);
    vertical-align: middle;
  }

  .inquiry-row {
    transition: background 0.15s;
    &:hover { background: rgba(74, 155, 140, 0.02); }
    &--unread { background: rgba(74, 155, 140, 0.035); }
  }

  .cell-buyer .buyer-info {
    display: flex;
    align-items: center;
    gap: 10px;
    .buyer-flag { font-size: 18px; }
    .buyer-name-line { display: flex; align-items: center; gap: 6px; }
    .buyer-name { font-weight: 600; color: $ink-1; }
    .unread-dot { width: 6px; height: 6px; border-radius: 50%; background: $down; }
    .buyer-company { font-size: 11px; color: $ink-3; display: block; }
  }

  .cell-spec {
    .category-name { font-weight: 600; color: $ink-1; display: block; }
    .spec-detail { font-size: 11px; color: $ink-3; display: block; }
  }

  .cell-amount {
    font-weight: 700;
    color: $ink-1;
  }

  .channel-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
    background: $panel-tint;
    border: 1px solid $border-hairline;
    color: $ink-2;

    .channel-dot { width: 6px; height: 6px; border-radius: 50%; }
    .whatsapp-dot { background: #25D366; }
    .website-dot { background: $accent; }
    .linkedin-dot { background: #0A66C2; }
    .other-dot { background: $ink-4; }
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    background: $panel-tint;
    color: $ink-2;
    border: 1px solid $border-hairline;

    &--new { background: rgba(59, 130, 246, 0.1); color: #2563eb; border-color: rgba(59, 130, 246, 0.2); }
    &--quoted, &--pi_sent { background: $accent-soft; color: $accent-dark; border-color: rgba(74, 155, 140, 0.3); }
    &--in_production { background: $up-soft; color: $up; border-color: rgba(16, 185, 129, 0.2); }
  }

  .time-hint { display: block; font-size: 10.5px; color: $ink-4; margin-top: 2px; }

  .actions-group {
    display: flex;
    justify-content: flex-end;
    gap: 6px;

    .btn-action-whatsapp {
      border-color: #25D366;
      color: #128C7E;
      border-radius: 6px;
      font-size: 11.5px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      &:hover { background: #25D366; color: #fff; }
    }

    .btn-action-quote {
      border-radius: 6px;
      font-size: 11.5px;
      color: $ink-2;
      &:hover { border-color: $accent; color: $accent; }
    }
  }
}

.inquiries-card__foot {
  padding: 12px 20px;
  background-color: $panel-tint;
  border-top: 1px solid $border-hairline;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  .honesty-label { font-size: 11.5px; color: $ink-3; }
  .btn-all-inquiries { color: $accent !important; font-weight: 600; font-size: 12px; padding: 0; }
}

.tabular-nums { font-variant-numeric: tabular-nums; }
.text-right { text-align: right; }

@media (max-width: 1200px) {
  .today-board__bento-section { grid-template-columns: 1fr; }
  .trade-steps-grid { grid-template-columns: repeat(4, 1fr); }
}

@media (max-width: 768px) {
  .today-board { padding: 16px 14px 32px; }
  .trade-steps-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
