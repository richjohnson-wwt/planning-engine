import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Planning from '../views/Planning.vue'
import Routes from '../views/Routes.vue'
import Teams from '../views/Teams.vue'
import Progress from '../views/Progress.vue'
import Login from '../views/Login.vue'
import Admin from '../views/Admin.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: true }
    },
    {
      path: '/planning',
      name: 'planning',
      component: Planning,
      meta: { requiresAuth: true }
    },
    {
      path: '/routes',
      name: 'routes',
      component: Routes,
      meta: { requiresAuth: true }
    },
    {
      path: '/teams',
      name: 'teams',
      component: Teams,
      meta: { requiresAuth: true }
    },
    {
      path: '/progress',
      name: 'progress',
      component: Progress,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'admin',
      component: Admin,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    // Legacy redirect for old /results URL
    {
      path: '/results',
      redirect: '/routes'
    }
  ]
})

// Navigation guard to check authentication
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  
  if (requiresAuth && !token) {
    // Redirect to login if route requires auth and user is not authenticated
    next({ name: 'login' })
  } else if (to.name === 'login' && token) {
    // Redirect to home if user is already authenticated and tries to access login
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
