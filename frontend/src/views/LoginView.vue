<template>
  <div class="login-wrapper">
    <n-card class="login-card" :bordered="false">
      <div class="login-header">
        <svg viewBox="0 0 36 36" width="36" height="36" fill="none" style="margin-bottom: 12px">
          <rect width="36" height="36" rx="8" fill="#1677ff"/>
          <path d="M10 18l5 5 11-11" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h1 class="login-title">AICP 性能测试工具</h1>
        <p class="login-subtitle">请登录以继续</p>
      </div>
      <n-form ref="formRef" :model="formData" :rules="rules" @submit.prevent="handleLogin">
        <n-form-item path="username" label="用户名">
          <n-input
            v-model:value="formData.username"
            placeholder="请输入用户名"
            size="large"
            :input-props="{ autocomplete: 'username' }"
          />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="formData.password"
            type="password"
            placeholder="请输入密码"
            show-password-on="click"
            size="large"
            :input-props="{ autocomplete: 'current-password' }"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          class="login-btn"
          @click="handleLogin"
        >
          登 录
        </n-button>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { login } from '../api'

const router = useRouter()
const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formData = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

async function handleLogin() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const res = await login(formData.username, formData.password)
    const token = res.data?.token ?? res.token ?? res
    if (token && typeof token === 'string') {
      localStorage.setItem('token', token)
    } else if (res.data?.access_token) {
      localStorage.setItem('token', res.data.access_token)
    }
    message.success('登录成功')
    router.push('/')
  } catch (err: any) {
    message.error(err?.response?.data?.detail ?? err?.message ?? '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}

.login-card {
  width: 400px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 20px 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: #1f1f1f;
  margin: 0 0 6px 0;
}

.login-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 14px;
}

.login-btn {
  margin-top: 8px;
  background: #1677ff !important;
  border: none !important;
  font-weight: 500;
}

.login-btn:hover {
  background: #4096ff !important;
}
</style>
