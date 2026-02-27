<template>
  <n-layout has-sider class="layout-root">
    <n-layout-sider
      bordered
      :width="240"
      :collapsed-width="0"
      collapse-mode="width"
      class="layout-sider"
      content-class="sider-content"
    >
      <div class="sider-header">
        <h2 class="app-title">AICP 性能测试工具</h2>
      </div>
      <n-menu
        :value="activeKey"
        :options="menuOptions"
        :root-indent="20"
        class="sider-menu"
        @update:value="handleMenuSelect"
      />
      <div class="sider-footer">
        <n-button quaternary block class="logout-btn" @click="handleLogout">
          退出登录
        </n-button>
      </div>
    </n-layout-sider>
    <n-layout class="layout-main" content-class="main-content">
      <router-view />
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import {
  NIcon
} from 'naive-ui'

const router = useRouter()
const route = useRoute()

const menuOptions: MenuOption[] = [
  { label: '服务配置', key: '/config' },
  { label: '性能分析', key: '/analysis' },
  { label: '性能压测', key: '/benchmark' },
  { label: '性能对比', key: '/compare' },
  { label: '测试记录', key: '/records' },
]

const activeKey = computed(() => {
  const path = route.path
  const match = menuOptions.find((opt) => opt.key === path)
  if (match) return match.key as string
  for (const opt of menuOptions) {
    if (path.startsWith(opt.key as string)) return opt.key as string
  }
  return '/config'
})

function handleMenuSelect(key: string) {
  router.push(key)
}

function handleLogout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.layout-root {
  height: 100vh;
  background: #0a0e1a;
}

.layout-sider {
  background: rgba(255, 255, 255, 0.02) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

:deep(.sider-content) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sider-header {
  padding: 24px 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.app-title {
  font-size: 17px;
  font-weight: 700;
  background: linear-gradient(135deg, #00f0ff, #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  white-space: nowrap;
}

.sider-menu {
  flex: 1;
  padding-top: 8px;
}

.sider-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.logout-btn {
  color: rgba(255, 255, 255, 0.45) !important;
}

.logout-btn:hover {
  color: #ff6b6b !important;
}

.layout-main {
  background: #0a0e1a !important;
}

:deep(.main-content) {
  padding: 24px 32px;
  overflow-y: auto;
  height: 100vh;
}
</style>
