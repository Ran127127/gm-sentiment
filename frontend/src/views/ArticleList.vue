<template>
  <div class="article-list">
    <div class="page-header">
      <h2>全部文章</h2>
      <div class="filters">
        <el-select v-model="filters.brand_id" placeholder="品牌" clearable size="default" @change="loadData">
          <el-option label="别克" :value="1" />
          <el-option label="凯迪拉克" :value="2" />
          <el-option label="雪佛兰" :value="3" />
        </el-select>
        <el-select v-model="filters.label" placeholder="情感" clearable size="default" @change="loadData">
          <el-option label="正面" value="positive" />
          <el-option label="中性" value="neutral" />
          <el-option label="负面" value="negative" />
        </el-select>
      </div>
    </div>

    <el-table :data="articles" stripe v-loading="loading">
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
      <el-table-column prop="brand_name" label="品牌" width="100" />
      <el-table-column prop="model_name" label="车型" width="120" />
      <el-table-column label="情感" width="80">
        <template #default="{ row }">
          <el-tag :type="getSentimentType(row.sentiment?.label)" size="small">
            {{ getSentimentLabel(row.sentiment?.label) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="情感分" width="80">
        <template #default="{ row }">
          {{ row.sentiment ? (row.sentiment.score * 100).toFixed(0) : '--' }}
        </template>
      </el-table-column>
      <el-table-column label="互动" width="100">
        <template #default="{ row }">
          {{ row.like_count + row.comment_count + row.share_count }}
        </template>
      </el-table-column>
      <el-table-column label="时间" width="110">
        <template #default="{ row }">
          {{ formatDate(row.publish_time) }}
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getArticles } from '../api/sentiment'

const articles = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filters = ref({ brand_id: null, label: '' })

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, size: 20 }
    if (filters.value.brand_id) params.brand_id = filters.value.brand_id
    if (filters.value.label) params.label = filters.value.label
    const res = await getArticles(params)
    articles.value = res.data || []
    total.value = res.pagination?.total || 0
  } finally {
    loading.value = false
  }
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
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
</script>

<style lang="scss" scoped>
.article-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  h2 { font-size: 18px; font-weight: 600; }
  .filters { display: flex; gap: 12px; }
}
.article-link { color: #333; text-decoration: none; &:hover { color: #1890ff; } }
.pagination {
  display: flex;
  justify-content: center;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
}
</style>
