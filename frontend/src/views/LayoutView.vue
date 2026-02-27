<template>
  <n-layout has-sider class="layout-root">
    <n-layout-sider
      bordered
      :width="220"
      :collapsed-width="0"
      collapse-mode="width"
      class="layout-sider"
      content-class="sider-content"
    >
      <div class="sider-header">
        <div class="app-logo">
          <svg viewBox="0 0 28 28" width="28" height="28" fill="none">
            <rect width="28" height="28" rx="6" fill="#1677ff"/>
            <path d="M8 14l4 4 8-8" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="app-info">
          <div class="app-title">AICP 性能测试</div>
          <div class="app-subtitle">LLM Inference Platform</div>
        </div>
      </div>
      <n-menu
        :value="activeKey"
        :options="menuOptions"
        :root-indent="20"
        class="sider-menu"
        @update:value="handleMenuSelect"
      />
      <div class="sider-footer">
        <div class="user-info">
          <n-avatar :size="28" round style="background: #1677ff; font-size: 12px;">A</n-avatar>
          <span class="user-name">Administrator</span>
        </div>
        <n-button text size="small" class="logout-btn" @click="handleLogout">
          退出
        </n-button>
      </div>
    </n-layout-sider>
    <n-layout class="layout-main" content-class="main-content">
      <router-view />
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'

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
  background: #f0f2f5;
}

.layout-sider {
  background: #ffffff !important;
  border-right: 1px solid #f0f0f0 !important;
}

:deep(.sider-content) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sider-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.app-logo {
  flex-shrink: 0;
}

.app-info {
  min-width: 0;
}

.app-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f1f1f;
  white-space: nowrap;
}

.app-subtitle {
  font-size: 11px;
  color: #8c8c8c;
  white-space: nowrap;
}

.sider-menu {
  flex: 1;
  padding-top: 4px;
}

/* Active menu item: blue background + white text + left blue bar */
:deep(.n-menu-item-content--selected) {
  background: #1677ff !important;
  color: #ffffff !important;
  border-radius: 0 !important;
  margin: 0 !important;
}

:deep(.n-menu-item-content--selected::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #1677ff;
  border-radius: 0;
}

:deep(.n-menu .n-menu-item) {
  margin: 0 !important;
  border-radius: 0 !important;
}

:deep(.n-menu .n-menu-item-content) {
  border-radius: 0 !important;
  padding-left: 20px !important;
  height: 44px;
}

:deep(.n-menu .n-menu-item-content:hover:not(.n-menu-item-content--selected)) {
  background: #f5f5f5 !important;
  color: #1677ff !important;
}

:deep(.n-menu .n-menu-item-content--selected .n-menu-item-content__default-label) {
  color: #ffffff !important;
}

.sider-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name {
  font-size: 13px;
  color: #595959;
}

.logout-btn {
  color: #8c8c8c !important;
  font-size: 13px;
}

.logout-btn:hover {
  color: #ff4d4f !important;
}

.layout-main {
  background: #f0f2f5 !important;
}

:deep(.main-content) {
  padding: 24px 32px;
  overflow-y: auto;
  height: 100vh;
}
</style>
