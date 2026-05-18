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
      path: '/backendTest',
      name: 'backendTest',
      component: () => import('../views/BackendTestView.vue'),
    },
  ],
})

export default router
