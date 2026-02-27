<template>
  <div class="benchmark-page">
    <h1 class="page-title">基准测试</h1>

    <n-grid :x-gap="24" :cols="2" class="top-section">
      <n-gi>
        <n-card class="glass-card" :bordered="false" title="新建基准测试">
          <n-form label-placement="top" label-width="auto">
            <n-form-item label="测试名称">
              <n-input v-model:value="form.name" placeholder="例如 benchmark-gpt4o-v2" />
            </n-form-item>
            <n-form-item label="源任务">
              <n-select
                v-model:value="form.source_task_id"
                :options="collectTaskOptions"
                :loading="collectLoading"
                filterable
                placeholder="选择采集任务"
              />
            </n-form-item>
            <n-grid :x-gap="12" :cols="2">
              <n-gi>
                <n-form-item label="目标主机">
                  <n-input v-model:value="form.target_host" placeholder="e.g. 127.0.0.1" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="目标端口">
                  <n-input-number
                    v-model:value="form.target_port"
                    :min="1"
                    :max="65535"
                    placeholder="8080"
                    style="width: 100%"
                  />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-grid :x-gap="12" :cols="2">
              <n-gi>
                <n-form-item label="并发数">
                  <n-input-number
                    v-model:value="form.concurrency"
                    :min="1"
                    :max="500"
                    placeholder="1"
                    style="width: 100%"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="回放模式">
                  <n-select
                    v-model:value="form.replay_mode"
                    :options="replayModeOptions"
                  />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-grid :x-gap="12" :cols="2">
              <n-gi>
                <n-form-item label="延迟 (ms)">
                  <n-input-number
                    v-model:value="form.delay_ms"
                    :min="0"
                    placeholder="0"
                    style="width: 100%"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="超时 (s)">
                  <n-input-number
                    v-model:value="form.timeout_s"
                    :min="1"
                    placeholder="60"
                    style="width: 100%"
                  />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-button
              type="primary"
              class="accent-btn"
              :loading="starting"
              @click="handleStart"
            >
              开始测试
            </n-button>
          </n-form>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card class="glass-card" :bordered="false" title="运行中的测试">
          <div v-if="runningBenchmarks.length === 0" class="empty-text">
            暂无运行中的测试。
          </div>
          <div v-for="bm in runningBenchmarks" :key="bm.task_id" class="progress-item">
            <div class="progress-header">
              <span class="progress-name">{{ bm.name ?? bm.task_id }}</span>
              <n-tag type="success" size="small" :bordered="false">running</n-tag>
            </div>
            <n-progress
              type="line"
              :percentage="Math.min(Math.round((bm.progress ?? 0) * 100), 100)"
              :indicator-placement="'inside'"
              processing
              style="margin-top: 8px"
            />
            <div class="progress-detail">
              {{ bm.completed ?? 0 }} / {{ bm.total ?? '?' }} 请求
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

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

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 24px 0;
}

.top-section {
  margin-bottom: 24px;
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

.empty-text {
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 32px 0;
}

.progress-item {
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.progress-item:last-child {
  border-bottom: none;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-name {
  color: #ffffff;
  font-weight: 500;
  font-size: 14px;
}

.progress-detail {
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  margin-top: 4px;
}

.table-card {
  margin-top: 8px;
}
</style>
