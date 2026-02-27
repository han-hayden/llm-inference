<template>
  <div class="record-detail-view">
    <!-- Header -->
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px">
      <n-button quaternary circle @click="router.push('/records')">
        <template #icon>
          <n-icon :component="ArrowBackOutline" />
        </template>
      </n-button>
      <h2 style="margin: 0; font-size: 1.4rem">
        记录详情
        <span style="color: var(--text-secondary); font-size: 0.85rem; margin-left: 8px">{{ taskId }}</span>
      </h2>
    </div>

    <!-- Tabs -->
    <n-tabs type="segment" animated>
      <!-- Tab 1: Performance Overview -->
      <n-tab-pane name="overview" tab="性能概览">
        <!-- Metric Summary Cards -->
        <n-spin :show="metricsLoading">
          <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
            <n-grid-item span="4 s:2 m:1" v-for="card in metricCards" :key="card.label">
              <div class="glass-card" style="text-align: center">
                <div class="metric-label">{{ card.label }}</div>
                <div class="metric-value">{{ formatMetric(card.value) }}</div>
                <div style="margin-top: 8px; display: flex; justify-content: center; gap: 12px">
                  <span class="percentile-tag">P50: {{ formatMetric(card.p50) }}</span>
                  <span class="percentile-tag">P90: {{ formatMetric(card.p90) }}</span>
                  <span class="percentile-tag">P99: {{ formatMetric(card.p99) }}</span>
                </div>
              </div>
            </n-grid-item>
          </n-grid>
        </n-spin>

        <!-- Distribution Charts -->
        <n-spin :show="distLoading" style="margin-top: 24px">
          <n-grid :cols="3" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
            <n-grid-item span="3 m:1">
              <div class="glass-card">
                <h4 style="margin-bottom: 12px; color: var(--text-secondary)">上下文长度分布</h4>
                <div ref="contextChartRef" style="width: 100%; height: 300px"></div>
              </div>
            </n-grid-item>
            <n-grid-item span="3 m:1">
              <div class="glass-card">
                <h4 style="margin-bottom: 12px; color: var(--text-secondary)">响应延迟分布</h4>
                <div ref="latencyChartRef" style="width: 100%; height: 300px"></div>
              </div>
            </n-grid-item>
            <n-grid-item span="3 m:1">
              <div class="glass-card">
                <h4 style="margin-bottom: 12px; color: var(--text-secondary)">缓存命中率分布</h4>
                <div ref="cacheChartRef" style="width: 100%; height: 300px"></div>
              </div>
            </n-grid-item>
          </n-grid>
        </n-spin>
      </n-tab-pane>

      <!-- Tab 2: Performance Data -->
      <n-tab-pane name="performance" tab="性能数据">
        <n-data-table
          remote
          :columns="perfColumns"
          :data="perfData"
          :loading="perfLoading"
          :pagination="perfPagination"
          :row-key="(row: any) => row.id ?? row.序号"
          @update:page="handlePerfPageChange"
          @update:page-size="handlePerfPageSizeChange"
          striped
        />
      </n-tab-pane>

      <!-- Tab 3: QA Pairs -->
      <n-tab-pane name="qa" tab="问答数据">
        <n-data-table
          remote
          :columns="qaColumns"
          :data="qaData"
          :loading="qaLoading"
          :pagination="qaPagination"
          :row-key="(row: any) => row.id ?? row.序号"
          @update:page="handleQaPageChange"
          @update:page-size="handleQaPageSizeChange"
          striped
        />
      </n-tab-pane>

      <!-- Tab 4: Optimization Suggestions -->
      <n-tab-pane name="suggestions" tab="优化建议">
        <n-spin :show="suggestionsLoading">
          <div v-if="suggestions && suggestions.length > 0" style="display: flex; flex-direction: column; gap: 16px">
            <div class="glass-card" v-for="(item, idx) in suggestions" :key="idx">
              <h4 style="color: var(--accent-cyan); margin-bottom: 8px">{{ item.title || `Suggestion ${idx + 1}` }}</h4>
              <p style="color: var(--text-secondary); line-height: 1.6">{{ item.content || item }}</p>
            </div>
          </div>
          <div v-else class="glass-card" style="text-align: center; padding: 80px 20px">
            <n-icon :component="HardwareChipOutline" :size="64" style="color: var(--text-secondary); margin-bottom: 16px" />
            <h3 style="color: var(--text-secondary); margin-bottom: 8px">分析引擎即将上线</h3>
            <p style="color: var(--text-secondary); font-size: 0.85rem">
              分析引擎就绪后，将在此处生成智能优化建议。
            </p>
          </div>
        </n-spin>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, h } from 'vue'
import { useRouter } from 'vue-router'
import { NEllipsis } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { ArrowBackOutline, HardwareChipOutline } from '@vicons/ionicons5'
import * as echarts from 'echarts'
import {
  getPerformanceData,
  getQAData,
  getSummary,
  getDistributions,
  getMetricsSummary,
  getSuggestions,
} from '../api'

const props = defineProps<{
  taskId: string
}>()

const router = useRouter()

// ============ Metric Summary ============
interface MetricCard {
  label: string
  value: number | string
  p50: number | string
  p90: number | string
  p99: number | string
}

const metricsLoading = ref(false)
const metricCards = ref<MetricCard[]>([
  { label: 'TTFT Avg', value: '--', p50: '--', p90: '--', p99: '--' },
  { label: 'TPOT Avg', value: '--', p50: '--', p90: '--', p99: '--' },
  { label: 'TPS Avg', value: '--', p50: '--', p90: '--', p99: '--' },
  { label: 'E2E Avg', value: '--', p50: '--', p90: '--', p99: '--' },
])

function formatMetric(val: number | string): string {
  if (typeof val === 'string') return val
  if (val === null || val === undefined) return '--'
  return val >= 1000 ? val.toFixed(0) : val.toFixed(2)
}

async function loadMetrics() {
  metricsLoading.value = true
  try {
    const res = await getMetricsSummary(props.taskId)
    const d = res.data?.data ?? res.data
    if (d) {
      metricCards.value = [
        {
          label: 'TTFT Avg',
          value: d.ttft_avg ?? d.ttft?.avg ?? '--',
          p50: d.ttft_p50 ?? d.ttft?.p50 ?? '--',
          p90: d.ttft_p90 ?? d.ttft?.p90 ?? '--',
          p99: d.ttft_p99 ?? d.ttft?.p99 ?? '--',
        },
        {
          label: 'TPOT Avg',
          value: d.tpot_avg ?? d.tpot?.avg ?? '--',
          p50: d.tpot_p50 ?? d.tpot?.p50 ?? '--',
          p90: d.tpot_p90 ?? d.tpot?.p90 ?? '--',
          p99: d.tpot_p99 ?? d.tpot?.p99 ?? '--',
        },
        {
          label: 'TPS Avg',
          value: d.tps_avg ?? d.tps?.avg ?? '--',
          p50: d.tps_p50 ?? d.tps?.p50 ?? '--',
          p90: d.tps_p90 ?? d.tps?.p90 ?? '--',
          p99: d.tps_p99 ?? d.tps?.p99 ?? '--',
        },
        {
          label: 'E2E Avg',
          value: d.e2e_avg ?? d.e2e?.avg ?? d.e2e_latency?.avg ?? '--',
          p50: d.e2e_p50 ?? d.e2e?.p50 ?? d.e2e_latency?.p50 ?? '--',
          p90: d.e2e_p90 ?? d.e2e?.p90 ?? d.e2e_latency?.p90 ?? '--',
          p99: d.e2e_p99 ?? d.e2e?.p99 ?? d.e2e_latency?.p99 ?? '--',
        },
      ]
    }
  } catch (e) {
    console.error('Failed to load metrics summary', e)
  } finally {
    metricsLoading.value = false
  }
}

// ============ Distribution Charts ============
const distLoading = ref(false)
const contextChartRef = ref<HTMLElement | null>(null)
const latencyChartRef = ref<HTMLElement | null>(null)
const cacheChartRef = ref<HTMLElement | null>(null)

let contextChart: echarts.ECharts | null = null
let latencyChart: echarts.ECharts | null = null
let cacheChart: echarts.ECharts | null = null

function buildBarOption(categories: string[], values: number[], xLabel: string): echarts.EChartsOption {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1e2e',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e2e8f0' },
    },
    grid: {
      left: '8%',
      right: '4%',
      bottom: '12%',
      top: '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      name: xLabel,
      nameTextStyle: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: 40,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00f0ff' },
            { offset: 1, color: '#7c3aed' },
          ]),
        },
      },
    ],
  }
}

function initChart(el: HTMLElement | null): echarts.ECharts | null {
  if (!el) return null
  return echarts.init(el, undefined, { renderer: 'canvas' })
}

async function loadDistributions() {
  distLoading.value = true
  try {
    const res = await getDistributions(props.taskId)
    const d = res.data?.data ?? res.data

    await nextTick()

    contextChart = initChart(contextChartRef.value)
    latencyChart = initChart(latencyChartRef.value)
    cacheChart = initChart(cacheChartRef.value)

    if (d?.context_length) {
      const labels = d.context_length.labels ?? d.context_length.bins ?? []
      const vals = d.context_length.values ?? d.context_length.counts ?? []
      contextChart?.setOption(buildBarOption(labels, vals, 'Context Length'))
    } else {
      contextChart?.setOption(buildBarOption([], [], 'Context Length'))
    }

    if (d?.response_latency) {
      const labels = d.response_latency.labels ?? d.response_latency.bins ?? []
      const vals = d.response_latency.values ?? d.response_latency.counts ?? []
      latencyChart?.setOption(buildBarOption(labels, vals, 'Latency (ms)'))
    } else {
      latencyChart?.setOption(buildBarOption([], [], 'Latency (ms)'))
    }

    if (d?.cache_hit_rate) {
      const labels = d.cache_hit_rate.labels ?? d.cache_hit_rate.bins ?? []
      const vals = d.cache_hit_rate.values ?? d.cache_hit_rate.counts ?? []
      cacheChart?.setOption(buildBarOption(labels, vals, 'Cache Hit Rate'))
    } else {
      cacheChart?.setOption(buildBarOption([], [], 'Cache Hit Rate'))
    }
  } catch (e) {
    console.error('Failed to load distributions', e)
  } finally {
    distLoading.value = false
  }
}

function handleResize() {
  contextChart?.resize()
  latencyChart?.resize()
  cacheChart?.resize()
}

// ============ Performance Data Table ============
const perfLoading = ref(false)
const perfData = ref<any[]>([])
const perfPagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 条`,
})

const perfColumns: DataTableColumns<any> = [
  { title: '序号', key: '序号', width: 70, render: (_row, index) => (perfPagination.value.page - 1) * perfPagination.value.pageSize + index + 1 },
  { title: '模型', key: 'model', width: 160, ellipsis: { tooltip: true } },
  { title: '输入Token', key: 'prompt_tokens', width: 120, sorter: 'default' },
  { title: '缓存Token', key: 'cached_tokens', width: 120, sorter: 'default' },
  { title: '输出Token', key: 'completion_tokens', width: 140, sorter: 'default' },
  { title: 'TTFT (ms)', key: 'ttft_ms', width: 110, sorter: 'default' },
  { title: 'TPOT (ms)', key: 'tpot_ms', width: 110, sorter: 'default' },
  { title: 'TPS', key: 'tps', width: 90, sorter: 'default' },
  { title: '端到端延迟(ms)', key: 'e2e_latency_ms', width: 140, sorter: 'default' },
  { title: '到达时间', key: 'arrival_time', width: 180, ellipsis: { tooltip: true } },
]

async function loadPerfData() {
  perfLoading.value = true
  try {
    const res = await getPerformanceData(props.taskId, perfPagination.value.page, perfPagination.value.pageSize)
    const d = res.data?.data ?? res.data
    perfData.value = d?.items ?? d?.records ?? d?.list ?? []
    perfPagination.value.itemCount = d?.total ?? d?.count ?? perfData.value.length
  } catch (e) {
    console.error('Failed to load performance data', e)
  } finally {
    perfLoading.value = false
  }
}

function handlePerfPageChange(page: number) {
  perfPagination.value.page = page
  loadPerfData()
}

function handlePerfPageSizeChange(pageSize: number) {
  perfPagination.value.pageSize = pageSize
  perfPagination.value.page = 1
  loadPerfData()
}

// ============ QA Data Table ============
const qaLoading = ref(false)
const qaData = ref<any[]>([])
const qaPagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 条`,
})

const qaColumns: DataTableColumns<any> = [
  { title: '序号', key: '序号', width: 70, render: (_row, index) => (qaPagination.value.page - 1) * qaPagination.value.pageSize + index + 1 },
  { title: '模型', key: 'model', width: 160, ellipsis: { tooltip: true } },
  {
    title: '请求消息',
    key: 'messages',
    width: 360,
    render(row) {
      const text = typeof row.messages === 'string' ? row.messages : JSON.stringify(row.messages)
      return h(NEllipsis, { style: 'max-width: 340px', lineClamp: 2, expandTrigger: 'click', tooltip: false }, { default: () => text })
    },
  },
  {
    title: '响应内容',
    key: 'response_content',
    width: 360,
    render(row) {
      const text = typeof row.response_content === 'string' ? row.response_content : JSON.stringify(row.response_content)
      return h(NEllipsis, { style: 'max-width: 340px', lineClamp: 2, expandTrigger: 'click', tooltip: false }, { default: () => text })
    },
  },
]

async function loadQaData() {
  qaLoading.value = true
  try {
    const res = await getQAData(props.taskId, qaPagination.value.page, qaPagination.value.pageSize)
    const d = res.data?.data ?? res.data
    qaData.value = d?.items ?? d?.records ?? d?.list ?? []
    qaPagination.value.itemCount = d?.total ?? d?.count ?? qaData.value.length
  } catch (e) {
    console.error('Failed to load QA data', e)
  } finally {
    qaLoading.value = false
  }
}

function handleQaPageChange(page: number) {
  qaPagination.value.page = page
  loadQaData()
}

function handleQaPageSizeChange(pageSize: number) {
  qaPagination.value.pageSize = pageSize
  qaPagination.value.page = 1
  loadQaData()
}

// ============ Suggestions ============
const suggestionsLoading = ref(false)
const suggestions = ref<any[]>([])

async function loadSuggestions() {
  suggestionsLoading.value = true
  try {
    const res = await getSuggestions(props.taskId)
    const d = res.data?.data ?? res.data
    suggestions.value = Array.isArray(d) ? d : d?.items ?? d?.suggestions ?? []
  } catch (e) {
    console.error('Failed to load suggestions', e)
  } finally {
    suggestionsLoading.value = false
  }
}

// ============ Lifecycle ============
onMounted(() => {
  loadMetrics()
  loadPerfData()
  loadQaData()
  loadDistributions()
  loadSuggestions()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  contextChart?.dispose()
  latencyChart?.dispose()
  cacheChart?.dispose()
})
</script>

<style scoped>
.record-detail-view {
  padding: 4px;
}

.percentile-tag {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 8px;
  border-radius: 4px;
}
</style>
