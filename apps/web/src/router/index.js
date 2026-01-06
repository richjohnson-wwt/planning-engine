import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Planning from '../views/Planning.vue'
import Routes from '../views/Routes.vue'
import Teams from '../views/Teams.vue'
import Progress from '../views/Progress.vue'

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
      path: '/routes',
      name: 'routes',
      component: Routes
    },
    {
      path: '/teams',
      name: 'teams',
      component: Teams
    },
    {
      path: '/progress',
      name: 'progress',
      component: Progress
    },
    // Legacy redirect for old /results URL
    {
      path: '/results',
      redirect: '/routes'
    }
  ]
})

export default router
