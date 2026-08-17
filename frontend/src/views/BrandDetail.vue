<template>
  <div class="brand-detail">
    <div class="page-header">
      <el-button @click="$router.push('/')" :icon="ArrowLeft" circle size="small" />
      <h2>{{ brandInfo?.name_cn }} 品牌详情</h2>
    </div>

    <div class="summary-cards">
      <el-card shadow="never">
        <div class="summary-item">
          <span class="label">总文章数</span>
          <span class="value">{{ summary.total_count }}</span>
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
          <span class="value">{{ (summary.avg_score * 100).toFixed(0) }}</span>
        </div>
      </el-card>
    </div>

    <!-- 车型列表 -->
    <div class="section">
      <h3>车型列表</h3>
      <div class="model-grid">
        <router-link
          v-for="model in models"
          :key="model.id"
          :to="`/model/${model.id}`"
          class="model-card"
        >
          <span class="model-name">{{ model.name_cn }}</span>
          <span class="model-en">{{ model.name_en }}</span>
          <el-tag size="small" type="info">{{ model.category }}</el-tag>
        </router-link>
      </div>
    </div>

    <!-- 维度分析 -->
    <div class="section">
      <h3>维度情感分析</h3>
      <div ref="aspectChartRef" class="chart-container"></div>
    </div>

    <!-- 热门文章 -->
    <div class="section">
      <h3>品牌热门文章</h3>
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
        <el-table-column prop="model_name" label="车型" width="120" />
        <el-table-column label="情感" width="80">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment?.label)" size="small">
              {{ getSentimentLabel(row.sentiment?.label) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="互动" width="100">
          <template #default="{ row }">
            {{ row.like_count + row.comment_count }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getBrand, getBrandModels, getBrandSummary } from '../api/brand'
import { getAspectAnalysis, getArticles } from '../api/sentiment'

const route = useRoute()
const brandId = Number(route.params.id)

const brandInfo = ref(null)
const models = ref([])
const summary = ref({})
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

onMounted(async () => {
  const [brandRes, modelsRes, summaryRes, articlesRes] = await Promise.all([
    getBrand(brandId),
    getBrandModels(brandId),
    getBrandSummary(brandId, { days: 30 }),
    getArticles({ brand_id: brandId, size: 10 }),
  ])
  brandInfo.value = brandRes.data
  models.value = modelsRes.data
  summary.value = summaryRes.data || {}
  articles.value = articlesRes.data || []

  await loadAspect()
  window.addEventListener('resize', () => aspectChart?.resize())
})

onBeforeUnmount(() => {
  aspectChart?.dispose()
})

async function loadAspect() {
  const res = await getAspectAnalysis({ brand_id: brandId })
  const data = res.data || []
  if (!aspectChartRef.value || !data.length) return

  aspectChart = echarts.init(aspectChartRef.value)
  aspectChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 20, bottom: 30, left: 80 },
    xAxis: { type: 'value', max: 100 },
    yAxis: { type: 'category', data: data.map(d => d.aspect) },
    series: [{
      type: 'bar',
      data: data.map(d => ({
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
</script>

<style lang="scss" scoped>
.brand-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  h2 { font-size: 20px; font-weight: 600; }
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
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.model-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    border-color: #1890ff;
    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
    transform: translateY(-2px);
  }
  .model-name { font-weight: 600; }
  .model-en { font-size: 12px; color: #999; }
}
.chart-container { height: 300px; }
.article-link { color: #333; text-decoration: none; &:hover { color: #1890ff; } }
</style>
