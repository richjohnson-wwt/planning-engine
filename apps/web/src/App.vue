<template>
  <div id="app">
    <header class="app-header" v-if="store.user">
      <div class="container">
        <div class="header-content">
          <h1>Route Planning Engine</h1>
          <div class="user-section">
            <span class="username">{{ store.user }}</span>
            <button @click="handleLogout" class="btn-logout">Logout</button>
          </div>
        </div>
        <nav>
          <router-link to="/">Home</router-link>
          <router-link to="/planning">Planning</router-link>
          <router-link to="/routes">Routes</router-link>
          <router-link to="/teams">Teams</router-link>
          <router-link to="/progress">Progress</router-link>
          <router-link v-if="isAdmin" to="/admin" class="admin-link">Admin</router-link>
        </nav>
      </div>
    </header>
    
    <main class="app-main">
      <div class="container">
        <router-view />
      </div>
    </main>
    
    <footer class="app-footer">
      <div class="container">
        <p>&copy; 2025 Route Planning Engine</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { usePlanningStore } from './stores/planning'
import { useRouter } from 'vue-router'
import { authAPI } from './services/api'
import { ref, onMounted, watch } from 'vue'

const store = usePlanningStore()
const router = useRouter()
const isAdmin = ref(false)

// Check if current user is admin
async function checkAdminStatus() {
  if (!store.user) {
    isAdmin.value = false
    return
  }
  
  try {
    const response = await authAPI.getCurrentUser()
    isAdmin.value = response.data.is_admin
  } catch (err) {
    console.error('Failed to check admin status:', err)
    isAdmin.value = false
  }
}

// Watch for user changes (login/logout) and re-check admin status
watch(() => store.user, () => {
  checkAdminStatus()
})

onMounted(() => {
  checkAdminStatus()
})

async function handleLogout() {
  try {
    await authAPI.logout()
  } catch (err) {
    console.error('Logout error:', err)
  } finally {
    // Clear local state and redirect to login
    store.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  background-color: #1e3a8a;
  color: white;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.username {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
}

.btn-logout {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 0.4rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.2s;
}

.btn-logout:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

.app-header nav {
  margin-top: 0.5rem;
}

.app-header nav a {
  color: white;
  text-decoration: none;
  margin-right: 1.5rem;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.app-header nav a:hover,
.app-header nav a.router-link-active {
  background-color: rgba(255,255,255,0.1);
}

.app-header nav a.admin-link {
  background-color: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.app-header nav a.admin-link:hover {
  background-color: rgba(255, 255, 255, 0.25);
}

.app-main {
  min-height: calc(100vh - 200px);
  padding: 2rem 0;
}

.app-footer {
  background-color: #f3f4f6;
  padding: 1rem 0;
  text-align: center;
  color: #6b7280;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}
</style>
