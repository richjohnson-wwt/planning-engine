<template>
  <div class="workspace-selector">
    <!-- Mode Toggle -->
    <div class="mode-toggle">
      <button 
        @click="mode = 'select'" 
        :class="{ active: mode === 'select' }"
        class="toggle-btn"
      >
        Select Existing
      </button>
      <button 
        @click="mode = 'create'" 
        :class="{ active: mode === 'create' }"
        class="toggle-btn"
      >
        Create New
      </button>
    </div>
    
    <!-- Select Existing Workspace -->
    <div v-if="mode === 'select'" class="form-group">
      <label for="workspace-select">Select Workspace</label>
      <select
        id="workspace-select"
        v-model="selectedWorkspace"
        class="form-control"
        @change="selectWorkspace"
      >
        <option value="">-- Choose a workspace --</option>
        <option v-for="ws in workspaces" :key="ws" :value="ws">
          {{ ws }}
        </option>
      </select>
      <p v-if="loading" class="help-text">Loading workspaces...</p>
      <p v-else-if="workspaces.length === 0" class="help-text">No workspaces found. Create a new one!</p>
    </div>
    
    <!-- Create New Workspace -->
    <div v-if="mode === 'create'" class="form-group">
      <label for="workspace">Workspace Name</label>
      <input
        id="workspace"
        v-model="workspaceName"
        type="text"
        placeholder="Enter workspace name (e.g., ascension, jitb)"
        class="form-control"
      />
      <p class="help-text">State will be determined from your Excel data during parsing</p>
      
      <button @click="createWorkspace" class="btn btn-primary" :disabled="!canCreate">
        Create Workspace
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { workspaceAPI } from '../services/api'

const store = usePlanningStore()
const mode = ref('select')
const workspaceName = ref('')
const selectedWorkspace = ref('')
const workspaces = ref([])
const loading = ref(false)

const canCreate = computed(() => {
  return workspaceName.value.trim() !== ''
})

async function loadWorkspaces() {
  try {
    loading.value = true
    const response = await workspaceAPI.list()
    workspaces.value = response.data.workspaces || []
  } catch (err) {
    console.error('Error loading workspaces:', err)
    workspaces.value = []
  } finally {
    loading.value = false
  }
}

function selectWorkspace() {
  if (selectedWorkspace.value) {
    store.setWorkspace(selectedWorkspace.value)
    alert(`Workspace "${selectedWorkspace.value}" selected!`)
  }
}

async function createWorkspace() {
  try {
    await workspaceAPI.create(workspaceName.value)
    store.setWorkspace(workspaceName.value)
    alert(`Workspace "${workspaceName.value}" created successfully! Upload an Excel file to set the state.`)
    
    // Refresh workspace list and switch to select mode
    await loadWorkspaces()
    mode.value = 'select'
    selectedWorkspace.value = workspaceName.value
    workspaceName.value = ''
  } catch (err) {
    alert(`Error creating workspace: ${err.response?.data?.detail || err.message}`)
  }
}

// Load workspaces on mount
onMounted(() => {
  loadWorkspaces()
})
</script>

<style scoped>
.workspace-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mode-toggle {
  display: flex;
  gap: 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
}

.toggle-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: none;
  background: white;
  color: #6b7280;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border-right: 1px solid #d1d5db;
}

.toggle-btn:last-child {
  border-right: none;
}

.toggle-btn:hover {
  background: #f9fafb;
}

.toggle-btn.active {
  background: #1e3a8a;
  color: white;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-weight: 500;
  color: #374151;
}

.form-control {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

select.form-control {
  cursor: pointer;
}

.help-text {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 0.5rem;
}

.btn-primary {
  background-color: #1e3a8a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
