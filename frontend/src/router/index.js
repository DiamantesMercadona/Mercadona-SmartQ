import { createRouter, createWebHistory } from 'vue-router'

//mas tarde usar navigation guards

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'menu',
      component: () => import('../views/MenuView.vue'),
    },
    {
      path: '/simulacion',
      name: 'simulacion',
      component: () => import('../views/SimulacionView.vue'),
    },
    {
      path: '/gestion-empleados',
      name: 'gestion-empleados',
      component: () => import('../views/GestionEmpleadosView.vue'),
    },
    {
      path: '/graficas',
      name: 'graficas-view',
      component: () => import('../views/GraficasView.vue'),
    },
    {
      path: '/gestion-empleada',
      redirect: { name: 'gestion-empleados' },
    },
  ],
})

export default router
