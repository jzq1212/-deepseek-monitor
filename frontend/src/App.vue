<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <span class="dot live"></span>
        <div class="mode-switch">
          <button :class="{ active: provider === 'deepseek' }" @click="switchProvider('deepseek')">DeepSeek</button>
          <button :class="{ active: provider === 'openrouter' }" @click="switchProvider('openrouter')">OpenRouter</button>
        </div>
      </div>
      <div class="header-right">
        <button class="btn-icon" @click="showHistoryModal = true" title="补录历史余额">🕐</button>
        <span class="time">{{ lastRefresh || '--:--:--' }}</span>
        <button class="btn-refresh" @click="refresh" :disabled="loading">
          <span :class="{ spinning: loading }">⟳</span>
        </button>
      </div>
    </header>

    <!-- History Modal -->
    <div class="modal-overlay" v-if="showHistoryModal" @click.self="showHistoryModal = false">
      <div class="modal">
        <h3>补录历史余额</h3>
        <p class="modal-desc">{{ provider === 'deepseek' ? '从 DeepSeek 官网 Billing 页面找到历史余额，逐条补录即可看到消费趋势。' : '从 OpenRouter 页面找到历史余额，逐条补录即可看到额度趋势。' }}</p>
        <div class="history-list">
          <div class="history-row header-row">
            <span>日期</span>
            <span v-if="provider === 'deepseek'">余额</span>
            <template v-else>
              <span>剩余</span><span>已用</span><span>上限</span>
            </template>
            <span></span>
          </div>
          <div v-for="(h, i) in history" :key="i" class="history-row" :class="{ 'or-row': provider === 'openrouter' }">
            <span>{{ h.date }}</span>
            <template v-if="provider === 'deepseek'">
              <span>¥{{ (h.total||0).toFixed(2) }}</span>
            </template>
            <template v-else>
              <span>{{ sym }}{{ (h.total||0).toFixed(2) }}</span>
              <span>{{ sym }}{{ (h.usage||0).toFixed(2) }}</span>
              <span>{{ sym }}{{ (h.limit||0).toFixed(2) }}</span>
            </template>
            <button class="btn-xs danger" @click="removeHistory(h.date)">删除</button>
          </div>
        </div>
        <div class="manual-row" :class="{ 'or-input': provider === 'openrouter' }">
          <input v-model="manualDate" type="date" class="mini-input" />
          <template v-if="provider === 'deepseek'">
            <input v-model="manualBalance" type="number" step="0.01" placeholder="余额" class="mini-input" />
          </template>
          <template v-else>
            <input v-model="manualBalance" type="number" step="0.01" placeholder="剩余额度" class="mini-input mini-sm" />
            <input v-model="manualUsage" type="number" step="0.01" placeholder="已用" class="mini-input mini-sm" />
            <input v-model="manualLimit" type="number" step="0.01" placeholder="上限" class="mini-input mini-sm" />
          </template>
          <button class="btn" @click="addHistory">添加</button>
        </div>
        <div class="modal-btns">
          <button class="btn secondary" @click="showHistoryModal = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- Key Switcher -->
    <div class="key-bar">
      <div class="key-select" @click="showKeyMenu = !showKeyMenu">
        <span>{{ currentKeyName || '请添加 Key' }}</span>
        <span class="arrow">▾</span>
      </div>
      <div class="key-actions">
        <button class="btn-sm" @click="showAddKey = true">+ 添加</button>
        <button class="btn-sm danger" @click="deleteCurrentKey" v-if="currentKeys.length > 0">删除</button>
      </div>
      <div class="key-menu" v-if="showKeyMenu">
        <div v-for="(k, i) in currentKeys" :key="i"
             class="key-item" :class="{ active: i === activeIndex }"
             @click="switchKey(i)">
          {{ k.name }}
          <span v-if="i === activeIndex" class="check">✓</span>
        </div>
      </div>
    </div>

    <!-- Add Key Modal -->
    <div class="modal-overlay" v-if="showAddKey" @click.self="showAddKey = false">
      <div class="modal">
        <h3>添加 {{ provider === 'deepseek' ? 'DeepSeek' : 'OpenRouter' }} API Key</h3>
        <input v-model="newKeyName" placeholder="名称（如：个人账号）" class="input" />
        <input v-model="newKeyValue" :placeholder="provider === 'deepseek' ? 'sk-...' : 'sk-or-v1-...'" type="password" class="input" />
        <div class="modal-btns">
          <button class="btn" @click="addKey">确认添加</button>
          <button class="btn secondary" @click="showAddKey = false">取消</button>
        </div>
        <a v-if="provider === 'deepseek'" href="https://platform.deepseek.com/api_keys" target="_blank" class="link">点此获取 Key →</a>
        <a v-else href="https://openrouter.ai/settings/keys" target="_blank" class="link">点此获取 OpenRouter Key →</a>
      </div>
    </div>

    <!-- Balance Cards: DeepSeek -->
    <div class="stat-row" v-if="balance && provider === 'deepseek'">
      <div class="stat-card glow-blue">
        <div class="stat-label">总余额</div>
        <div class="stat-value green digital" :key="balance.total.toFixed(2)">{{ sym }}{{ balance.total.toFixed(2) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">充值余额</div>
        <div class="stat-value">{{ sym }}{{ balance.topped_up.toFixed(2) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">赠送余额</div>
        <div class="stat-value dim">{{ sym }}{{ balance.granted.toFixed(2) }}</div>
      </div>
    </div>

    <!-- Balance Cards: OpenRouter -->
    <div class="stat-row" v-if="balance && provider === 'openrouter'">
      <div class="stat-card glow-blue">
        <div class="stat-label">剩余额度</div>
        <div class="stat-value green digital" :key="(balance.total||0).toFixed(2)">{{ sym }}{{ (balance.total||0).toFixed(2) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已用额度</div>
        <div class="stat-value">{{ sym }}{{ (balance.usage||0).toFixed(2) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">额度上限</div>
        <div class="stat-value dim">{{ sym }}{{ (balance.limit||0).toFixed(2) }}</div>
      </div>
    </div>

    <!-- Charts -->
    <BorderBox8 :color="['#00d4ff', '#409eff']" background-color="transparent" class="chart-spacer">
      <div class="chart-card" ref="trendCard">
        <div class="card-title">{{ provider === 'deepseek' ? '余额趋势 (近14天)' : '额度趋势 (近14天)' }}</div>
        <div class="chart-wrap" ref="trendChart"></div>
      </div>
    </BorderBox8>

    <div class="chart-row">
      <BorderBox8 :color="['#a855f7', '#7c3aed']" background-color="transparent" class="flex-half">
        <div class="chart-card half" ref="pricingCard">
          <div class="card-title">{{ provider === 'deepseek' ? '模型定价 (CNY/百万Token)' : '模型定价 (USD/百万Token)' }}</div>
          <div class="chart-wrap-small" ref="pricingChart"></div>
        </div>
      </BorderBox8>
      <BorderBox8 :color="['#22c55e', '#15803d']" background-color="transparent" class="flex-half">
        <div class="chart-card half">
          <div class="card-title">消费统计</div>

          <!-- DeepSeek 消费统计 -->
          <div class="cost-area" v-if="balance && provider === 'deepseek'">
            <div class="big-number">{{ estimatedTokens }}</div>
            <div class="sub-text">可用 Token</div>
            <div class="cost-divider"></div>
            <div class="cost-row">
              <span class="cost-label">今日</span>
              <span class="cost-value">{{ sym }}{{ todayCost.toFixed(4) }}</span>
            </div>
            <div class="cost-row">
              <span class="cost-label">近7天</span>
              <span class="cost-value">{{ sym }}{{ weekCost.toFixed(2) }}</span>
            </div>
            <div class="tip-text" v-if="!hasHistory">点击顶部 🕐 补录历史余额</div>
            <div class="tip-text" v-else>已积累 {{ history.length }} 天数据</div>
          </div>

          <!-- OpenRouter 消费统计 -->
          <div class="cost-area" v-if="balance && provider === 'openrouter'">
            <div class="big-number">{{ sym }}{{ (balance.total||0).toFixed(2) }}</div>
            <div class="sub-text">剩余额度</div>
            <div class="cost-divider"></div>
            <div class="cost-row">
              <span class="cost-label">已用</span>
              <span class="cost-value">{{ sym }}{{ (balance.usage||0).toFixed(2) }}</span>
            </div>
            <div class="cost-row">
              <span class="cost-label">上限</span>
              <span class="cost-value">{{ sym }}{{ (balance.limit||0).toFixed(2) }}</span>
            </div>
            <div class="tip-text" v-if="balance.is_free_tier">免费层用户</div>
            <div class="tip-text" v-else>付费用户</div>
          </div>
        </div>
      </BorderBox8>
    </div>

    <!-- Footer -->
    <footer class="footer" v-if="balance">
      <span v-if="provider === 'deepseek'">夜间优惠 00:30-08:30</span>
      <span v-else>OpenRouter {{ balance.is_free_tier ? '免费层' : '' }}</span>
      <span class="dim">{{ balance.currency }}</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { BorderBox8 } from 'datav-vue3'

// ── State ──────────────────────────────────
const provider = ref('deepseek')  // 'deepseek' | 'openrouter'
const loading = ref(false)
const balance = ref(null)
const history = ref([])
const dailyCost = ref({})
const keys = ref([])           // DeepSeek keys
const orKeys = ref([])         // OpenRouter keys
const activeIndex = ref(0)
const lastRefresh = ref('')
const showKeyMenu = ref(false)
const showAddKey = ref(false)
const newKeyName = ref('')
const newKeyValue = ref('')
const manualDate = ref('')
const manualBalance = ref('')
const manualUsage = ref('')
const manualLimit = ref('')
const showHistoryModal = ref(false)

// Refs
const trendCard = ref(null)
const trendChart = ref(null)
const pricingCard = ref(null)
const pricingChart = ref(null)

let trendInstance = null
let pricingInstance = null

// ── Computed ───────────────────────────────
const currentKeys = computed(() => {
  return provider.value === 'deepseek' ? keys.value : orKeys.value
})

const currentKeyName = computed(() => {
  const list = currentKeys.value
  if (activeIndex.value < list.length) return list[activeIndex.value].name
  return list.length > 0 ? list[0].name : ''
})

const sym = computed(() => {
  return balance.value?.currency === 'CNY' ? '¥' : '$'
})

const estimatedTokens = computed(() => {
  if (!balance.value || balance.value.total <= 0) return '0'
  if (provider.value === 'openrouter') return sym.value + balance.value.total.toFixed(2)
  const avgPrice = 1.0 * 0.75 + 2.0 * 0.25
  const tokens = balance.value.total / avgPrice * 1_000_000
  if (tokens >= 1_000_000) return (tokens / 1_000_000).toFixed(1) + 'M'
  if (tokens >= 1_000) return (tokens / 1_000).toFixed(1) + 'K'
  return Math.floor(tokens).toLocaleString()
})

const todayCost = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return dailyCost.value[today] || 0
})

const weekCost = computed(() => {
  return Object.values(dailyCost.value).reduce((a, b) => a + b, 0)
})

const hasHistory = computed(() => history.value.length >= 2)

// 初始化手动补录日期为昨天
onMounted(() => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  manualDate.value = d.toISOString().slice(0, 10)
})

async function addHistory() {
  if (!manualDate.value || !manualBalance.value) return
  try {
    const path = provider.value === 'deepseek' ? '/api/history' : '/api/openrouter/history'
    const body = provider.value === 'deepseek' ? {
      date: manualDate.value,
      total: parseFloat(manualBalance.value),
      topped_up: balance.value?.topped_up || 0,
      granted: balance.value?.granted || 0,
    } : {
      date: manualDate.value,
      total: parseFloat(manualBalance.value),
      usage: parseFloat(manualUsage.value) || 0,
      limit: parseFloat(manualLimit.value) || 0,
    }
    await API(path, { method: 'POST', body: JSON.stringify(body) })
    const d = new Date(manualDate.value)
    d.setDate(d.getDate() - 1)
    manualDate.value = d.toISOString().slice(0, 10)
    manualBalance.value = ''
    manualUsage.value = ''
    manualLimit.value = ''
    await refresh()
  } catch (e) { alert('补录失败: ' + e.message) }
}

// ── API Calls ──────────────────────────────
const API = (path, opts = {}) =>
  fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts })
    .then(r => {
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || 'Error') })
      return r.json()
    })

function apiPath(path) {
  if (provider.value === 'openrouter') return '/api/openrouter' + path
  return '/api' + path
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  try {
    if (provider.value === 'deepseek') {
      const data = await API('/api/balance')
      balance.value = data.balance
      history.value = data.history || []
      dailyCost.value = data.daily_cost || {}
    } else {
      const data = await API('/api/openrouter/balance')
      balance.value = data.balance
      history.value = data.history || []
      dailyCost.value = data.daily_cost || {}
    }
    lastRefresh.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('Refresh failed:', e)
  } finally {
    loading.value = false
  }
}

async function loadKeys() {
  try {
    const path = provider.value === 'deepseek' ? '/api/keys' : '/api/openrouter/keys'
    const data = await API(path)
    if (provider.value === 'deepseek') {
      keys.value = data.keys || []
    } else {
      orKeys.value = data.keys || []
    }
    activeIndex.value = data.active_index || 0
  } catch (e) { console.error(e) }
}

async function addKey() {
  if (!newKeyName.value.trim() || !newKeyValue.value.trim()) return
  try {
    const path = provider.value === 'deepseek' ? '/api/keys' : '/api/openrouter/keys'
    await API(path, {
      method: 'POST',
      body: JSON.stringify({ name: newKeyName.value.trim(), api_key: newKeyValue.value.trim() }),
    })
    showAddKey.value = false
    newKeyName.value = ''
    newKeyValue.value = ''
    await loadKeys()
    if (currentKeys.value.length === 1) activeIndex.value = 0
    await switchKey(currentKeys.value.length - 1)
  } catch (e) { alert('添加失败: ' + e.message) }
}

async function removeHistory(dateStr) {
  if (!confirm(`删除 ${dateStr} 的记录？`)) return
  // 补录一条 0 余额来覆盖（实际后端会去重）
  const updated = history.value.filter(h => h.date !== dateStr)
  // 通过保存空历史来删除
  try {
    history.value = updated
    const path = provider.value === 'deepseek' ? '/api/history/delete' : '/api/openrouter/history/delete'
    await API(path, {
      method: 'POST',
      body: JSON.stringify({ date: dateStr }),
    })
    await refresh()
  } catch (e) {
    await refresh()
  }
}

async function deleteCurrentKey() {
  const list = currentKeys.value
  const name = list[activeIndex.value]?.name
  if (!name || !confirm(`删除 Key "${name}"？`)) return
  try {
    const base = provider.value === 'deepseek' ? '/api/keys' : '/api/openrouter/keys'
    await API(`${base}/${encodeURIComponent(name)}`, { method: 'DELETE' })
    showKeyMenu.value = false
    await loadKeys()
    if (activeIndex.value >= list.length) activeIndex.value = Math.max(0, list.length - 1)
    await API(`${base}/active`, {
      method: 'PUT',
      body: JSON.stringify({ index: activeIndex.value }),
    })
    await refresh()
  } catch (e) { alert('删除失败: ' + e.message) }
}

async function switchKey(i) {
  activeIndex.value = i
  showKeyMenu.value = false
  const base = provider.value === 'deepseek' ? '/api/keys' : '/api/openrouter/keys'
  await API(`${base}/active`, { method: 'PUT', body: JSON.stringify({ index: i }) })
  await refresh()
}

async function switchProvider(p) {
  if (provider.value === p) return
  // 销毁旧图表实例
  try { trendInstance?.dispose() } catch (e) {}
  trendInstance = null
  try { pricingInstance?.dispose() } catch (e) {}
  pricingInstance = null
  provider.value = p
  balance.value = null
  history.value = []
  dailyCost.value = {}
  activeIndex.value = 0
  await nextTick()
  await loadKeys()
  if (currentKeys.value.length > 0) await refresh()
  else renderPricingChart()
}

// ── Charts ─────────────────────────────────
function renderCharts() {
  try {
    renderTrendChart()
    renderPricingChart()
  } catch (e) {
    console.error('Chart render error:', e)
  }
}

function renderTrendChart() {
  if (!trendChart.value) return
  if (!trendInstance) trendInstance = echarts.init(trendChart.value)

  const hist = history.value || []
  const dates = hist.map(h => h.date.slice(5))
  const totals = hist.map(h => h.total)

  const option = {
    backgroundColor: 'transparent',
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#1e2959' } },
      axisTick: { show: false },
      axisLabel: { color: '#6b7394', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1a2040', type: 'dashed' } },
      axisLabel: { color: '#6b7394', fontSize: 10 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111640',
      borderColor: '#1e2959',
      textStyle: { color: '#e0e6ff', fontSize: 12 },
    },
    series: [{
      type: 'line',
      data: totals,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#00d4ff', width: 2.5 },
      itemStyle: {
        color: '#00d4ff',
        borderColor: '#0a0e27',
        borderWidth: 1,
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' },
        ]),
      },
    }],
  }

  trendInstance.setOption(option, true)
}

function renderPricingChart() {
  if (!pricingChart.value) return
  if (!pricingInstance) pricingInstance = echarts.init(pricingChart.value)

  let models, inputData, outputData, cacheData, currency
  if (provider.value === 'deepseek') {
    models = ['V4 Flash', 'V4 Pro']
    inputData = [1.0, 3.0]
    outputData = [2.0, 6.0]
    cacheData = [0.02, 0.025]
    currency = '¥'
  } else {
    models = ['Ring 2.6 1T', 'Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4', 'Gemini 3.1 Pro']
    inputData = [0, 5.0, 3.0, 2.5, 1.25]
    outputData = [0, 25.0, 15.0, 15.0, 5.0]
    cacheData = [0, 0.5, 0.3, 0.25, 0.25]
    currency = '$'
  }

  const option = {
    backgroundColor: 'transparent',
    legend: {
      data: ['输入', '输出', '缓存命中'],
      textStyle: { color: '#6b7394', fontSize: 9 },
      top: 0,
      itemWidth: 10,
      itemHeight: 8,
    },
    grid: { left: 48, right: 14, top: 30, bottom: 28 },
    xAxis: {
      type: 'category',
      data: models,
      axisLine: { lineStyle: { color: '#1e2959' } },
      axisTick: { show: false },
      axisLabel: { color: '#e0e6ff', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: currency + '/M',
      nameTextStyle: { color: '#6b7394', fontSize: 8 },
      splitLine: { lineStyle: { color: '#1a2040', type: 'dashed' } },
      axisLabel: { color: '#6b7394', fontSize: 9 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111640',
      borderColor: '#1e2959',
      textStyle: { color: '#e0e6ff', fontSize: 11 },
      formatter: (params) => {
        let s = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          s += `${p.marker} ${p.seriesName}: <b>${currency}${p.value}</b>/百万<br/>`
        })
        return s
      },
    },
    series: [
      {
        name: '输入', type: 'bar', data: inputData,
        barWidth: '30%',
        barGap: '15%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409eff' }, { offset: 1, color: '#1d4ed8' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
        label: {
          show: true, position: 'top', color: '#6b7394', fontSize: 8,
          formatter: (p) => p.value >= 1 ? p.value.toFixed(1) : p.value.toFixed(3),
        },
      },
      {
        name: '输出', type: 'bar', data: outputData,
        barWidth: '30%',
        barGap: '15%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#a855f7' }, { offset: 1, color: '#7c3aed' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
        label: {
          show: true, position: 'top', color: '#6b7394', fontSize: 8,
          formatter: (p) => p.value >= 1 ? p.value.toFixed(1) : p.value.toFixed(3),
        },
      },
      {
        name: '缓存命中', type: 'bar', data: cacheData,
        barWidth: '30%',
        barGap: '15%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#22c55e' }, { offset: 1, color: '#15803d' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
        label: {
          show: true, position: 'top', color: '#6b7394', fontSize: 8,
          formatter: (p) => p.value.toFixed(3),
        },
      },
    ],
  }

  pricingInstance.setOption(option, true)
}

// ── Lifecycle ──────────────────────────────
let trendObserver = null
let pricingObserver = null
let clickOutside

onMounted(async () => {
  await loadKeys()
  if (currentKeys.value.length > 0) await refresh()
  else { await nextTick(); renderPricingChart() }

  // ResizeObserver 比 window.resize 更可靠（pywebview 兼容）
  if (trendChart.value) {
    trendObserver = new ResizeObserver(() => trendInstance?.resize())
    trendObserver.observe(trendChart.value)
  }
  if (pricingChart.value) {
    pricingObserver = new ResizeObserver(() => pricingInstance?.resize())
    pricingObserver.observe(pricingChart.value)
  }

  clickOutside = (e) => {
    if (!e.target.closest('.key-select') && !e.target.closest('.key-menu')) {
      showKeyMenu.value = false
    }
  }
  document.addEventListener('click', clickOutside)
})

onUnmounted(() => {
  trendObserver?.disconnect()
  pricingObserver?.disconnect()
  document.removeEventListener('click', clickOutside)
  trendInstance?.dispose()
  pricingInstance?.dispose()
})

// Auto-refresh every 30 min
let timer = setInterval(refresh, 30 * 60 * 1000)
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.dashboard {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding-bottom: 20px;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--green);
  box-shadow: 0 0 6px var(--green);
}
.dot.live { animation: pulse 2s infinite; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.title { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
.mode-switch {
  display: flex; gap: 2px; background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden;
}
.mode-switch button {
  background: transparent; border: none; color: var(--text-dim);
  padding: 4px 12px; cursor: pointer; font-size: 12px; font-weight: 600;
  transition: all 0.2s; white-space: nowrap;
}
.mode-switch button.active {
  background: var(--blue); color: #fff;
}
.mode-switch button:hover:not(.active) {
  color: var(--text);
}
.time { font-size: 11px; color: var(--text-dim); margin-right: 8px; }
.btn-icon {
  background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
  width: 32px; height: 32px; border-radius: 8px; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  margin-right: 6px;
}
.btn-icon:hover { border-color: var(--orange); }
.btn-refresh {
  background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
  width: 32px; height: 32px; border-radius: 8px; cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}
.btn-refresh:hover { border-color: var(--cyan); }
.spinning { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin {
 100% { transform: rotate(360deg); }
}

/* Key Bar */
.key-bar {
  position: relative; display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
}
.key-select {
  flex: 1; background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 6px 12px; cursor: pointer; font-size: 13px;
  display: flex; justify-content: space-between; align-items: center;
}
.key-select:hover { border-color: var(--blue); }
.arrow { color: var(--text-dim); font-size: 10px; }
.key-actions { display: flex; gap: 6px; }
.btn-sm {
  background: var(--card-bg); border: 1px solid var(--border); color: var(--text);
  padding: 6px 10px; border-radius: 6px; cursor: pointer; font-size: 11px;
}
.btn-sm:hover { border-color: var(--blue); }
.btn-sm.danger:hover { border-color: var(--red); color: var(--red); }
.key-menu {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 8px; margin-top: 4px; overflow: hidden;
}
.key-item {
  padding: 8px 12px; cursor: pointer; display: flex; justify-content: space-between;
  font-size: 13px;
}
.key-item:hover { background: rgba(64, 158, 255, 0.1); }
.key-item.active { color: var(--cyan); }
.check { color: var(--green); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200;
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; width: 380px; max-height: 90vh; overflow-y: auto;
}
.modal h3 { margin-bottom: 16px; font-size: 15px; }
.input {
  width: 100%; background: #0a0e27; border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 12px; color: var(--text); font-size: 13px;
  margin-bottom: 8px; outline: none;
}
.input:focus { border-color: var(--blue); }
.modal-btns { display: flex; gap: 8px; margin-top: 12px; }
.btn {
  background: var(--blue); color: #fff; border: none; padding: 8px 16px;
  border-radius: 6px; cursor: pointer; font-size: 13px;
}
.btn.secondary { background: var(--border); }
.link { display: block; margin-top: 12px; color: var(--cyan);
  font-size: 12px; text-align: center; }

/* Stat Cards */
.stat-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 10px;
}
.stat-card {
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px; text-align: center;
}
.stat-card.glow-blue { box-shadow: var(--glow-blue); border-color: rgba(64,158,255,0.3); }
.stat-label { font-size: 11px; color: var(--text-dim); margin-bottom: 4px; }
.stat-value { font-size: 18px; font-weight: 700; }
.stat-value.green { color: var(--green); }
.stat-value.dim { color: var(--text-dim); }
.stat-value.digital {
  animation: flipIn 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}
@keyframes flipIn {
  0% { transform: translateY(-60%); opacity: 0; }
  60% { transform: translateY(5%); }
  100% { transform: translateY(0); opacity: 1; }
}

/* Charts */
.chart-card {
  padding: 6px; margin-bottom: 0; width: 100%;
}
.card-title {
  font-size: 12px; color: var(--text-dim); margin-bottom: 8px;
}
.chart-wrap { width: 100%; min-height: 180px; height: 30vh; }
.chart-wrap-small { width: 100%; min-height: 140px; height: 25vh; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
.flex-half { min-height: 220px; }
.flex-half > .chart-card { flex: 1; }
.chart-spacer { margin-bottom: 8px; min-height: 240px; }

/* Cost Area */
.cost-area { text-align: center; padding: 4px 0; }
.big-number {
  font-size: 28px; font-weight: 800;
  background: linear-gradient(135deg, var(--cyan), var(--blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.sub-text { font-size: 11px; color: var(--text-dim); margin: 1px 0 10px; }
.cost-divider { width: 60%; height: 1px; background: var(--border); margin: 0 auto 10px; }
.cost-row { display: flex; justify-content: space-between; padding: 3px 16px; }
.cost-row .cost-label { font-size: 12px; color: var(--text-dim); }
.cost-row .cost-value { font-size: 16px; font-weight: 700; color: var(--text); }
.tip-text { font-size: 10px; color: var(--text-dim); margin-top: 6px; opacity: 0.6; }

/* History Modal */
.modal-desc { font-size: 12px; color: var(--text-dim); margin-bottom: 12px; line-height: 1.5; }
.history-list { max-height: 180px; overflow-y: auto; margin-bottom: 12px; }
.history-row {
  display: grid; grid-template-columns: 1fr 1fr 50px; gap: 8px;
  padding: 5px 8px; font-size: 12px; border-radius: 4px;
  align-items: center;
}
.history-row.or-row {
  grid-template-columns: 1fr 1fr 1fr 1fr 50px;
}
.history-row:hover { background: rgba(64,158,255,0.05); }
.history-row.header-row { color: var(--text-dim); font-size: 10px; }
.manual-row { display: flex; gap: 6px; justify-content: center; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
.mini-input {
  background: #0a0e27; border: 1px solid var(--border); border-radius: 4px;
  color: var(--text); font-size: 12px; padding: 6px 8px; width: 110px; outline: none;
}
.mini-sm { width: 72px; }
.mini-input:focus { border-color: var(--blue); }
.btn-xs {
  background: none; border: none; color: var(--text-dim); font-size: 10px;
  cursor: pointer; padding: 2px 6px;
}
.btn-xs:hover { color: var(--red); }
.btn-xs.danger { color: var(--text-dim); }
.btn-xs.danger:hover { color: var(--red); }

/* Footer */
.footer {
  display: flex; justify-content: space-between;
  font-size: 11px; color: var(--text-dim); margin-top: 4px;
}
.red { color: var(--red); }
</style>
