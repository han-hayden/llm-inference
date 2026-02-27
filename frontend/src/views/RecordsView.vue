<template>
  <div class="records-page">
    <h1 class="page-title">测试记录</h1>

    <n-card class="glass-card" :bordered="false">
      <template #header>
        <div class="card-header-row">
          <span>所有任务记录</span>
          <n-button
            type="primary"
            class="accent-btn"
            :disabled="selectedKeys.length !== 2"
            @click="handleCompare"
          >
            对比选中 ({{ selectedKeys.length }}/2)
          </n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="tasks"
        :loading="loading"
        :row-key="(row: any) => row.task_id"
        :checked-row-keys="selectedKeys"
        :row-props="rowProps"
        :pagination="{ pageSize: 15 }"
        size="small"
        striped
        @update:checked-row-keys="handleCheck"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag } from 'naive-ui'
import type { DataTableColumns, DataTableRowKey } from 'naive-ui'
import { listTaskFiles } from '../api'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const tasks = ref<any[]>([])
const selectedKeys = ref<DataTableRowKey[]>([])

const columns: DataTableColumns<any> = [
  { type: 'selection', width: 48 },
  { title: '任务ID', key: 'task_id', width: 220, ellipsis: { tooltip: true } },
  { title: '名称', key: 'name', width: 200 },
  {
    title: '类型',
    key: 'type',
    width: 120,
    render(row) {
      const typeColor = row.type === 'collect' ? 'info' : row.type === 'benchmark' ? 'warning' : 'default'
      return h(NTag, { type: typeColor, size: 'small', bordered: false }, { default: () => row.type ?? '-' })
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render(row) {
      const color = row.status === 'running' ? 'success' : row.status === 'completed' ? 'info' : 'default'
      return h(NTag, { type: color, size: 'small', bordered: false }, { default: () => row.status ?? '-' })
    }
  },
  { title: '记录数', key: 'record_count', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 }
]

function rowProps(row: any) {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      router.push(`/records/${row.task_id}`)
    }
  }
}

function handleCheck(keys: DataTableRowKey[]) {
  if (keys.length > 2) {
    message.warning('最多选择 2 个任务进行对比')
    return
  }
  selectedKeys.value = keys
}

function handleCompare() {
  if (selectedKeys.value.length !== 2) {
    message.warning('请选择 2 个任务进行对比')
    return
  }
  const [baseline, optimized] = selectedKeys.value
  router.push(`/compare?baseline=${baseline}&optimized=${optimized}`)
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await listTaskFiles()
    const data = res.data ?? res
    tasks.value = Array.isArray(data) ? data : (data.tasks ?? data.items ?? [])
  } catch (err) {
    console.error('Failed to load task records', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.records-page {
  max-width: 1400px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.accent-btn[disabled] {
  opacity: 0.4;
}
</style>
