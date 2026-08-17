import request from './request'

export function getBrands() {
  return request.get('/brands')
}

export function getBrand(id) {
  return request.get(`/brands/${id}`)
}

export function getBrandModels(id) {
  return request.get(`/brands/${id}/models`)
}

export function getBrandSummary(id, params) {
  return request.get(`/brands/${id}/summary`, { params })
}
