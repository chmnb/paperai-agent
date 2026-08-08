import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  { path: '/home', name: 'Home', component: () => import('@/views/Home.vue') },
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
  { path: '/papers', name: 'PaperList', component: () => import('@/views/PaperList.vue') },
  { path: '/paper/:id', name: 'PaperReader', component: () => import('@/views/PaperReader.vue') },
  { path: '/paper/:id/qa', name: 'PaperQA', component: () => import('@/views/PaperQA.vue') },
  { path: '/notes', name: 'Notes', component: () => import('@/views/Notes.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from) => {
  const token = localStorage.getItem('access_token')
  if (!token && to.path !== '/login' && to.path !== '/home') return '/login'
  return true
})

export default router