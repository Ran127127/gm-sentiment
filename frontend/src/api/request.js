import axios from 'axios'

// Render部署时前端和后端分离，通过VITE_API_BASE_URL指定后端地址
// 本地开发时留空，使用相对路径（由vite proxy转发）
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const request = axios.create({
  baseURL,
  timeout: 15000,
})

// 请求拦截器：自动附加JWT token
request.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 自动种子标记，避免重复触发
let seedPromise = null

async function autoSeedIfNeeded() {
  if (seedPromise) return seedPromise
  seedPromise = (async () => {
    try {
      console.log('[auto-seed] 检测到数据为空，正在初始化种子数据...')
      await axios.post(`${baseURL}/admin/seed?force=true`, null, { timeout: 60000 })
      console.log('[auto-seed] 种子数据初始化完成')
    } catch (e) {
      console.warn('[auto-seed] 自动初始化失败:', e.message)
    }
  })()
  return seedPromise
}

// 响应拦截器
request.interceptors.response.use(
  async (response) => {
    const data = response.data
    // 检测GET请求返回空数据时自动触发种子初始化
    if (response.config.method === 'get' && data?.code === 200) {
      const isEmpty = Array.isArray(data.data) && data.data.length === 0
      if (isEmpty && !response.config.url.includes('admin/seed')) {
        await autoSeedIfNeeded()
        // 重试原始请求
        const retry = await axios({
          ...response.config,
          headers: { ...response.config.headers, _retry: '1' },
        })
        return retry.data
      }
    }
    return data
  },
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
