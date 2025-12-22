import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Planning from '../views/Planning.vue'
import Results from '../views/Results.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/planning',
      name: 'planning',
      component: Planning
    },
    {
      path: '/results',
      name: 'results',
      component: Results
    }
  ]
})

export default router
