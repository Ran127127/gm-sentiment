<template>
  <div class="dashboard">
    <!-- 品牌概览卡片 -->
    <div class="brand-cards">
      <div
        v-for="item in overviewData"
        :key="item.brand.id"
        class="brand-card"
        :class="{ active: item.brand.id === brandId }"
        @click="$router.push(`/brand/${item.brand.id}`)"
      >
        <div class="brand-header">
          <span class="brand-name">{{ item.brand.name_cn }}</span>
          <span class="brand-en">{{ item.brand.name_en }}</span>
        </div>
        <div class="sentiment-index">
          <span class="index-value" :style="{ color: getIndexColor(item.sentiment_index) }">
            {{ item.sentiment_index }}
          </span>
          <span class="index-label">舆情指数</span>
        </div>
        <div class="brand-stats">
          <div class="stat-item">
            <span class="stat-value positive">{{ item.positive_ratio }}%</span>
            <span class="stat-label">正面</span>
          </div>
          <div class="stat-item">
            <span class="stat-value neutral">{{ item.neutral_ratio }}%</span>
            <span class="stat-label">中性</span>
          </div>
          <div class="stat-item">
            <span class="stat-value negative">{{ item.negative_ratio }}%</span>
            <span class="stat-label">负面</span>
          </div>
        </div>
        <div class="brand-change" :class="item.change > 0 ? 'up' : item.change < 0 ? 'down' : ''">
          <span v-if="item.change > 0">+{{ item.change }}</span>
          <span v-else-if="item.change < 0">{{ item.change }}</span>
          <span v-else>--</span>
          <span class="change-label">较昨日</span>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <div class="chart-card trend-card">
        <div class="card-header">
          <h3>情感趋势</h3>
          <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
            <el-radio-button :value="7">7天</el-radio-button>
            <el-radio-button :value="30">30天</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card source-card">
        <div class="card-header">
          <h3>平台分布</h3>
        </div>
        <div ref="sourceChartRef" class="chart-container"></div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card keyword-card">
        <div class="card-header">
          <h3>热门关键词</h3>
        </div>
        <div ref="keywordChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card radar-card">
        <div class="card-header">
          <h3>车型维度对比</h3>
          <el-select v-model="radarBrandId" size="small" placeholder="选择品牌" @change="loadRadar">
            <el-option label="别克" :value="1" />
            <el-option label="凯迪拉克" :value="2" />
            <el-option label="雪佛兰" :value="3" />
          </el-select>
        </div>
        <div ref="radarChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- 热门文章 -->
    <div class="section-card">
      <div class="card-header">
        <h3>热门讨论 TOP 10</h3>
        <el-button type="primary" link @click="$router.push('/articles')">
          查看全部
        </el-button>
      </div>
      <el-table :data="hotArticles" stripe style="width: 100%">
        <el-table-column label="平台" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="300">
          <template #default="{ row }">
            <a :href="row.url" target="_blank" class="article-link">{{ row.title }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="brand_name" label="品牌" width="100" />
        <el-table-column label="情感" width="80">
          <template #default="{ row }">
            <el-tag
              :type="getSentimentType(row.sentiment?.label)"
              size="small"
            >
              {{ getSentimentLabel(row.sentiment?.label) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="互动" width="100">
          <template #default="{ row }">
            {{ formatCount(row.like_count + row.comment_count + row.share_count) }}
          </template>
        </el-table-column>
        <el-table-column label="时间" width="100">
          <template #default="{ row }">
            {{ formatDate(row.publish_time) }}
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 智能建议 -->
    <div class="section-card">
      <div class="card-header">
        <h3>智能建议</h3>
        <el-button type="primary" link @click="$router.push('/recommendations')">
          查看全部
        </el-button>
      </div>
      <div class="recommendations-list">
        <div
          v-for="rec in recommendations"
          :key="rec.id"
          class="recommendation-item"
          :class="rec.priority"
        >
          <div class="rec-priority">
            <el-tag :type="getPriorityType(rec.priority)" size="small">
              {{ getPriorityLabel(rec.priority) }}
            </el-tag>
          </div>
          <div class="rec-content">
            <p class="rec-title">{{ rec.title }}</p>
            <p class="rec-meta">
              {{ rec.brand_name }}
              <span v-if="rec.model_name"> / {{ rec.model_name }}</span>
              <span class="rec-date">{{ rec.date }}</span>
            </p>
          </div>
        </div>
        <el-empty v-if="!recommendations.length" description="暂无建议" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { getOverview, getSentimentTrend, getSourceDistribution, getKeywordCloud, getModelComparison, getHotArticles } from '../api/dashboard'
import { getRecommendations } from '../api/recommendation'

const props = defineProps({
  brandId: { type: Number, default: 0 },
})

const overviewData = ref([])
const hotArticles = ref([])
const recommendations = ref([])
const trendDays = ref(7)
const radarBrandId = ref(1)

const trendChartRef = ref(null)
const sourceChartRef = ref(null)
const keywordChartRef = ref(null)
const radarChartRef = ref(null)

let trendChart = null
let sourceChart = null
let keywordChart = null
let radarChart = null

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', handleResize)
})

watch(() => props.brandId, () => loadAll())

async function loadAll() {
  await Promise.all([
    loadOverview(),
    loadTrend(),
    loadSource(),
    loadKeyword(),
    loadRadar(),
    loadHotArticles(),
    loadRecommendations(),
  ])
}

function handleResize() {
  trendChart?.resize()
  sourceChart?.resize()
  keywordChart?.resize()
  radarChart?.resize()
}

async function loadOverview() {
  try {
    const res = await getOverview()
    overviewData.value = res.data || []
  } catch (e) {
    console.error('加载概览失败', e)
  }
}

async function loadTrend() {
  try {
    const params = { days: trendDays.value }
    if (props.brandId) params.brand_id = props.brandId
    const res = await getSentimentTrend(params)
    renderTrendChart(res.data || [])
  } catch (e) {
    console.error('加载趋势失败', e)
  }
}

async function loadSource() {
  try {
    const params = {}
    if (props.brandId) params.brand_id = props.brandId
    const res = await getSourceDistribution(params)
    renderSourceChart(res.data || [])
  } catch (e) {
    console.error('加载来源分布失败', e)
  }
}

async function loadKeyword() {
  try {
    const params = { days: 7 }
    if (props.brandId) params.brand_id = props.brandId
    const res = await getKeywordCloud(params)
    renderKeywordChart(res.data || [])
  } catch (e) {
    console.error('加载关键词失败', e)
  }
}

async function loadRadar() {
  try {
    const res = await getModelComparison({ brand_id: radarBrandId.value })
    renderRadarChart(res.data || [])
  } catch (e) {
    console.error('加载雷达图失败', e)
  }
}

async function loadHotArticles() {
  try {
    const params = { limit: 10 }
    if (props.brandId) params.brand_id = props.brandId
    const res = await getHotArticles(params)
    hotArticles.value = res.data || []
  } catch (e) {
    console.error('加载热门文章失败', e)
  }
}

async function loadRecommendations() {
  try {
    const params = {}
    if (props.brandId) params.brand_id = props.brandId
    const res = await getRecommendations(params)
    recommendations.value = (res.data || []).slice(0, 5)
  } catch (e) {
    console.error('加载建议失败', e)
  }
}

// ========== 图表渲染 ==========

function renderTrendChart(data) {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  const dates = data.map(d => d.date)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { top: 10, right: 20, bottom: 40, left: 50 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [
      { name: '正面', type: 'line', smooth: true, data: data.map(d => d.positive), itemStyle: { color: '#52c41a' }, areaStyle: { color: 'rgba(82,196,26,0.1)' } },
      { name: '中性', type: 'line', smooth: true, data: data.map(d => d.neutral), itemStyle: { color: '#faad14' } },
      { name: '负面', type: 'line', smooth: true, data: data.map(d => d.negative), itemStyle: { color: '#ff4d4f' }, areaStyle: { color: 'rgba(255,77,79,0.1)' } },
    ],
  })
}

function renderSourceChart(data) {
  if (!sourceChartRef.value) return
  if (!sourceChart) {
    sourceChart = echarts.init(sourceChartRef.value)
  }
  sourceChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      data: data.map(d => ({ name: d.source, value: d.count })),
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  })
}

function renderKeywordChart(data) {
  if (!keywordChartRef.value) return
  if (!keywordChart) {
    keywordChart = echarts.init(keywordChartRef.value)
  }
  keywordChart.setOption({
    tooltip: { show: true },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [14, 50],
      rotationRange: [-30, 30],
      textStyle: {
        fontFamily: 'PingFang SC, Microsoft YaHei',
        color: () => {
          const colors = ['#52c41a', '#1890ff', '#722ed1', '#faad14', '#ff4d4f', '#13c2c2', '#eb2f96']
          return colors[Math.floor(Math.random() * colors.length)]
        },
      },
      data: data,
    }],
  })
}

function renderRadarChart(data) {
  if (!radarChartRef.value) return
  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value)
  }
  const indicators = ['外观', '内饰', '动力', '空间', '性价比', '操控', '舒适性'].map(name => ({ name, max: 100 }))
  const colors = ['#1890ff', '#52c41a', '#faad14', '#722ed1', '#ff4d4f']

  radarChart.setOption({
    tooltip: {},
    legend: { data: data.map(d => d.model.name_cn), bottom: 0, type: 'scroll' },
    radar: { indicator: indicators, radius: '60%', center: ['50%', '45%'] },
    series: [{
      type: 'radar',
      data: data.map((d, i) => ({
        name: d.model.name_cn,
        value: Object.values(d.radar),
        lineStyle: { color: colors[i % colors.length] },
        itemStyle: { color: colors[i % colors.length] },
        areaStyle: { color: colors[i % colors.length], opacity: 0.1 },
      })),
    }],
  })
}

// ========== 工具函数 ==========

function getIndexColor(index) {
  if (index >= 70) return '#52c41a'
  if (index >= 50) return '#faad14'
  return '#ff4d4f'
}

function getSentimentType(label) {
  if (label === 'positive') return 'success'
  if (label === 'negative') return 'danger'
  return 'info'
}

function getSentimentLabel(label) {
  if (label === 'positive') return '正面'
  if (label === 'negative') return '负面'
  return '中性'
}

function getPriorityType(priority) {
  if (priority === 'high') return 'danger'
  if (priority === 'medium') return 'warning'
  return 'info'
}

function getPriorityLabel(priority) {
  if (priority === 'high') return '高优先级'
  if (priority === 'medium') return '中优先级'
  return '低优先级'
}

function formatCount(num) {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return num
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.brand-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.brand-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  &.active {
    border-color: #1890ff;
  }
}

.brand-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;

  .brand-name {
    font-size: 18px;
    font-weight: 600;
  }
  .brand-en {
    font-size: 12px;
    color: #999;
  }
}

.sentiment-index {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 16px;

  .index-value {
    font-size: 36px;
    font-weight: 700;
  }
  .index-label {
    font-size: 13px;
    color: #999;
  }
}

.brand-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .stat-value {
    font-size: 16px;
    font-weight: 600;
    &.positive { color: #52c41a; }
    &.neutral { color: #faad14; }
    &.negative { color: #ff4d4f; }
  }
  .stat-label {
    font-size: 12px;
    color: #999;
    margin-top: 2px;
  }
}

.brand-change {
  font-size: 13px;
  color: #999;
  &.up { color: #52c41a; }
  &.down { color: #ff4d4f; }
  .change-label {
    margin-left: 4px;
    font-size: 12px;
  }
}

.charts-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h3 {
    font-size: 15px;
    font-weight: 600;
  }
}

.chart-container {
  height: 280px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
}

.article-link {
  color: #333;
  text-decoration: none;
  &:hover {
    color: #1890ff;
  }
}

.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid #ddd;
  background: #fafafa;

  &.high { border-left-color: #ff4d4f; background: #fff2f0; }
  &.medium { border-left-color: #faad14; background: #fffbe6; }
  &.low { border-left-color: #52c41a; background: #f6ffed; }
}

.rec-content {
  flex: 1;
  .rec-title {
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 4px;
  }
  .rec-meta {
    font-size: 12px;
    color: #999;
  }
  .rec-date {
    margin-left: 8px;
  }
}
</style>
