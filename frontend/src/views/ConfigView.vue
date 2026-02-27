<template>
  <div class="config-page">
    <h1 class="page-title">服务配置</h1>

    <n-card class="glass-card" :bordered="false">
      <!-- Current config summary bar -->
      <div class="config-status-bar" v-if="currentConfig && !loading">
        <div class="status-bar-item">
          <span class="status-bar-label">当前目标</span>
          <span class="status-bar-value">{{ currentConfig.target_host ?? '-' }}:{{ currentConfig.target_port ?? '-' }}</span>
        </div>
        <div class="status-bar-item">
          <span class="status-bar-label">API 类型</span>
          <n-tag :type="currentConfig.api_type === 'openai_compatible' ? 'info' : 'warning'" size="small" :bordered="false">
            {{ currentConfig.api_type ?? '-' }}
          </n-tag>
        </div>
        <template v-if="currentConfig.api_type === 'custom'">
          <div class="status-bar-item">
            <span class="status-bar-label">JSONPath</span>
            <span class="status-bar-value mono">{{ currentConfig.custom_tokens_jsonpath ?? '-' }}</span>
          </div>
        </template>
      </div>

      <n-divider v-if="currentConfig && !loading" style="margin: 16px 0" />

      <!-- Edit form -->
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="120px"
        style="max-width: 560px"
      >
        <n-form-item label="目标主机" path="target_host">
          <n-input v-model:value="formData.target_host" placeholder="例如 127.0.0.1 或 api.example.com" />
        </n-form-item>
        <n-form-item label="目标端口" path="target_port">
          <n-input-number
            v-model:value="formData.target_port"
            :min="1"
            :max="65535"
            placeholder="e.g. 8080"
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="API 类型" path="api_type">
          <n-select
            v-model:value="formData.api_type"
            :options="apiTypeOptions"
            placeholder="选择 API 类型"
          />
        </n-form-item>
        <n-form-item
          v-if="formData.api_type === 'custom'"
          label="Tokens JSONPath"
          path="custom_tokens_jsonpath"
        >
          <n-input
            v-model:value="formData.custom_tokens_jsonpath"
            placeholder="e.g. $.choices[0].delta.content"
          />
        </n-form-item>
        <n-form-item label=" ">
          <n-button
            type="primary"
            :loading="saving"
            class="accent-btn"
            @click="handleSave"
          >
            保存配置
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { getProxyConfig, setProxyConfig } from '../api'

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const saving = ref(false)
const currentConfig = ref<any>(null)

const formData = reactive({
  target_host: '',
  target_port: 8080 as number | null,
  api_type: 'openai_compatible' as string,
  custom_tokens_jsonpath: ''
})

const apiTypeOptions = [
  { label: 'OpenAI Compatible', value: 'openai_compatible' },
  { label: 'Custom', value: 'custom' }
]

const rules: FormRules = {
  target_host: { required: true, message: '请输入目标主机', trigger: 'blur' },
  target_port: { required: true, type: 'number', message: '请输入目标端口', trigger: 'blur' },
  api_type: { required: true, message: '请选择 API 类型', trigger: 'change' }
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await getProxyConfig()
    const data = res.data ?? res
    currentConfig.value = data
    if (data) {
      formData.target_host = data.target_host ?? ''
      formData.target_port = data.target_port ?? 8080
      formData.api_type = data.api_type ?? 'openai_compatible'
      formData.custom_tokens_jsonpath = data.custom_tokens_jsonpath ?? ''
    }
  } catch (err) {
    console.error('Failed to load proxy config', err)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload: any = {
      target_host: formData.target_host,
      target_port: formData.target_port,
      api_type: formData.api_type
    }
    if (formData.api_type === 'custom') {
      payload.custom_tokens_jsonpath = formData.custom_tokens_jsonpath
    }
    await setProxyConfig(payload)
    message.success('配置保存成功')
    await loadConfig()
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '配置保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.config-page {
  max-width: 800px;
}

.config-status-bar {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.status-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-bar-label {
  color: #8c8c8c;
  font-size: 13px;
}

.status-bar-value {
  color: #1f1f1f;
  font-size: 14px;
  font-weight: 500;
}

.status-bar-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #1677ff;
  font-size: 13px;
}
</style>
