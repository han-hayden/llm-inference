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
    name: 'baseline-gpt4o-FP16-TP1',
    type: 'collect',
    status: 'completed',
    record_count: 500,
    created_at: '2026-02-01 10:30:00',
  },
  {
    task_id: 'task-optimized-gpt4o-20260210',
    name: 'optimized-gpt4o-INT8-TP2-PrefixCache',
    type: 'collect',
    status: 'completed',
    record_count: 500,
    created_at: '2026-02-10 14:20:00',
  },
  {
    task_id: 'task-baseline-deepseek-20260215',
    name: 'baseline-deepseek-FP16-TP1',
    type: 'collect',
    status: 'completed',
    record_count: 300,
    created_at: '2026-02-15 09:00:00',
  },
  {
    task_id: 'task-optimized-deepseek-20260218',
    name: 'optimized-deepseek-AWQ-TP4-ContBatch',
    type: 'collect',
    status: 'completed',
    record_count: 300,
    created_at: '2026-02-18 11:15:00',
  },
  {
    task_id: 'task-bench-concurrency-20260220',
    name: 'bench-concurrency-stress-test',
    type: 'benchmark',
    status: 'completed',
    record_count: 1000,
    created_at: '2026-02-20 16:45:00',
  },
]

/** Check if a task_id belongs to an optimized (post-tuning) run */
function isOptimizedTask(taskId: string): boolean {
  return taskId.includes('optimized')
}

function rand(min: number, max: number) {
  return Math.round((Math.random() * (max - min) + min) * 100) / 100
}

function randInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function buildMetricsSummary(taskId: string) {
  if (isOptimizedTask(taskId)) {
    // ── Optimized: INT8 quantization + TP2 + Prefix Caching + Continuous Batching ──
    return {
      ttft_avg: 92.4,    ttft_p50: 78.1,    ttft_p90: 163.5,   ttft_p99: 287.2,
      tpot_avg: 12.8,    tpot_p50: 10.5,    tpot_p90: 23.7,    tpot_p99: 41.3,
      tps_avg: 78.1,     tps_p50: 85.2,     tps_p90: 53.6,     tps_p99: 39.4,
      e2e_avg: 1580,     e2e_p50: 1290,     e2e_p90: 2950,     e2e_p99: 4620,
    }
  }
  // ── Baseline: FP16 / TP=1 / no caching / naive batching ──
  return {
    ttft_avg: 523.6,   ttft_p50: 448.2,   ttft_p90: 982.1,   ttft_p99: 1836.5,
    tpot_avg: 67.5,    tpot_p50: 57.8,    tpot_p90: 124.3,   tpot_p99: 208.7,
    tps_avg: 14.8,     tps_p50: 17.3,     tps_p90: 8.1,      tps_p99: 4.8,
    e2e_avg: 9180,     e2e_p50: 7450,     e2e_p90: 17820,    e2e_p99: 28350,
  }
}

function buildDistributions(taskId: string) {
  if (isOptimizedTask(taskId)) {
    return {
      context_length: {
        labels: ['0-512', '512-1K', '1K-2K', '2K-4K', '4K-8K', '8K-16K', '16K+'],
        values: [12, 28, 55, 82, 45, 22, 8],
      },
      response_latency: {
        // Most requests complete fast — heavy left skew
        labels: ['0-200', '200-500', '500-1K', '1K-2K', '2K-3K', '3K-5K', '5K+'],
        values: [85, 120, 95, 42, 12, 4, 1],
      },
      cache_hit_rate: {
        // Prefix caching ON → high hit rates
        labels: ['0%', '0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        values: [5, 8, 15, 35, 72, 118],
      },
    }
  }
  return {
    context_length: {
      labels: ['0-512', '512-1K', '1K-2K', '2K-4K', '4K-8K', '8K-16K', '16K+'],
      values: [10, 25, 52, 78, 43, 20, 7],
    },
    response_latency: {
      // No optimization → heavy right tail, lots of slow requests
      labels: ['0-200', '200-500', '500-1K', '1K-2K', '2K-3K', '3K-5K', '5K+'],
      values: [8, 18, 35, 68, 82, 95, 55],
    },
    cache_hit_rate: {
      // No prefix caching → almost all misses
      labels: ['0%', '0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
      values: [145, 52, 28, 15, 8, 3],
    },
  }
}

function buildSuggestions(taskId: string) {
  if (isOptimizedTask(taskId)) {
    return [
      {
        title: '优化效果确认：Prefix Caching 生效',
        content: '当前缓存命中率达 75.3%，TTFT 从基线的 523.6ms 降至 92.4ms（降幅 82.4%）。System Prompt 前缀（平均 1,200 tokens）已被有效复用。建议持续监控缓存命中率，若低于 60% 可考虑增大 KV Cache 池大小。',
      },
      {
        title: '优化效果确认：INT8 量化 + TP2 并行',
        content: '量化后 TPS 从 14.8 提升至 78.1（提升 5.3 倍），TPOT 从 67.5ms 降至 12.8ms（降幅 81.0%）。Perplexity 增幅仅 0.3%，输出质量无明显损失。GPU 显存利用率从 92% 降至 51%，剩余空间可支撑更大 batch size。',
      },
      {
        title: '进一步优化：启用 Speculative Decoding',
        content: '当前 TPOT P99 仍有 41.3ms，长输出场景（>1000 tokens）解码阶段占总延迟 60% 以上。建议引入 Draft Model（如 gpt-4o-mini）做 Speculative Decoding，预计可再将 TPOT 降低 30-40%，TPS 提升至 100+ tokens/s。',
      },
      {
        title: '进一步优化：动态批处理调参',
        content: '当前 continuous batching 的 max_num_seqs=128，但监测到峰值并发仅 64。建议将 max_num_seqs 调至 256 并启用 chunked prefill（chunk_size=512），预计可在不影响 P99 延迟的前提下将整体吞吐量再提升 20-30%。',
      },
    ]
  }
  return [
    {
      title: '强烈建议：启用 KV Cache 前缀复用',
      content: '检测到 78% 的请求共享相同 System Prompt 前缀（平均 1,200 tokens），但当前未启用 Prefix Caching，每次请求都需重新计算 Prefill。启用后预计 TTFT 可从 523.6ms 降至 80-120ms（降幅约 80%），显存占用可减少约 15%。配置方法：enable_prefix_caching=true。',
    },
    {
      title: '强烈建议：INT8/AWQ 量化降低解码延迟',
      content: '当前使用 FP16 推理，单卡 GPU 显存利用率达 92%，TPS 仅 14.8 tokens/s，TPOT 高达 67.5ms。建议部署 INT8 或 AWQ 量化版本，实测 perplexity 增幅 <0.5%，但可将显存占用降低约 45%，TPS 预计提升 3-5 倍至 50-80 tokens/s。',
    },
    {
      title: '强烈建议：增加 Tensor Parallelism 至 TP=2',
      content: '当前 TP=1 单卡推理，解码阶段 TPOT P99 达 208.7ms，成为端到端延迟的主要瓶颈。若有多 GPU 资源，将 tensor_parallel_size 提升至 2 可将计算并行度翻倍，TPOT 预计降低 40-50%，E2E P99 从 28.4s 降至 12-15s。',
    },
    {
      title: '建议：启用 Continuous Batching 替代 Static Batching',
      content: '当前使用 static batching（max_batch_size=32），高峰期排队等待时间平均 680ms，P90 排队时间达 1.5s。切换至 continuous batching 后，请求可在前一批次解码过程中动态加入，预计队列等待时间降至 50ms 以下，整体吞吐量提升 40-60%。',
    },
  ]
}

function buildCompareResult() {
  const n = 50
  // Baseline: high TTFT, slow decode speed
  const baselineTTFT = Array.from({ length: n }, () => rand(380, 720))
  const optimizedTTFT = Array.from({ length: n }, () => rand(55, 145))
  const baselineDecode = Array.from({ length: n }, () => rand(10, 22))
  const optimizedDecode = Array.from({ length: n }, () => rand(55, 105))

  return {
    ttft_reduction: 0.824,     // 82.4% reduction (523→92)
    tps_increase: 4.277,       // +427.7% increase (14.8→78.1, i.e. 5.3x)
    tpot_reduction: 0.810,     // 81.0% reduction (67.5→12.8)
    e2e_reduction: 0.828,      // 82.8% reduction (9180→1580)
    baseline_ttft: baselineTTFT,
    optimized_ttft: optimizedTTFT,
    baseline_decode_speed: baselineDecode,
    optimized_decode_speed: optimizedDecode,
  }
}

function buildPerformanceData(page: number, size: number, taskId: string) {
  const total = 500
  const optimized = isOptimizedTask(taskId)
  const count = Math.min(size, total - (page - 1) * size)
  if (count <= 0) return { items: [], total }

  const items = Array.from({ length: count }, (_, i) => {
    const promptTokens = randInt(200, 8000)
    if (optimized) {
      const cachedTokens = Math.round(promptTokens * rand(0.55, 0.85))
      return {
        id: (page - 1) * size + i + 1,
        model: 'gpt-4o-2026-01-01',
        prompt_tokens: promptTokens,
        cached_tokens: cachedTokens,
        completion_tokens: randInt(80, 1500),
        ttft_ms: rand(52, 168),
        tpot_ms: rand(8, 28),
        tps: rand(42, 110),
        e2e_latency_ms: rand(650, 3200),
        arrival_time: `2026-02-10 ${String(randInt(8, 22)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}`,
      }
    }
    return {
      id: (page - 1) * size + i + 1,
      model: 'gpt-4o-2026-01-01',
      prompt_tokens: promptTokens,
      cached_tokens: randInt(0, 50),
      completion_tokens: randInt(80, 1500),
      ttft_ms: rand(280, 1200),
      tpot_ms: rand(38, 145),
      tps: rand(6, 26),
      e2e_latency_ms: rand(4500, 22000),
      arrival_time: `2026-02-01 ${String(randInt(8, 22)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}:${String(randInt(0, 59)).padStart(2, '0')}`,
    }
  })
  return { items, total }
}

function buildQAData(page: number, size: number) {
  const total = 500
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
    handler: (m, config) => {
      const page = Number(config.params?.page) || 1
      const size = Number(config.params?.size) || 20
      return buildPerformanceData(page, size, m[1])
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
    handler: () => ({ total_records: 500, model: 'gpt-4o', duration_seconds: 1820 }),
  },
  // Metrics
  {
    method: 'get',
    pattern: /\/api\/metrics\/([^/]+)\/summary$/,
    handler: (m) => ({ data: buildMetricsSummary(m[1]) }),
  },
  {
    method: 'get',
    pattern: /\/api\/metrics\/([^/]+)\/distributions$/,
    handler: (m) => ({ data: buildDistributions(m[1]) }),
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
    handler: (m) => ({ data: buildSuggestions(m[1]) }),
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
