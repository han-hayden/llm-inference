/**
 * Mock data for frontend development.
 * Activated when VITE_USE_MOCK=true in .env.development
 *
 * Uses axios request interceptor to short-circuit API calls and return fake data.
 */
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// ============ Seed data ============

let mockProxyConfig: Record<string, any> = {
  target_host: '127.0.0.1',
  target_port: 8080,
  api_type: 'openai_compatible',
  custom_tokens_jsonpath: '',
}

const MOCK_TASKS = [
  {
    task_id: 'task-baseline-gpt4o-20260201',
    name: 'baseline-gpt4o-20260201',
    type: 'collect',
    status: 'completed',
    record_count: 256,
    created_at: '2026-02-01 10:30:00',
  },
  {
    task_id: 'task-optimized-gpt4o-20260210',
    name: 'optimized-gpt4o-20260210',
    type: 'collect',
    status: 'completed',
    record_count: 256,
    created_at: '2026-02-10 14:20:00',
  },
  {
    task_id: 'task-baseline-deepseek-20260215',
    name: 'baseline-deepseek-20260215',
    type: 'collect',
    status: 'completed',
    record_count: 128,
    created_at: '2026-02-15 09:00:00',
  },
  {
    task_id: 'task-bench-concurrency-20260220',
    name: 'bench-concurrency-20260220',
    type: 'benchmark',
    status: 'completed',
    record_count: 512,
    created_at: '2026-02-20 16:45:00',
  },
]

function rand(min: number, max: number) {
  return Math.round((Math.random() * (max - min) + min) * 100) / 100
}

function randInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function buildMetricsSummary() {
  return {
    ttft_avg: rand(120, 280),
    ttft_p50: rand(100, 200),
    ttft_p90: rand(250, 400),
    ttft_p99: rand(450, 800),
    tpot_avg: rand(15, 35),
    tpot_p50: rand(12, 28),
    tpot_p90: rand(30, 55),
    tpot_p99: rand(55, 90),
    tps_avg: rand(35, 75),
    tps_p50: rand(40, 70),
    tps_p90: rand(25, 40),
    tps_p99: rand(15, 30),
    e2e_avg: rand(800, 2500),
    e2e_p50: rand(600, 2000),
    e2e_p90: rand(2000, 4000),
    e2e_p99: rand(4000, 6000),
  }
}

function buildDistributions() {
  return {
    context_length: {
      labels: ['0-512', '512-1K', '1K-2K', '2K-4K', '4K-8K', '8K-16K', '16K+'],
      values: [randInt(5, 20), randInt(15, 40), randInt(30, 60), randInt(40, 80), randInt(20, 50), randInt(10, 30), randInt(3, 15)],
    },
    response_latency: {
      labels: ['0-200', '200-500', '500-1K', '1K-2K', '2K-3K', '3K-5K', '5K+'],
      values: [randInt(10, 30), randInt(25, 55), randInt(40, 70), randInt(30, 60), randInt(15, 35), randInt(8, 20), randInt(2, 10)],
    },
    cache_hit_rate: {
      labels: ['0%', '0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
      values: [randInt(15, 30), randInt(10, 25), randInt(20, 40), randInt(30, 55), randInt(25, 45), randInt(35, 65)],
    },
  }
}

function buildSuggestions() {
  return [
    {
      title: '启用 KV Cache 前缀复用',
      content: '检测到约 62% 的请求具有相同的 System Prompt 前缀（平均 1,200 tokens）。启用 Prefix Caching 后预计可将 TTFT 降低 40-55%，同时减少 GPU 显存占用约 15%。建议在推理引擎配置中开启 enable_prefix_caching=true。',
    },
    {
      title: '优化批处理调度策略',
      content: '当前 max_batch_size=32，但监测到高峰期平均排队等待时间为 450ms。建议将 max_batch_size 提升至 64 并启用 continuous batching，预计可将 P90 端到端延迟从 3.8s 降至 2.5s，吞吐量提升约 30%。',
    },
    {
      title: '调整量化精度',
      content: '当前模型使用 FP16 推理，GPU 显存利用率达 92%。建议尝试 INT8/AWQ 量化，在保持输出质量（perplexity 增幅 < 0.5%）的前提下，可将显存占用降低约 45%，TPS 提升 20-35%。',
    },
    {
      title: '增加 Tensor Parallelism',
      content: '检测到单次推理的 TPOT P99 为 85ms，解码阶段成为瓶颈。如有多 GPU 资源，建议将 tensor_parallel_size 从 1 提升至 2，预计可将 TPOT 降低 35-40%，显著改善长文本生成场景的用户体验。',
    },
  ]
}

function buildCompareResult() {
  const n = 30
  const baselineTTFT = Array.from({ length: n }, () => rand(150, 350))
  const optimizedTTFT = Array.from({ length: n }, () => rand(80, 220))
  const baselineDecode = Array.from({ length: n }, () => rand(30, 60))
  const optimizedDecode = Array.from({ length: n }, () => rand(45, 85))

  return {
    ttft_reduction: rand(0.2, 0.45),
    tps_increase: rand(0.15, 0.4),
    tpot_reduction: rand(0.1, 0.35),
    e2e_reduction: rand(0.15, 0.38),
    baseline_ttft: baselineTTFT,
    optimized_ttft: optimizedTTFT,
    baseline_decode_speed: baselineDecode,
    optimized_decode_speed: optimizedDecode,
  }
}

function buildPerformanceData(page: number, size: number) {
  const total = 256
  const items = Array.from({ length: Math.min(size, total - (page - 1) * size) }, (_, i) => ({
    id: (page - 1) * size + i + 1,
    model: 'gpt-4o-2026-01-01',
    prompt_tokens: randInt(100, 8000),
    cached_tokens: randInt(0, 4000),
    completion_tokens: randInt(50, 2000),
    ttft_ms: rand(80, 500),
    tpot_ms: rand(10, 60),
    tps: rand(20, 90),
    e2e_latency_ms: rand(500, 5000),
    arrival_time: `2026-02-01 ${String(randInt(8, 22)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}`,
  }))
  return { items, total }
}

function buildQAData(page: number, size: number) {
  const total = 256
  const sampleQuestions = [
    '请解释量子计算的基本原理',
    '如何优化 Python 代码的性能？',
    '什么是 Transformer 架构？',
    '请用 Rust 实现一个简单的 HTTP 服务器',
    '解释 CAP 定理及其在分布式系统中的应用',
    '如何设计一个高可用的微服务架构？',
    'KV Cache 的工作原理是什么？',
    '请比较 gRPC 和 REST API 的优缺点',
  ]
  const items = Array.from({ length: Math.min(size, total - (page - 1) * size) }, (_, i) => ({
    id: (page - 1) * size + i + 1,
    model: 'gpt-4o-2026-01-01',
    messages: sampleQuestions[i % sampleQuestions.length],
    response_content: `这是对"${sampleQuestions[i % sampleQuestions.length]}"的模拟回答，包含详细的技术分析和建议...（此处省略约 ${randInt(200, 800)} 字）`,
  }))
  return { items, total }
}

// ============ Route matching & response ============

interface MockRoute {
  method: string
  pattern: RegExp
  handler: (match: RegExpMatchArray, config: InternalAxiosRequestConfig) => any
}

const routes: MockRoute[] = [
  // Auth
  {
    method: 'post',
    pattern: /\/api\/auth\/login$/,
    handler: () => ({ access_token: 'mock-token-abc123', token_type: 'bearer' }),
  },
  // Config
  {
    method: 'get',
    pattern: /\/api\/config\/proxy$/,
    handler: () => ({ ...mockProxyConfig }),
  },
  {
    method: 'post',
    pattern: /\/api\/config\/proxy$/,
    handler: (_m, config) => {
      const body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
      if (body) {
        mockProxyConfig = { ...mockProxyConfig, ...body }
      }
      return { status: 'ok' }
    },
  },
  // Collect
  {
    method: 'post',
    pattern: /\/api\/collect\/start$/,
    handler: () => ({ task_id: 'task-mock-' + Date.now(), status: 'running' }),
  },
  {
    method: 'post',
    pattern: /\/api\/collect\/stop$/,
    handler: () => ({ status: 'stopped' }),
  },
  {
    method: 'get',
    pattern: /\/api\/collect\/status$/,
    handler: () => ({ status: 'idle', task_id: null, collected_count: 0, elapsed_seconds: 0, progress: null }),
  },
  {
    method: 'get',
    pattern: /\/api\/collect\/tasks$/,
    handler: () => MOCK_TASKS.filter((t) => t.type === 'collect'),
  },
  // Files
  {
    method: 'get',
    pattern: /\/api\/files\/tasks$/,
    handler: () => ({ tasks: MOCK_TASKS }),
  },
  {
    method: 'get',
    pattern: /\/api\/files\/([^/]+)\/performance$/,
    handler: (_m, config) => {
      const page = Number(config.params?.page) || 1
      const size = Number(config.params?.size) || 20
      return buildPerformanceData(page, size)
    },
  },
  {
    method: 'get',
    pattern: /\/api\/files\/([^/]+)\/qa$/,
    handler: (_m, config) => {
      const page = Number(config.params?.page) || 1
      const size = Number(config.params?.size) || 20
      return buildQAData(page, size)
    },
  },
  {
    method: 'get',
    pattern: /\/api\/files\/([^/]+)\/summary$/,
    handler: () => ({ total_records: 256, model: 'gpt-4o', duration_seconds: 1820 }),
  },
  // Metrics
  {
    method: 'get',
    pattern: /\/api\/metrics\/([^/]+)\/summary$/,
    handler: () => ({ data: buildMetricsSummary() }),
  },
  {
    method: 'get',
    pattern: /\/api\/metrics\/([^/]+)\/distributions$/,
    handler: () => ({ data: buildDistributions() }),
  },
  // Benchmark
  {
    method: 'get',
    pattern: /\/api\/benchmark\/tasks$/,
    handler: () => MOCK_TASKS.filter((t) => t.type === 'benchmark'),
  },
  // Compare
  {
    method: 'get',
    pattern: /\/api\/compare$/,
    handler: () => buildCompareResult(),
  },
  // Report
  {
    method: 'post',
    pattern: /\/api\/report\/generate$/,
    handler: () => ({ report_id: 'report-mock-' + Date.now(), status: 'completed' }),
  },
  {
    method: 'get',
    pattern: /\/api\/report\/list$/,
    handler: () => ([]),
  },
  // Analysis
  {
    method: 'get',
    pattern: /\/api\/analysis\/engines$/,
    handler: () => ([{ id: 'default', name: 'Built-in Analyzer', status: 'ready' }]),
  },
  {
    method: 'get',
    pattern: /\/api\/analysis\/([^/]+)\/suggestions$/,
    handler: () => ({ data: buildSuggestions() }),
  },
]

// ============ Install ============

export function setupMock(axiosInstance: AxiosInstance) {
  axiosInstance.interceptors.request.use((config) => {
    const method = (config.method ?? 'get').toLowerCase()
    const url = config.url ?? ''

    for (const route of routes) {
      if (route.method !== method) continue
      const match = url.match(route.pattern)
      if (match) {
        // Simulate network delay
        const adapter = () =>
          new Promise<any>((resolve) => {
            setTimeout(() => {
              resolve({
                data: route.handler(match, config),
                status: 200,
                statusText: 'OK',
                headers: { 'content-type': 'application/json' },
                config,
              })
            }, randInt(100, 400))
          })

        config.adapter = adapter
        break
      }
    }

    return config
  })

  console.log('%c[Mock] API mock enabled — all requests return fake data', 'color: #00f0ff; font-weight: bold')
}
