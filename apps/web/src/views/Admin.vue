<template>
  <div class="admin">
    <h2>User Management</h2>
    <p class="subtitle">Manage user accounts (Admin only)</p>

    <!-- Create User Section -->
    <div class="card create-user-section">
      <h3>Create New User</h3>
      <form @submit.prevent="handleCreateUser" class="create-form">
        <div class="form-row">
          <div class="form-group">
            <label for="new-username">Username</label>
            <input
              id="new-username"
              v-model="newUser.username"
              type="text"
              placeholder="Enter username"
              required
              :disabled="creating"
            />
          </div>
          
          <div class="form-group">
            <label for="new-password">Password</label>
            <input
              id="new-password"
              v-model="newUser.password"
              type="password"
              placeholder="Enter password"
              required
              :disabled="creating"
            />
          </div>
          
          <div class="form-group checkbox-group">
            <label>
              <input
                v-model="newUser.isAdmin"
                type="checkbox"
                :disabled="creating"
              />
              Admin User
            </label>
          </div>
          
          <div class="form-group">
            <button type="submit" class="btn btn-primary" :disabled="creating">
              {{ creating ? 'Creating...' : 'Create User' }}
            </button>
          </div>
        </div>
      </form>
      
      <div v-if="createError" class="error-message">
        {{ createError }}
      </div>
      
      <div v-if="createSuccess" class="success-message">
        {{ createSuccess }}
      </div>
    </div>

    <!-- Users List Section -->
    <div class="card users-section">
      <div class="section-header">
        <h3>Existing Users</h3>
        <button @click="loadUsers" class="btn btn-secondary" :disabled="loading">
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
      
      <div v-if="loading && users.length === 0" class="loading">
        Loading users...
      </div>
      
      <div v-else-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-else-if="users.length === 0" class="no-users">
        No users found.
      </div>
      
      <table v-else class="users-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.username">
            <td class="username">{{ user.username }}</td>
            <td>
              <span :class="['role-badge', user.is_admin ? 'admin' : 'user']">
                {{ user.is_admin ? 'Admin' : 'User' }}
              </span>
            </td>
            <td class="created-date">{{ formatDate(user.created_at) }}</td>
            <td>
              <button
                @click="confirmDelete(user.username)"
                class="btn btn-danger btn-small"
                :disabled="user.username === store.user || deleting === user.username"
              >
                {{ deleting === user.username ? 'Deleting...' : 'Delete' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="modal" @click.stop>
        <h3>Confirm Delete</h3>
        <p>Are you sure you want to delete user <strong>{{ deleteConfirm }}</strong>?</p>
        <p class="warning">This action cannot be undone.</p>
        <div class="modal-actions">
          <button @click="cancelDelete" class="btn btn-secondary">Cancel</button>
          <button @click="handleDeleteUser" class="btn btn-danger">Delete User</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { authAPI } from '../services/api'
import { usePlanningStore } from '../stores/planning'

const store = usePlanningStore()

const users = ref([])
const loading = ref(false)
const error = ref('')

const newUser = ref({
  username: '',
  password: '',
  isAdmin: false
})
const creating = ref(false)
const createError = ref('')
const createSuccess = ref('')

const deleteConfirm = ref(null)
const deleting = ref(null)

// Handle ESC key to close modals
function handleEscKey(event) {
  if (event.key === 'Escape') {
    deleteConfirm.value = null
  }
}

onMounted(() => {
  // Ensure no modals are stuck open on mount
  deleteConfirm.value = null
  
  // Add ESC key listener
  window.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEscKey)
})

async function loadUsers() {
  loading.value = true
  error.value = ''
  
  try {
    const response = await authAPI.listUsers()
    users.value = response.data
  } catch (err) {
    console.error('Failed to load users:', err)
    error.value = err.response?.data?.detail || 'Failed to load users'
  } finally {
    loading.value = false
  }
}

async function handleCreateUser() {
  if (!newUser.value.username || !newUser.value.password) {
    createError.value = 'Username and password are required'
    return
  }
  
  creating.value = true
  createError.value = ''
  createSuccess.value = ''
  
  try {
    await authAPI.createUser(
      newUser.value.username,
      newUser.value.password,
      newUser.value.isAdmin
    )
    
    createSuccess.value = `User '${newUser.value.username}' created successfully!`
    
    // Reset form
    newUser.value = {
      username: '',
      password: '',
      isAdmin: false
    }
    
    // Reload users list
    await loadUsers()
    
    // Clear success message after 3 seconds
    setTimeout(() => {
      createSuccess.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to create user:', err)
    createError.value = err.response?.data?.detail || 'Failed to create user'
  } finally {
    creating.value = false
  }
}

function confirmDelete(username) {
  deleteConfirm.value = username
}

function cancelDelete() {
  deleteConfirm.value = null
}

async function handleDeleteUser() {
  const username = deleteConfirm.value
  deleteConfirm.value = null
  deleting.value = username
  
  try {
    await authAPI.deleteUser(username)
    
    // Remove from list
    users.value = users.value.filter(u => u.username !== username)
  } catch (err) {
    console.error('Failed to delete user:', err)
    error.value = err.response?.data?.detail || 'Failed to delete user'
  } finally {
    deleting.value = null
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.admin {
  max-width: 1000px;
  margin: 0 auto;
}

h2 {
  color: #1e3a8a;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #64748b;
  margin-bottom: 2rem;
}

.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.create-user-section h3,
.users-section h3 {
  margin: 0 0 1rem 0;
  color: #334155;
  font-size: 1.25rem;
}

.create-form {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto auto;
  gap: 1rem;
  align-items: end;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 0.5rem;
  color: #334155;
  font-weight: 500;
  font-size: 0.875rem;
}

.form-group input[type="text"],
.form-group input[type="password"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.875rem;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.checkbox-group {
  justify-content: flex-end;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  margin-bottom: 0;
}

.checkbox-group input[type="checkbox"] {
  cursor: pointer;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #5568d3;
}

.btn-secondary {
  background-color: #e2e8f0;
  color: #334155;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #cbd5e1;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #dc2626;
}

.btn-small {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

.error-message {
  background-color: #fee2e2;
  color: #991b1b;
  padding: 0.75rem;
  border-radius: 4px;
  margin-top: 1rem;
  font-size: 0.875rem;
  border: 1px solid #fecaca;
}

.success-message {
  background-color: #d1fae5;
  color: #065f46;
  padding: 0.75rem;
  border-radius: 4px;
  margin-top: 1rem;
  font-size: 0.875rem;
  border: 1px solid #a7f3d0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.loading,
.no-users {
  text-align: center;
  padding: 2rem;
  color: #64748b;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th {
  text-align: left;
  padding: 0.75rem;
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 0.875rem;
  border-bottom: 2px solid #e2e8f0;
}

.users-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.875rem;
}

.users-table tr:hover {
  background-color: #f8fafc;
}

.username {
  font-weight: 500;
  color: #1e3a8a;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.role-badge.admin {
  background-color: #dbeafe;
  color: #1e40af;
}

.role-badge.user {
  background-color: #e0e7ff;
  color: #4338ca;
}

.created-date {
  color: #64748b;
  font-size: 0.8125rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.modal h3 {
  margin: 0 0 1rem 0;
  color: #1e3a8a;
}

.modal p {
  margin: 0.5rem 0;
  color: #334155;
}

.modal .warning {
  color: #dc2626;
  font-size: 0.875rem;
  font-style: italic;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .checkbox-group {
    justify-content: flex-start;
  }
}
</style>
