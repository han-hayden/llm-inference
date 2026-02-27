import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { noAuth: true },
  },
  {
    path: '/',
    component: () => import('../views/LayoutView.vue'),
    children: [
      { path: '', redirect: '/config' },
      { path: 'config', name: 'Config', component: () => import('../views/ConfigView.vue') },
      { path: 'analysis', name: 'Analysis', component: () => import('../views/AnalysisView.vue') },
      { path: 'records', name: 'Records', component: () => import('../views/RecordsView.vue') },
      { path: 'records/:taskId', name: 'RecordDetail', component: () => import('../views/RecordDetailView.vue'), props: true },
      { path: 'benchmark', name: 'Benchmark', component: () => import('../views/BenchmarkView.vue') },
      { path: 'compare', name: 'Compare', component: () => import('../views/CompareView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.noAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
