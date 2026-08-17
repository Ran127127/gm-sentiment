import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import BrandDetail from '../views/BrandDetail.vue'
import ModelDetail from '../views/ModelDetail.vue'
import ArticleList from '../views/ArticleList.vue'
import ArticleDetail from '../views/ArticleDetail.vue'
import Recommendations from '../views/Recommendations.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    props: true,
  },
  {
    path: '/brand/:id',
    name: 'BrandDetail',
    component: BrandDetail,
    props: true,
  },
  {
    path: '/model/:id',
    name: 'ModelDetail',
    component: ModelDetail,
    props: true,
  },
  {
    path: '/articles',
    name: 'ArticleList',
    component: ArticleList,
    props: true,
  },
  {
    path: '/articles/:id',
    name: 'ArticleDetail',
    component: ArticleDetail,
    props: true,
  },
  {
    path: '/recommendations',
    name: 'Recommendations',
    component: Recommendations,
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
