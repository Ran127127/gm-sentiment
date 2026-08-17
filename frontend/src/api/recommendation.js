import request from './request'

export function getRecommendations(params) {
  return request.get('/recommendations', { params })
}

export function getRecommendationDetail(id) {
  return request.get(`/recommendations/${id}`)
}

export function acknowledgeRecommendation(id) {
  return request.post(`/recommendations/${id}/acknowledge`)
}
