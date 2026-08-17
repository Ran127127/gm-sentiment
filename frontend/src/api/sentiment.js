import request from './request'

export function getArticles(params) {
  return request.get('/sentiment/articles', { params })
}

export function getArticleDetail(id) {
  return request.get(`/sentiment/articles/${id}`)
}

export function getAspectAnalysis(params) {
  return request.get('/sentiment/aspect-analysis', { params })
}
