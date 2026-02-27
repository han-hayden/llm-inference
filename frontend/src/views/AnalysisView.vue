<template>
  <div class="analysis-page">
    <h1 class="page-title">性能分析</h1>

    <!-- Data Collection Section -->
    <n-grid :x-gap="24" :cols="2" class="top-section">
      <n-gi>
        <n-card class="glass-card" :bordered="false" title="数据采集">
          <n-form label-placement="top" label-width="auto">
            <n-form-item label="采集名称">
              <n-input v-model:value="form.name" placeholder="例如 baseline-gpt4o-20260101" />
            </n-form-item>
            <n-form-item label="停止方式">
              <n-radio-group v-model:value="form.stop_type">
                <n-space>
                  <n-radio value="count">按次数</n-radio>
                  <n-radio value="time">按时间（秒）</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item :label="form.stop_type === 'count' ? '请求次数' : '持续时间（秒）'">
              <n-input-number
                v-model:value="form.stop_value"
                :min="1"
                placeholder="请输入数值"
                style="width: 100%"
              />
            </n-form-item>
            <n-space>
              <n-button
                type="primary"
                class="accent-btn"
                :loading="starting"
                :disabled="isActive"
                @click="handleStart"
              >
                开始采集
              </n-button>
              <n-button
                type="error"
                ghost
                :disabled="!isActive"
                :loading="stopping"
                @click="handleStop"
              >
                停止采集
              </n-button>
            </n-space>
          </n-form>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card class="glass-card" :bordered="false" title="采集状态">
          <n-spin :show="statusLoading">
            <div v-if="collectStatus" class="status-display">
              <div class="status-row">
                <span class="status-label">状态</span>
                <n-tag :type="isActive ? 'success' : 'default'" size="small" :bordered="false">
                  {{ collectStatus.status ?? 'idle' }}
                </n-tag>
              </div>
              <n-divider style="margin: 12px 0" />
              <div class="status-row">
                <span class="status-label">任务ID</span>
                <span class="status-value mono">{{ collectStatus.task_id ?? '-' }}</span>
              </div>
              <n-divider style="margin: 12px 0" />
              <div class="status-row">
                <span class="status-label">已采集</span>
                <span class="status-value highlight">{{ collectStatus.collected_count ?? 0 }}</span>
              </div>
              <n-divider style="margin: 12px 0" />
              <div class="status-row">
                <span class="status-label">已用时</span>
                <span class="status-value">{{ collectStatus.elapsed_seconds ?? 0 }}s</span>
              </div>
              <template v-if="isActive && collectStatus.progress != null">
                <n-divider style="margin: 12px 0" />
                <n-progress
                  type="line"
                  :percentage="Math.min(Math.round(collectStatus.progress * 100), 100)"
                  :indicator-placement="'inside'"
                  processing
                />
              </template>
            </div>
            <div v-else class="status-empty">
              暂无进行中的采集任务。
            </div>
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Divider -->
    <n-divider />

    <!-- Task Selector -->
    <n-card class="glass-card" :bordered="false">
      <n-form-item label="选择分析任务" label-placement="left">
        <n-select
          v-model:value="selectedTaskId"
          :options="taskOptions"
          :loading="tasksLoading"
          filterable
          clearable
          placeholder="选择一个任务查看分析结果"
          style="width: 400px"
          @update:value="handleTaskChange"
        />
      </n-form-item>
    </n-card>

    <!-- Analysis Results (shown when a task is selected) -->
    <template v-if="selectedTaskId">
      <!-- Metric Summary Cards -->
      <n-spin :show="metricsLoading">
        <n-grid :cols="4" :x-gap="16" :y-gap="16" class="metrics-grid">
          <n-gi v-for="card in metricCards" :key="card.label">
            <n-card class="glass-card metric-card" :bordered="false">
              <div class="metric-label">{{ card.label }}</div>
              <div class="metric-value">{{ formatMetric(card.value) }}</div>
              <div class="percentile-row">
                <span class="percentile-tag">P50: {{ formatMetric(card.p50) }}</span>
                <span class="percentile-tag">P90: {{ formatMetric(card.p90) }}</span>
                <span class="percentile-tag">P99: {{ formatMetric(card.p99) }}</span>
              </div>
            </n-card>
          </n-gi>
        </n-grid>
      </n-spin>

      <!-- Distribution Charts -->
      <n-spin :show="distLoading">
        <n-grid :cols="3" :x-gap="16" :y-gap="16" class="charts-grid">
          <n-gi>
            <n-card class="glass-card" :bordered="false" title="上下文长度分布">
              <div ref="contextChartRef" class="chart-container"></div>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card class="glass-card" :bordered="false" title="响应延迟分布">
              <div ref="latencyChartRef" class="chart-container"></div>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card class="glass-card" :bordered="false" title="缓存命中率分布">
              <div ref="cacheChartRef" class="chart-container"></div>
            </n-card>
          </n-gi>
        </n-grid>
      </n-spin>

      <!-- Optimization Suggestions -->
      <n-spin :show="suggestionsLoading">
        <n-card class="glass-card suggestions-card" :bordered="false" title="优化建议">
          <div v-if="suggestions && suggestions.length > 0" class="suggestions-list">
            <div class="suggestion-item" v-for="(item, idx) in suggestions" :key="idx">
              <h4 class="suggestion-title">{{ item.title || `建议 ${idx + 1}` }}</h4>
              <p class="suggestion-content">{{ item.content || item }}</p>
            </div>
          </div>
          <div v-else class="status-empty">
            选择任务后将展示智能优化建议。
          </div>
        </n-card>
      </n-spin>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import {
  startCollect,
  stopCollect,
  getCollectStatus,
  listTaskFiles,
  getMetricsSummary,
  getDistributions,
  getSuggestions,
} from '../api'

const message = useMessage()

// ============ Data Collection ============
const form = reactive({
  name: '',
  stop_type: 'count' as 'count' | 'time',
  stop_value: 100 as number | null,
})

const starting = ref(false)
const stopping = ref(false)
const statusLoading = ref(false)
const collectStatus = ref<any>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const isActive = computed(() => {
  return collectStatus.value?.status === 'running' || collectStatus.value?.status === 'collecting'
})

async function fetchStatus() {
  try {
    const res = await getCollectStatus()
    collectStatus.value = res.data ?? res
  } catch {
    collectStatus.value = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (isActive.value) {
      fetchStatus()
    } else {
      stopPolling()
      loadTasks()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleStart() {
  if (!form.name) {
    message.warning('请输入采集名称')
    return
  }
  starting.value = true
  try {
    await startCollect({
      name: form.name,
      stop_type: form.stop_type,
      stop_value: form.stop_value ?? 100,
    })
    message.success('采集已启动')
    await fetchStatus()
    startPolling()
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '启动采集失败')
  } finally {
    starting.value = false
  }
}

async function handleStop() {
  stopping.value = true
  try {
    await stopCollect({})
    message.success('采集已停止')
    await fetchStatus()
    await loadTasks()
    stopPolling()
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '停止采集失败')
  } finally {
    stopping.value = false
  }
}

// ============ Task Selection ============
const tasksLoading = ref(false)
const taskOptions = ref<{ label: string; value: string }[]>([])
const selectedTaskId = ref<string | null>(null)

async function loadTasks() {
  tasksLoading.value = true
  try {
    const res = await listTaskFiles()
    const data = res.data ?? res
    const list = Array.isArray(data) ? data : (data.tasks ?? data.items ?? [])
    taskOptions.value = list.map((t: any) => ({
      label: `${t.name ?? t.task_id} (${t.type ?? 'unknown'})`,
      value: t.task_id,
    }))
  } catch (err) {
    console.error('Failed to load tasks', err)
  } finally {
    tasksLoading.value = false
  }
}

function handleTaskChange(taskId: string | null) {
  if (taskId) {
    loadMetrics(taskId)
    loadDistributions(taskId)
    loadSuggestions(taskId)
  }
}

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

async function loadMetrics(taskId: string) {
  metricsLoading.value = true
  try {
    const res = await getMetricsSummary(taskId)
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

async function loadDistributions(taskId: string) {
  distLoading.value = true
  try {
    const res = await getDistributions(taskId)
    const d = res.data?.data ?? res.data

    await nextTick()

    contextChart?.dispose()
    latencyChart?.dispose()
    cacheChart?.dispose()

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

// ============ Suggestions ============
const suggestionsLoading = ref(false)
const suggestions = ref<any[]>([])

async function loadSuggestions(taskId: string) {
  suggestionsLoading.value = true
  try {
    const res = await getSuggestions(taskId)
    const d = res.data?.data ?? res.data
    suggestions.value = Array.isArray(d) ? d : d?.items ?? d?.suggestions ?? []
  } catch (e) {
    console.error('Failed to load suggestions', e)
  } finally {
    suggestionsLoading.value = false
  }
}

// ============ Lifecycle ============
onMounted(async () => {
  statusLoading.value = true
  await fetchStatus()
  statusLoading.value = false
  await loadTasks()
  if (isActive.value) {
    startPolling()
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopPolling()
  window.removeEventListener('resize', handleResize)
  contextChart?.dispose()
  latencyChart?.dispose()
  cacheChart?.dispose()
})
</script>

<style scoped>
.analysis-page {
  max-width: 1400px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 24px 0;
}

.top-section {
  margin-bottom: 0;
}

.glass-card {
  background: rgba(255, 255, 255, 0.04) !important;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  border-radius: 12px !important;
}

.accent-btn {
  background: linear-gradient(135deg, #00f0ff, #7c3aed) !important;
  border: none !important;
  font-weight: 600;
}

.status-display {
  padding: 4px 0;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

.status-value {
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
}

.status-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.status-value.highlight {
  color: #00f0ff;
  font-weight: 700;
  font-size: 18px;
}

.status-empty {
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 32px 0;
}

.metrics-grid {
  margin: 24px 0;
}

.metric-card {
  text-align: center;
  padding: 8px 0;
}

.metric-label {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #00f0ff;
}

.percentile-row {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.percentile-tag {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 8px;
  border-radius: 4px;
}

.charts-grid {
  margin: 24px 0;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.suggestions-card {
  margin-top: 8px;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.suggestion-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 16px;
}

.suggestion-title {
  color: #00f0ff;
  margin: 0 0 8px 0;
  font-size: 15px;
}

.suggestion-content {
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.6;
  margin: 0;
}
</style>
