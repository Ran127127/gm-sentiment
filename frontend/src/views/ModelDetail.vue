<template>
  <div class="model-detail">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft" circle size="small" />
      <div class="breadcrumb">
        <router-link to="/">首页</router-link>
        <span class="sep">/</span>
        <router-link :to="`/brand/${data?.brand?.id}`">{{ data?.brand?.name_cn }}</router-link>
        <span class="sep">/</span>
        <span class="current">{{ data?.model?.name_cn }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else-if="data">
      <!-- 概览卡片 -->
      <div class="summary-cards">
        <el-card shadow="never">
          <div class="summary-item">
            <span class="label">总文章数</span>
            <span class="value">{{ data.summary.total_count }}</span>
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
            <span class="value">{{ (data.summary.avg_score * 100).toFixed(0) }}</span>
          </div>
        </el-card>
      </div>

      <!-- 热门关键词 -->
      <div v-if="data.summary.hot_keywords && data.summary.hot_keywords.length" class="section">
        <h3>热门关键词</h3>
        <div class="keyword-cloud">
          <el-tag
            v-for="kw in data.summary.hot_keywords"
            :key="kw.name"
            :type="getKeywordType(kw)"
            size="default"
            class="kw-tag"
          >
            {{ kw.name }} ({{ kw.value }})
          </el-tag>
        </div>
      </div>

      <!-- 维度情感分析 -->
      <div v-if="data.aspects && data.aspects.length" class="section">
        <h3>维度情感分析</h3>
        <div ref="aspectChartRef" class="chart-container"></div>
      </div>

      <!-- 热门文章 -->
      <div v-if="data.articles && data.articles.length" class="section">
        <h3>热门文章</h3>
        <el-table :data="data.articles" stripe>
          <el-table-column label="平台" width="120">
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
          <el-table-column label="浏览" width="80" prop="view_count" />
          <el-table-column label="互动" width="80">
            <template #default="{ row }">
              {{ row.like_count + row.comment_count }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <div v-else class="empty-state">
      <el-empty description="未找到该车型数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getModelDetail } from '../api/brand'

const route = useRoute()
const modelId = Number(route.params.id)

const data = ref(null)
const loading = ref(true)
const aspectChartRef = ref(null)
let aspectChart = null

const positiveRatio = computed(() =>
  data.value?.summary?.total_count
    ? (data.value.summary.positive_count / data.value.summary.total_count * 100).toFixed(1)
    : 0
)
const negativeRatio = computed(() =>
  data.value?.summary?.total_count
    ? (data.value.summary.negative_count / data.value.summary.total_count * 100).toFixed(1)
    : 0
)

onMounted(async () => {
  try {
    const res = await getModelDetail(modelId)
    data.value = res.data
  } catch (e) {
    console.error('加载车型详情失败:', e)
  } finally {
    loading.value = false
  }

  await nextTick()
  if (data.value?.aspects?.length && aspectChartRef.value) {
    renderAspectChart()
    window.addEventListener('resize', () => aspectChart?.resize())
  }
})

onBeforeUnmount(() => {
  aspectChart?.dispose()
})

function renderAspectChart() {
  const aspects = data.value.aspects
  if (!aspectChartRef.value || !aspects.length) return

  aspectChart = echarts.init(aspectChartRef.value)
  aspectChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 30, bottom: 30, left: 80 },
    xAxis: { type: 'value', max: 100, name: '得分' },
    yAxis: { type: 'category', data: aspects.map(d => d.aspect) },
    series: [{
      type: 'bar',
      data: aspects.map(d => ({
        value: (d.avg_score * 100).toFixed(1),
        itemStyle: {
          color: d.avg_score > 0.6 ? '#52c41a' : d.avg_score > 0.4 ? '#faad14' : '#ff4d4f',
        },
      })),
      barWidth: 22,
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  })
}

function getKeywordType(kw) {
  if (kw.value >= 5) return ''
  if (kw.value >= 3) return 'info'
  return 'info'
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
.model-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.breadcrumb {
  font-size: 14px;
  color: #666;
  a {
    color: #409eff;
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }
  .sep { margin: 0 6px; color: #ccc; }
  .current { color: #333; font-weight: 600; }
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
.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.kw-tag {
  font-size: 13px;
}
.chart-container { height: 320px; }
.article-link { color: #333; text-decoration: none; &:hover { color: #1890ff; } }
.loading-state, .empty-state {
  background: #fff;
  border-radius: 12px;
  padding: 40px 20px;
}
</style>
