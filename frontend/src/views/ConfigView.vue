<template>
  <div class="config-page">
    <h1 class="page-title">代理配置</h1>

    <n-grid :x-gap="24" :cols="2">
      <n-gi>
        <n-card class="glass-card" :bordered="false" title="编辑配置">
          <n-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-placement="top"
            label-width="auto"
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
              label="自定义 Tokens JSONPath"
              path="custom_tokens_jsonpath"
            >
              <n-input
                v-model:value="formData.custom_tokens_jsonpath"
                placeholder="e.g. $.choices[0].delta.content"
              />
            </n-form-item>
            <n-form-item>
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
      </n-gi>

      <n-gi>
        <n-card class="glass-card" :bordered="false" title="当前生效配置">
          <n-spin :show="loading">
            <div v-if="currentConfig" class="config-display">
              <div class="config-item">
                <span class="config-label">目标主机</span>
                <span class="config-value">{{ currentConfig.target_host ?? '-' }}</span>
              </div>
              <n-divider style="margin: 12px 0" />
              <div class="config-item">
                <span class="config-label">目标端口</span>
                <span class="config-value">{{ currentConfig.target_port ?? '-' }}</span>
              </div>
              <n-divider style="margin: 12px 0" />
              <div class="config-item">
                <span class="config-label">API 类型</span>
                <n-tag :type="currentConfig.api_type === 'openai_compatible' ? 'info' : 'warning'" size="small" :bordered="false">
                  {{ currentConfig.api_type ?? '-' }}
                </n-tag>
              </div>
              <template v-if="currentConfig.api_type === 'custom'">
                <n-divider style="margin: 12px 0" />
                <div class="config-item">
                  <span class="config-label">Tokens JSONPath 路径</span>
                  <span class="config-value mono">{{ currentConfig.custom_tokens_jsonpath ?? '-' }}</span>
                </div>
              </template>
            </div>
            <div v-else class="config-empty">
              尚未加载配置。
            </div>
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>
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
  max-width: 1200px;
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

.config-display {
  padding: 4px 0;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-label {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

.config-value {
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
}

.config-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #00f0ff;
  font-size: 13px;
}

.config-empty {
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 32px 0;
}
</style>
