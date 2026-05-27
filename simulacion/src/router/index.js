import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: { name: 'simulacion' },
    },
    {
      path: '/simulacion',
      name: 'simulacion',
      component: () => import('../views/SimulacionView.vue'),
    },
    {
      path: '/video-stream',
      name: 'videoStream',
      component: () => import('../views/VideoStreamView.vue'),
    },
  ],
})

export default router
