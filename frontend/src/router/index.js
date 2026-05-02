import { createRouter, createWebHistory } from 'vue-router'

//mas tarde usar navigation guards

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: { name: 'login' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/simulacion',
      name: 'simulacion',
      component: () => import('../views/SimulacionView.vue'),
    },
  ],
})

export default router
