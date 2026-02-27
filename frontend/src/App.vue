<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#1677ff',
    primaryColorHover: '#4096ff',
    primaryColorPressed: '#0958d9',
    bodyColor: '#f0f2f5',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    tableColorStriped: '#fafafa',
    borderColor: '#e8e8e8',
    textColorBase: '#1f1f1f',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', sans-serif",
    fontFamilyMono: "'JetBrains Mono', 'Fira Code', monospace",
  },
  Button: {
    borderRadiusMedium: '6px',
  },
  Card: {
    borderRadius: '8px',
  },
  DataTable: {
    thColor: '#fafafa',
    tdColor: '#ffffff',
    borderColor: '#f0f0f0',
  },
}
</script>
