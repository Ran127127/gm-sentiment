import request from './request'

export function getOverview() {
  return request.get('/dashboard/overview')
}

export function getSentimentTrend(params) {
  return request.get('/dashboard/sentiment-trend', { params })
}

export function getSourceDistribution(params) {
  return request.get('/dashboard/source-distribution', { params })
}

export function getKeywordCloud(params) {
  return request.get('/dashboard/keyword-cloud', { params })
}

export function getModelComparison(params) {
  return request.get('/dashboard/model-comparison', { params })
}

export function getHotArticles(params) {
  return request.get('/dashboard/hot-articles', { params })
}
