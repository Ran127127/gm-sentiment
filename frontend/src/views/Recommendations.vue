<template>
  <div class="recommendations-page">
    <div class="page-header">
      <h2>智能建议</h2>
      <div class="filters">
        <el-select v-model="filters.brand_id" placeholder="品牌" clearable @change="loadData">
          <el-option label="别克" :value="1" />
          <el-option label="凯迪拉克" :value="2" />
          <el-option label="雪佛兰" :value="3" />
        </el-select>
        <el-select v-model="filters.priority" placeholder="优先级" clearable @change="loadData">
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable @change="loadData">
          <el-option label="待处理" value="pending" />
          <el-option label="已确认" value="acknowledged" />
        </el-select>
      </div>
    </div>

    <div class="rec-list" v-loading="loading">
      <div v-for="rec in recommendations" :key="rec.id" class="rec-card" :class="rec.priority">
        <div class="rec-header">
          <el-tag :type="getPriorityType(rec.priority)" size="small">
            {{ getPriorityLabel(rec.priority) }}
          </el-tag>
          <el-tag :type="rec.status === 'pending' ? 'warning' : 'success'" size="small">
            {{ rec.status === 'pending' ? '待处理' : '已确认' }}
          </el-tag>
          <span class="rec-category">{{ getCategoryLabel(rec.category) }}</span>
          <span class="rec-date">{{ rec.date }}</span>
        </div>
        <h3 class="rec-title">{{ rec.title }}</h3>
        <p class="rec-desc">{{ rec.description }}</p>
        <div class="rec-footer">
          <span class="rec-brand">{{ rec.brand_name }}</span>
          <span v-if="rec.model_name" class="rec-model">{{ rec.model_name }}</span>
          <el-button
            v-if="rec.status === 'pending'"
            type="primary"
            size="small"
            @click="handleAcknowledge(rec.id)"
          >
            确认
          </el-button>
        </div>
        <div class="rec-evidence" v-if="rec.evidence">
          <span class="evidence-label">数据支撑：</span>
          <span v-if="rec.evidence.avg_score">
            情感均分 {{ (rec.evidence.avg_score * 100).toFixed(0) }}
          </span>
          <span v-if="rec.evidence.negative_ratio">
            负面率 {{ (rec.evidence.negative_ratio * 100).toFixed(1) }}%
          </span>
          <span v-if="rec.evidence.total">
            样本量 {{ rec.evidence.total }}
          </span>
        </div>
      </div>
      <el-empty v-if="!loading && !recommendations.length" description="暂无建议" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRecommendations, acknowledgeRecommendation } from '../api/recommendation'

const recommendations = ref([])
const loading = ref(false)
const filters = ref({ brand_id: null, priority: '', status: '' })

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.brand_id) params.brand_id = filters.value.brand_id
    if (filters.value.priority) params.priority = filters.value.priority
    if (filters.value.status) params.status = filters.value.status
    const res = await getRecommendations(params)
    recommendations.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function handleAcknowledge(id) {
  try {
    await acknowledgeRecommendation(id)
    ElMessage.success('已确认')
    loadData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function getPriorityType(p) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}
function getPriorityLabel(p) {
  if (p === 'high') return '高优先级'
  if (p === 'medium') return '中优先级'
  return '低优先级'
}
function getCategoryLabel(c) {
  const map = { pr_crisis: '公关预警', marketing: '营销策略', product_feedback: '产品反馈', opportunity: '传播机会' }
  return map[c] || c
}
</script>

<style lang="scss" scoped>
.recommendations-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
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
.rec-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.rec-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid #ddd;
  &.high { border-left-color: #ff4d4f; }
  &.medium { border-left-color: #faad14; }
  &.low { border-left-color: #52c41a; }
}
.rec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  .rec-category { font-size: 13px; color: #666; }
  .rec-date { font-size: 12px; color: #999; margin-left: auto; }
}
.rec-title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  margin-bottom: 8px;
}
.rec-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12px;
}
.rec-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  .rec-brand { font-size: 13px; color: #999; }
  .rec-model { font-size: 13px; color: #999; }
  button { margin-left: auto; }
}
.rec-evidence {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #999;
  display: flex;
  gap: 16px;
  .evidence-label { color: #666; }
}
</style>
