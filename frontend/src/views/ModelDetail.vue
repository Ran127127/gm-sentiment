<template>
  <div class="model-detail" v-loading="loading">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft" circle size="small" />
      <h2>{{ modelInfo?.name_cn }} <span class="brand-tag">{{ modelInfo?.name_en }}</span></h2>
      <el-tag v-if="modelInfo?.category" size="small" type="info">{{ modelInfo.category }}</el-tag>
    </div>

    <!-- 摘要卡片 -->
    <div class="summary-cards">
      <el-card shadow="never">
        <div class="summary-item">
          <span class="label">总文章数</span>
          <span class="value">{{ summary.total_count || 0 }}</span>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-item">
          <span class="label">正面占比</span>
          <span class="value positive">{{ positiveRatio }}%</span>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-item">
          <span class="label">负面占比</span>
          <span class="value negative">{{ negativeRatio }}%</span>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="summary-item">
          <span class="label">平均情感分</span>
          <span class="value">{{ scoreDisplay }}</span>
        </div>
      </el-card>
    </div>

    <!-- 维度分析 -->
    <div class="section" v-if="aspects.length">
      <h3>维度情感分析</h3>
      <div ref="aspectChartRef" class="chart-container"></div>
    </div>

    <!-- 热门关键词 -->
    <div class="section" v-if="hotKeywords.length">
      <h3>热门关键词</h3>
      <div class="keyword-cloud">
        <el-tag
          v-for="kw in hotKeywords"
          :key="kw.name"
          :size="getKeywordSize(kw.value)"
          :type="getKeywordType(kw.name)"
          class="keyword-tag"
        >
          {{ kw.name }} ({{ kw.value }})
        </el-tag>
      </div>
    </div>

    <!-- 相关文章 -->
    <div class="section">
      <h3>相关文章</h3>
      <el-table :data="articles" stripe>
        <el-table-column label="平台" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="300">
          <template #default="{ row }">
            <router-link :to="`/articles/${row.id}`" class="article-link">{{ row.title }}</router-link>
          </template>
        </el-table-column>
        <el-table-column label="情感" width="80">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment?.label)" size="small">
              {{ getSentimentLabel(row.sentiment?.label) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="互动" width="100">
          <template #default="{ row }">
            {{ row.like_count + row.comment_count + row.share_count }}
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="120">
          <template #default="{ row }">
            {{ formatDate(row.publish_time) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!articles.length" description="暂无相关文章" :image-size="60" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getModelDetail } from '../api/brand'
import { getArticles } from '../api/sentiment'

const route = useRoute()
const modelId = Number(route.params.id)

const loading = ref(true)
const modelInfo = ref(null)
const summary = ref({})
const aspects = ref([])
const hotKeywords = ref([])
const articles = ref([])
const aspectChartRef = ref(null)
let aspectChart = null

const positiveRatio = computed(() =>
  summary.value.total_count
    ? (summary.value.positive_count / summary.value.total_count * 100).toFixed(1)
    : 0
)
const negativeRatio = computed(() =>
  summary.value.total_count
    ? (summary.value.negative_count / summary.value.total_count * 100).toFixed(1)
    : 0
)
const scoreDisplay = computed(() =>
  summary.value.avg_score ? (summary.value.avg_score * 100).toFixed(0) : 0
)

onMounted(async () => {
  try {
    const res = await getModelDetail(modelId, { days: 30 })
    const data = res.data
    modelInfo.value = data.model
    summary.value = data.summary || {}
    aspects.value = data.aspects || []
    hotKeywords.value = data.hot_keywords || []

    // 加载相关文章
    const articlesRes = await getArticles({ model_id: modelId, size: 20 })
    articles.value = articlesRes.data || []

    // 渲染维度图表
    await renderAspectChart()
    window.addEventListener('resize', () => aspectChart?.resize())
  } catch (err) {
    console.error('Failed to load model detail:', err)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  aspectChart?.dispose()
})

async function renderAspectChart() {
  if (!aspectChartRef.value || !aspects.value.length) return

  aspectChart = echarts.init(aspectChartRef.value)
  aspectChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const d = params[0]
        const aspect = aspects.value.find(a => a.aspect === d.name)
        return `${d.name}<br/>平均分: ${d.value}<br/>正面: ${aspect?.positive_ratio || 0}%<br/>负面: ${aspect?.negative_ratio || 0}%`
      },
    },
    grid: { top: 10, right: 20, bottom: 30, left: 80 },
    xAxis: { type: 'value', max: 100, name: '分数' },
    yAxis: { type: 'category', data: aspects.value.map(a => a.aspect) },
    series: [{
      type: 'bar',
      data: aspects.value.map(d => ({
        value: (d.avg_score * 100).toFixed(1),
        itemStyle: {
          color: d.avg_score > 0.6 ? '#52c41a' : d.avg_score > 0.4 ? '#faad14' : '#ff4d4f',
        },
      })),
      barWidth: 20,
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  })
}

function getKeywordSize(value) {
  if (value >= 5) return 'large'
  if (value >= 3) return 'default'
  return 'small'
}

function getKeywordType(name) {
  const negative = ['噪音', '异响', '顿挫', '油耗', '粗糙', '偏硬', '偏软', '不足']
  if (negative.some(k => name.includes(k))) return 'danger'
  return 'success'
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
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style lang="scss" scoped>
.model-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  h2 { font-size: 20px; font-weight: 600; }
  .brand-tag { font-size: 14px; font-weight: 400; color: #999; }
}
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.summary-item {
  text-align: center;
  .label { display: block; font-size: 13px; color: #999; margin-bottom: 8px; }
  .value { font-size: 28px; font-weight: 700; &.positive { color: #52c41a; } &.negative { color: #ff4d4f; } }
}
.section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  h3 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
}
.chart-container { height: 300px; }
.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  .keyword-tag { cursor: default; }
}
.article-link { color: #333; text-decoration: none; &:hover { color: #1890ff; } }
</style>
