<template>
  <div class="article-detail" v-loading="loading">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft" circle size="small" />
      <h2>文章详情</h2>
    </div>

    <template v-if="article">
      <div class="article-main">
        <div class="article-info">
          <el-tag size="small">{{ article.source_name }}</el-tag>
          <span class="meta">{{ article.brand_name }} / {{ article.model_name }}</span>
          <span class="meta">{{ formatDate(article.publish_time) }}</span>
          <span class="meta">{{ article.author }}</span>
        </div>
        <h1 class="article-title">{{ article.title }}</h1>
        <div class="article-content">{{ article.content }}</div>
        <div class="article-stats">
          <span>阅读 {{ article.view_count }}</span>
          <span>点赞 {{ article.like_count }}</span>
          <span>评论 {{ article.comment_count }}</span>
          <span>分享 {{ article.share_count }}</span>
        </div>
      </div>

      <div class="sentiment-panel">
        <h3>情感分析结果</h3>
        <div class="sentiment-score" v-if="article.sentiment">
          <div class="score-circle" :style="{ borderColor: getScoreColor(article.sentiment.score) }">
            <span class="score-value">{{ (article.sentiment.score * 100).toFixed(0) }}</span>
            <span class="score-label">{{ getSentimentLabel(article.sentiment.label) }}</span>
          </div>
        </div>
        <div class="aspect-list" v-if="article.sentiment?.aspects">
          <div v-for="(score, aspect) in article.sentiment.aspects" :key="aspect" class="aspect-item">
            <span class="aspect-name">{{ aspect }}</span>
            <el-progress
              :percentage="(score * 100).toFixed(0)"
              :color="getScoreColor(score)"
              :stroke-width="12"
              style="flex: 1"
            />
          </div>
        </div>
        <div class="keywords" v-if="article.sentiment?.keywords?.length">
          <el-tag v-for="kw in article.sentiment.keywords" :key="kw" size="small" type="info">
            {{ kw }}
          </el-tag>
        </div>
      </div>

      <div class="comments-section">
        <h3>评论 ({{ comments.length }})</h3>
        <div v-for="comment in comments" :key="comment.id" class="comment-item">
          <div class="comment-header">
            <span class="comment-author">{{ comment.author }}</span>
            <el-tag
              v-if="comment.sentiment"
              :type="getSentimentType(comment.sentiment.label)"
              size="small"
            >
              {{ getSentimentLabel(comment.sentiment.label) }}
            </el-tag>
            <span class="comment-likes">{{ comment.like_count }} 赞</span>
          </div>
          <p class="comment-content">{{ comment.content }}</p>
        </div>
        <el-empty v-if="!comments.length" description="暂无评论" :image-size="60" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getArticleDetail } from '../api/sentiment'

const route = useRoute()
const articleId = Number(route.params.id)
const article = ref(null)
const comments = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await getArticleDetail(articleId)
    article.value = res.data
    comments.value = res.data?.comments || []
  } finally {
    loading.value = false
  }
})

function getScoreColor(score) {
  if (score > 0.6) return '#52c41a'
  if (score > 0.4) return '#faad14'
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
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
</script>

<style lang="scss" scoped>
.article-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  h2 { font-size: 18px; font-weight: 600; }
}
.article-main {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
}
.article-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  .meta { font-size: 13px; color: #999; }
}
.article-title {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 20px;
}
.article-content {
  font-size: 15px;
  line-height: 1.8;
  color: #444;
  margin-bottom: 20px;
}
.article-stats {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #999;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
.sentiment-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  h3 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
}
.sentiment-score {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}
.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 4px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  .score-value { font-size: 28px; font-weight: 700; }
  .score-label { font-size: 12px; color: #999; }
}
.aspect-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.aspect-item {
  display: flex;
  align-items: center;
  gap: 12px;
  .aspect-name { width: 60px; font-size: 13px; }
}
.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.comments-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  h3 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
}
.comment-item {
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  &:last-child { border-bottom: none; }
}
.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  .comment-author { font-weight: 500; font-size: 14px; }
  .comment-likes { font-size: 12px; color: #999; margin-left: auto; }
}
.comment-content {
  font-size: 14px;
  line-height: 1.6;
  color: #555;
}
</style>
