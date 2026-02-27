<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#00f0ff',
    primaryColorHover: '#33f3ff',
    primaryColorPressed: '#00c8d6',
    bodyColor: '#0a0e1a',
    cardColor: 'rgba(255,255,255,0.05)',
    modalColor: '#111827',
    popoverColor: '#1a1e2e',
    tableColorStriped: 'rgba(255,255,255,0.02)',
    borderColor: 'rgba(255,255,255,0.1)',
    textColorBase: '#e2e8f0',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontFamilyMono: "'JetBrains Mono', 'Fira Code', monospace",
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  Card: {
    borderRadius: '12px',
  },
  DataTable: {
    thColor: 'rgba(255,255,255,0.05)',
    tdColor: 'transparent',
    borderColor: 'rgba(255,255,255,0.06)',
  },
}
</script>
