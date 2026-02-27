<template>
  <div class="compare-page">
    <h1 class="page-title">对比分析</h1>

    <n-card class="glass-card" :bordered="false" title="选择对比任务">
      <n-grid :x-gap="16" :cols="3">
        <n-gi>
          <n-form-item label="基线任务">
            <n-select
              v-model:value="baselineId"
              :options="taskOptions"
              :loading="tasksLoading"
              filterable
              placeholder="选择基线任务"
            />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="优化任务">
            <n-select
              v-model:value="optimizedId"
              :options="taskOptions"
              :loading="tasksLoading"
              filterable
              placeholder="选择优化任务"
            />
          </n-form-item>
        </n-gi>
        <n-gi style="display: flex; align-items: flex-end; padding-bottom: 26px;">
          <n-button
            type="primary"
            class="accent-btn"
            :loading="comparing"
            :disabled="!baselineId || !optimizedId"
            @click="handleCompare"
          >
            开始对比
          </n-button>
        </n-gi>
      </n-grid>
    </n-card>

    <template v-if="result">
      <n-grid :x-gap="16" :y-gap="16" :cols="4" class="improvement-grid">
        <n-gi>
          <n-card class="glass-card metric-card" :bordered="false">
            <div class="metric-label">TTFT Reduction</div>
            <div class="metric-value" :class="metricClass(result.ttft_reduction)">
              {{ formatPercent(result.ttft_reduction) }}
            </div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card class="glass-card metric-card" :bordered="false">
            <div class="metric-label">TPS Increase</div>
            <div class="metric-value" :class="metricClass(result.tps_increase, true)">
              {{ formatPercent(result.tps_increase) }}
            </div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card class="glass-card metric-card" :bordered="false">
            <div class="metric-label">TPOT Reduction</div>
            <div class="metric-value" :class="metricClass(result.tpot_reduction)">
              {{ formatPercent(result.tpot_reduction) }}
            </div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card class="glass-card metric-card" :bordered="false">
            <div class="metric-label">E2E Reduction</div>
            <div class="metric-value" :class="metricClass(result.e2e_reduction)">
              {{ formatPercent(result.e2e_reduction) }}
            </div>
          </n-card>
        </n-gi>
      </n-grid>

      <n-grid :x-gap="24" :cols="2" class="charts-grid">
        <n-gi>
          <n-card class="glass-card" :bordered="false" title="TTFT Comparison">
            <div ref="ttftChartRef" class="chart-container"></div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card class="glass-card" :bordered="false" title="Decode Speed Comparison">
            <div ref="decodeChartRef" class="chart-container"></div>
          </n-card>
        </n-gi>
      </n-grid>

      <div class="export-section">
        <n-button
          type="primary"
          class="accent-btn"
          :loading="exporting"
          @click="handleExportReport"
        >
          导出报告
        </n-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import { compareTasks, listTaskFiles, generateReport, downloadReportUrl } from '../api'

const route = useRoute()
const message = useMessage()

const baselineId = ref<string | null>(null)
const optimizedId = ref<string | null>(null)
const tasksLoading = ref(false)
const comparing = ref(false)
const taskOptions = ref<{ label: string; value: string }[]>([])
const result = ref<any>(null)
const exporting = ref(false)

const ttftChartRef = ref<HTMLElement | null>(null)
const decodeChartRef = ref<HTMLElement | null>(null)
let ttftChart: echarts.ECharts | null = null
let decodeChart: echarts.ECharts | null = null

function formatPercent(val: number | undefined | null): string {
  if (val == null) return 'N/A'
  const sign = val > 0 ? '+' : ''
  return `${sign}${(val * 100).toFixed(1)}%`
}

function metricClass(val: number | undefined | null, higherIsBetter = false): string {
  if (val == null) return ''
  if (higherIsBetter) return val > 0 ? 'positive' : val < 0 ? 'negative' : ''
  return val > 0 ? 'positive' : val < 0 ? 'negative' : ''
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    const res = await listTaskFiles()
    const data = res.data ?? res
    const list = Array.isArray(data) ? data : (data.tasks ?? data.items ?? [])
    taskOptions.value = list.map((t: any) => ({
      label: `${t.name ?? t.task_id} (${t.type ?? 'unknown'})`,
      value: t.task_id
    }))
  } catch (err) {
    console.error('Failed to load tasks', err)
  } finally {
    tasksLoading.value = false
  }
}

async function handleCompare() {
  if (!baselineId.value || !optimizedId.value) {
    message.warning('请选择基线任务和优化任务')
    return
  }
  comparing.value = true
  try {
    const res = await compareTasks(baselineId.value, optimizedId.value)
    result.value = res.data ?? res
    await nextTick()
    renderCharts()
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '对比失败')
  } finally {
    comparing.value = false
  }
}

async function handleExportReport() {
  if (!baselineId.value || !optimizedId.value) return
  exporting.value = true
  try {
    const res = await generateReport({
      title: 'AICP LLM推理性能测试报告',
      baseline_task_id: baselineId.value,
      optimized_task_id: optimizedId.value,
    })
    const data = res.data ?? res
    const reportId = data.report_id ?? data.id
    if (reportId) {
      window.open(downloadReportUrl(reportId), '_blank')
      message.success('报告生成成功')
    } else {
      message.error('未获取到报告ID')
    }
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '导出报告失败')
  } finally {
    exporting.value = false
  }
}

function buildChartOption(title: string, baselineData: number[], optimizedData: number[], yLabel: string): echarts.EChartsOption {
  const xLabels = baselineData.map((_: number, i: number) => `#${i + 1}`)
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['Baseline', 'Optimized'],
      textStyle: { color: 'rgba(255,255,255,0.65)' },
      top: 0
    },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: xLabels,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: 'rgba(255,255,255,0.45)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: yLabel,
      nameTextStyle: { color: 'rgba(255,255,255,0.45)' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: 'rgba(255,255,255,0.45)' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
    },
    series: [
      {
        name: 'Baseline',
        type: 'line',
        data: baselineData,
        smooth: true,
        lineStyle: { color: '#7c3aed', width: 2 },
        itemStyle: { color: '#7c3aed' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(124,58,237,0.3)' },
          { offset: 1, color: 'rgba(124,58,237,0.02)' }
        ]) }
      },
      {
        name: 'Optimized',
        type: 'line',
        data: optimizedData,
        smooth: true,
        lineStyle: { color: '#00f0ff', width: 2 },
        itemStyle: { color: '#00f0ff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0,240,255,0.3)' },
          { offset: 1, color: 'rgba(0,240,255,0.02)' }
        ]) }
      }
    ]
  }
}

function renderCharts() {
  if (!result.value) return

  const r = result.value
  const baselineTTFT = r.baseline_ttft ?? r.ttft?.baseline ?? []
  const optimizedTTFT = r.optimized_ttft ?? r.ttft?.optimized ?? []
  const baselineDecode = r.baseline_decode_speed ?? r.decode_speed?.baseline ?? []
  const optimizedDecode = r.optimized_decode_speed ?? r.decode_speed?.optimized ?? []

  if (ttftChartRef.value) {
    ttftChart?.dispose()
    ttftChart = echarts.init(ttftChartRef.value)
    ttftChart.setOption(buildChartOption('TTFT', baselineTTFT, optimizedTTFT, 'ms'))
  }

  if (decodeChartRef.value) {
    decodeChart?.dispose()
    decodeChart = echarts.init(decodeChartRef.value)
    decodeChart.setOption(buildChartOption('Decode Speed', baselineDecode, optimizedDecode, 'tokens/s'))
  }
}

function handleResize() {
  ttftChart?.resize()
  decodeChart?.resize()
}

onMounted(async () => {
  await loadTasks()

  const qBaseline = route.query.baseline as string | undefined
  const qOptimized = route.query.optimized as string | undefined
  if (qBaseline) baselineId.value = qBaseline
  if (qOptimized) optimizedId.value = qOptimized

  if (baselineId.value && optimizedId.value) {
    await handleCompare()
  }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  ttftChart?.dispose()
  decodeChart?.dispose()
})
</script>

<style scoped>
.compare-page {
  max-width: 1400px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 24px 0;
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

.improvement-grid {
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
  color: rgba(255, 255, 255, 0.7);
}

.metric-value.positive {
  color: #00f0ff;
}

.metric-value.negative {
  color: #ff6b6b;
}

.charts-grid {
  margin-top: 8px;
}

.chart-container {
  width: 100%;
  height: 340px;
}

.export-section {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
</style>
