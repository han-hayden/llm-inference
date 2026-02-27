<template>
  <div class="benchmark-page">
    <h1 class="page-title">性能压测</h1>

    <n-card class="glass-card" :bordered="false">
      <!-- Running benchmarks status bar -->
      <div class="benchmark-status-bar" v-if="runningBenchmarks.length > 0">
        <div v-for="bm in runningBenchmarks" :key="bm.task_id" class="running-item">
          <div class="running-header">
            <span class="status-bar-label">运行中</span>
            <span class="running-name">{{ bm.name ?? bm.task_id }}</span>
            <n-tag type="success" size="small" :bordered="false">running</n-tag>
          </div>
          <div class="running-progress">
            <n-progress
              type="line"
              :percentage="Math.min(Math.round((bm.progress ?? 0) * 100), 100)"
              :indicator-placement="'inside'"
              processing
              style="width: 200px"
            />
            <span class="running-detail">{{ bm.completed ?? 0 }} / {{ bm.total ?? '?' }} 请求</span>
          </div>
        </div>
        <n-divider style="margin: 16px 0" />
      </div>

      <!-- Inline form -->
      <n-form label-placement="left" label-width="80px" style="max-width: 640px">
        <n-grid :x-gap="16" :cols="2">
          <n-gi>
            <n-form-item label="测试名称">
              <n-input v-model:value="form.name" placeholder="例如 benchmark-gpt4o-v2" size="small" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="源任务">
              <n-select
                v-model:value="form.source_task_id"
                :options="collectTaskOptions"
                :loading="collectLoading"
                filterable
                placeholder="选择采集任务"
                size="small"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-grid :x-gap="16" :cols="4">
          <n-gi>
            <n-form-item label="目标主机">
              <n-input v-model:value="form.target_host" placeholder="127.0.0.1" size="small" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="目标端口">
              <n-input-number
                v-model:value="form.target_port"
                :min="1"
                :max="65535"
                placeholder="8080"
                size="small"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="并发数">
              <n-input-number
                v-model:value="form.concurrency"
                :min="1"
                :max="500"
                placeholder="1"
                size="small"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="回放模式">
              <n-select
                v-model:value="form.replay_mode"
                :options="replayModeOptions"
                size="small"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-grid :x-gap="16" :cols="4">
          <n-gi>
            <n-form-item label="延迟(ms)">
              <n-input-number
                v-model:value="form.delay_ms"
                :min="0"
                placeholder="0"
                size="small"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="超时(s)">
              <n-input-number
                v-model:value="form.timeout_s"
                :min="1"
                placeholder="60"
                size="small"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
          <n-gi :span="2" style="display: flex; align-items: flex-start; padding-top: 26px;">
            <n-button
              type="primary"
              class="accent-btn"
              size="small"
              :loading="starting"
              @click="handleStart"
            >
              开始测试
            </n-button>
          </n-gi>
        </n-grid>
      </n-form>
    </n-card>

    <n-card class="glass-card table-card" :bordered="false" title="历史测试">
      <n-data-table
        :columns="columns"
        :data="benchmarkTasks"
        :loading="tasksLoading"
        :pagination="{ pageSize: 10 }"
        size="small"
        striped
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import { useMessage, NTag } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { startBenchmark, getBenchmarkProgress, listBenchmarkTasks, listCollectTasks } from '../api'

const message = useMessage()

const form = reactive({
  name: '',
  source_task_id: null as string | null,
  target_host: '',
  target_port: 8080 as number | null,
  concurrency: 1 as number | null,
  replay_mode: 'sequential' as string,
  delay_ms: 0 as number | null,
  timeout_s: 60 as number | null
})

const replayModeOptions = [
  { label: '顺序', value: 'sequential' },
  { label: '并发', value: 'concurrent' }
]

const starting = ref(false)
const collectLoading = ref(false)
const tasksLoading = ref(false)
const collectTaskOptions = ref<{ label: string; value: string }[]>([])
const benchmarkTasks = ref<any[]>([])
const runningBenchmarks = ref<any[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

const columns: DataTableColumns<any> = [
  { title: '任务ID', key: 'task_id', width: 220, ellipsis: { tooltip: true } },
  { title: '名称', key: 'name', width: 180 },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render(row) {
      const color = row.status === 'running' ? 'success' : row.status === 'completed' ? 'info' : row.status === 'failed' ? 'error' : 'default'
      return h(NTag, { type: color, size: 'small', bordered: false }, { default: () => row.status ?? '-' })
    }
  },
  { title: '记录数', key: 'record_count', width: 100 },
  { title: '源任务', key: 'source_task_id', width: 200, ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'created_at', width: 180 }
]

async function loadCollectTasks() {
  collectLoading.value = true
  try {
    const res = await listCollectTasks()
    const data = res.data ?? res
    const list = Array.isArray(data) ? data : (data.tasks ?? data.items ?? [])
    collectTaskOptions.value = list.map((t: any) => ({
      label: `${t.name ?? t.task_id} (${t.record_count ?? 0} records)`,
      value: t.task_id
    }))
  } catch (err) {
    console.error('Failed to load collect tasks', err)
  } finally {
    collectLoading.value = false
  }
}

async function loadBenchmarkTasks() {
  tasksLoading.value = true
  try {
    const res = await listBenchmarkTasks()
    const data = res.data ?? res
    benchmarkTasks.value = Array.isArray(data) ? data : (data.tasks ?? data.items ?? [])
  } catch (err) {
    console.error('Failed to load benchmark tasks', err)
  } finally {
    tasksLoading.value = false
  }
}

async function pollProgress() {
  const running = benchmarkTasks.value.filter((t) => t.status === 'running')
  if (running.length === 0) {
    runningBenchmarks.value = []
    return
  }
  const results: any[] = []
  for (const t of running) {
    try {
      const res = await getBenchmarkProgress(t.task_id)
      const data = res.data ?? res
      results.push({ ...t, ...data })
    } catch {
      results.push(t)
    }
  }
  runningBenchmarks.value = results

  const allDone = results.every((r) => r.progress >= 1 || r.status === 'completed')
  if (allDone) {
    stopPolling()
    await loadBenchmarkTasks()
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await pollProgress()
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleStart() {
  if (!form.name) {
    message.warning('请输入测试名称')
    return
  }
  if (!form.source_task_id) {
    message.warning('请选择源任务')
    return
  }
  starting.value = true
  try {
    await startBenchmark({
      name: form.name,
      source_task_id: form.source_task_id,
      target_host: form.target_host,
      target_port: form.target_port ?? 8080,
      concurrency: form.concurrency ?? 1,
      replay_mode: form.replay_mode,
      delay_ms: form.delay_ms ?? 0,
      timeout_s: form.timeout_s ?? 60
    })
    message.success('测试已启动')
    await loadBenchmarkTasks()
    startPolling()
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '启动测试失败')
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCollectTasks(), loadBenchmarkTasks()])
  const hasRunning = benchmarkTasks.value.some((t) => t.status === 'running')
  if (hasRunning) {
    await pollProgress()
    startPolling()
  }
})

onUnmounted(stopPolling)
</script>


<style scoped>
.benchmark-page {
  max-width: 1400px;
}

.benchmark-status-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.running-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.running-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-bar-label {
  color: #8c8c8c;
  font-size: 13px;
}

.running-name {
  color: #1f1f1f;
  font-weight: 500;
  font-size: 14px;
}

.running-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.running-detail {
  color: #8c8c8c;
  font-size: 12px;
  white-space: nowrap;
}

.table-card {
  margin-top: 8px;
}
</style>
