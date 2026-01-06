<template>
  <div class="progress">
    <h2>Site Progress Tracking</h2>
    
    <!-- Workspace and State Selector -->
    <div class="controls">
      <div class="selector-group">
        <div class="selector">
          <label>Workspace:</label>
          <span class="workspace-display">{{ store.workspace || 'Not selected' }}</span>
        </div>
        
        <div class="selector">
          <label for="state-select">State:</label>
          <select 
            id="state-select"
            v-model="selectedState" 
            @change="loadProgress"
            class="select-input"
            :disabled="!store.workspace || loadingStates"
          >
            <option value="">All States</option>
            <option v-for="state in availableStates" :key="state.name" :value="state.name">
              {{ state.name }} ({{ state.site_count }} sites)
            </option>
          </select>
        </div>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <p>Loading progress data...</p>
    </div>
    
    <!-- No Workspace Selected -->
    <div v-else-if="!store.workspace" class="no-selection">
      <p>Please select a workspace to track site progress.</p>
      <router-link to="/" class="btn btn-secondary">Go to Home</router-link>
    </div>
    
    <!-- Progress Content -->
    <div v-else class="progress-container">
      <!-- Summary Statistics -->
      <div v-if="progressData" class="summary-section">
        <div class="summary-cards">
          <div class="card">
            <h4>Total Sites</h4>
            <p class="stat">{{ progressData.total_sites }}</p>
          </div>
          <div class="card card-pending">
            <h4>Pending</h4>
            <p class="stat">{{ progressData.by_status.pending || 0 }}</p>
          </div>
          <div class="card card-in-progress">
            <h4>In Progress</h4>
            <p class="stat">{{ progressData.by_status.in_progress || 0 }}</p>
          </div>
          <div class="card card-completed">
            <h4>Completed</h4>
            <p class="stat">{{ progressData.by_status.completed || 0 }}</p>
          </div>
          <div class="card card-blocked">
            <h4>Blocked</h4>
            <p class="stat">{{ progressData.by_status.blocked || 0 }}</p>
          </div>
        </div>
      </div>
      
      <!-- No Progress Data -->
      <div v-if="!progressData || progressData.total_sites === 0" class="no-data">
        <p>No progress data available yet.</p>
        <p>Progress tracking will be automatically initialized when you run your first plan.</p>
        <button @click="initializeProgress" class="btn btn-primary" :disabled="initializing">
          {{ initializing ? 'Initializing...' : 'Initialize Progress Tracking Now' }}
        </button>
      </div>
      
      <!-- Bulk Actions Toolbar -->
      <div v-if="progressData && progressData.total_sites > 0" class="bulk-actions-section">
        <div class="bulk-actions-toolbar">
          <div class="selection-info">
            <span v-if="selectedSites.length === 0">No sites selected</span>
            <span v-else>{{ selectedSites.length }} site(s) selected</span>
          </div>
          
          <div v-if="selectedSites.length > 0" class="bulk-actions">
            <select v-model="bulkAction" class="bulk-select">
              <option value="">Select Action...</option>
              <option value="status">Update Status</option>
              <option value="crew">Assign Crew</option>
              <option value="complete">Mark Complete</option>
            </select>
            
            <select v-if="bulkAction === 'status'" v-model="bulkStatus" class="bulk-select">
              <option value="">Select Status...</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="blocked">Blocked</option>
            </select>
            
            <input 
              v-if="bulkAction === 'crew'" 
              v-model="bulkCrew" 
              type="text" 
              placeholder="Enter crew name..."
              class="bulk-input"
            />
            
            <button 
              @click="applyBulkAction" 
              class="btn btn-primary btn-sm"
              :disabled="!canApplyBulkAction"
            >
              Apply
            </button>
            
            <button @click="clearSelection" class="btn btn-secondary btn-sm">
              Clear Selection
            </button>
          </div>
        </div>
      </div>
      
      <!-- Progress Table -->
      <div v-if="progressData && progressData.total_sites > 0" class="table-container">
        <table class="progress-table">
          <thead>
            <tr>
              <th class="checkbox-col">
                <input 
                  type="checkbox" 
                  @change="toggleSelectAll"
                  :checked="allSelected"
                  :indeterminate.prop="someSelected"
                />
              </th>
              <th>Site ID</th>
              <th>State</th>
              <th>City</th>
              <th>Cluster</th>
              <th>Status</th>
              <th>Crew Assigned</th>
              <th>Completed Date</th>
              <th>Notes</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="site in progressData.progress" :key="site.site_id" :class="{ 'selected-row': isSelected(site.site_id) }">
              <td class="checkbox-col">
                <input 
                  type="checkbox" 
                  :checked="isSelected(site.site_id)"
                  @change="toggleSelection(site.site_id)"
                />
              </td>
              <td class="site-id">{{ site.site_id }}</td>
              <td class="state">{{ site.state }}</td>
              <td class="city">{{ site.city || '-' }}</td>
              <td class="cluster">{{ site.cluster_id !== null ? `Cluster ${site.cluster_id + 1}` : '-' }}</td>
              <td>
                <span 
                  v-if="editingSite !== site.site_id"
                  :class="['status-badge', `status-${site.status}`]"
                >
                  {{ formatStatus(site.status) }}
                </span>
                <select 
                  v-else
                  v-model="editForm.status"
                  class="edit-select"
                >
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="blocked">Blocked</option>
                </select>
              </td>
              <td class="crew">
                <span v-if="editingSite !== site.site_id">{{ site.crew_assigned || '-' }}</span>
                <input 
                  v-else
                  v-model="editForm.crew_assigned"
                  type="text"
                  class="edit-input"
                  placeholder="Crew name"
                />
              </td>
              <td class="date">{{ formatDate(site.completed_date) }}</td>
              <td class="notes">
                <span v-if="editingSite !== site.site_id" :title="site.notes">{{ site.notes || '-' }}</span>
                <input 
                  v-else
                  v-model="editForm.notes"
                  type="text"
                  class="edit-input"
                  placeholder="Add notes..."
                />
              </td>
              <td class="timestamp">{{ formatTimestamp(site.last_updated) }}</td>
              <td class="actions-col">
                <div v-if="editingSite !== site.site_id" class="action-buttons">
                  <button @click="startEdit(site)" class="btn-icon" title="Edit">
                    ✏️
                  </button>
                </div>
                <div v-else class="action-buttons">
                  <button @click="saveEdit(site.site_id)" class="btn-icon btn-save" title="Save">
                    ✓
                  </button>
                  <button @click="cancelEdit" class="btn-icon btn-cancel" title="Cancel">
                    ✕
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Error Display -->
    <div v-if="error" class="error">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { workspaceAPI, progressAPI } from '../services/api'

const store = usePlanningStore()

// State
const selectedState = ref('')
const availableStates = ref([])
const progressData = ref(null)
const loading = ref(false)
const loadingStates = ref(false)
const initializing = ref(false)
const error = ref('')

// Bulk edit state
const selectedSites = ref([])
const bulkAction = ref('')
const bulkStatus = ref('')
const bulkCrew = ref('')

// Inline edit state
const editingSite = ref(null)
const editForm = ref({
  status: '',
  crew_assigned: '',
  notes: ''
})

// Methods
async function loadStates() {
  if (!store.workspace) return
  
  loadingStates.value = true
  try {
    const response = await workspaceAPI.getStates(store.workspace)
    availableStates.value = response.data.states || []
  } catch (err) {
    console.error('Failed to load states:', err)
    error.value = 'Failed to load states'
  } finally {
    loadingStates.value = false
  }
}

async function loadProgress() {
  if (!store.workspace) return
  
  loading.value = true
  error.value = ''
  
  try {
    const stateFilter = selectedState.value || null
    const response = await progressAPI.list(store.workspace, stateFilter)
    progressData.value = response.data
    
    console.log('Progress data loaded:', progressData.value)
  } catch (err) {
    console.error('Failed to load progress:', err)
    error.value = 'Failed to load progress data'
    progressData.value = null
  } finally {
    loading.value = false
  }
}

async function initializeProgress() {
  if (!store.workspace) return
  
  initializing.value = true
  error.value = ''
  
  try {
    const response = await progressAPI.initialize(store.workspace, true)
    
    if (response.data.success) {
      console.log('Progress initialized:', response.data.message)
      // Reload progress data
      await loadProgress()
    } else {
      error.value = response.data.error || 'Failed to initialize progress'
    }
  } catch (err) {
    console.error('Failed to initialize progress:', err)
    error.value = 'Failed to initialize progress tracking'
  } finally {
    initializing.value = false
  }
}

function formatStatus(status) {
  const statusMap = {
    'pending': 'Pending',
    'in_progress': 'In Progress',
    'completed': 'Completed',
    'blocked': 'Blocked'
  }
  return statusMap[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString()
  } catch {
    return dateStr
  }
}

function formatTimestamp(timestamp) {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString()
  } catch {
    return timestamp
  }
}

// Bulk selection methods
function toggleSelection(siteId) {
  const index = selectedSites.value.indexOf(siteId)
  if (index > -1) {
    selectedSites.value.splice(index, 1)
  } else {
    selectedSites.value.push(siteId)
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedSites.value = []
  } else {
    selectedSites.value = progressData.value.progress.map(site => site.site_id)
  }
}

function isSelected(siteId) {
  return selectedSites.value.includes(siteId)
}

function clearSelection() {
  selectedSites.value = []
  bulkAction.value = ''
  bulkStatus.value = ''
  bulkCrew.value = ''
}

// Computed properties for selection state
const allSelected = computed(() => {
  return progressData.value && 
         progressData.value.progress.length > 0 && 
         selectedSites.value.length === progressData.value.progress.length
})

const someSelected = computed(() => {
  return selectedSites.value.length > 0 && !allSelected.value
})

const canApplyBulkAction = computed(() => {
  if (bulkAction.value === 'status') {
    return bulkStatus.value !== ''
  } else if (bulkAction.value === 'crew') {
    return bulkCrew.value.trim() !== ''
  } else if (bulkAction.value === 'complete') {
    return true
  }
  return false
})

// Bulk action methods
async function applyBulkAction() {
  if (!canApplyBulkAction.value || selectedSites.value.length === 0) return
  
  loading.value = true
  error.value = ''
  
  try {
    const updateData = {
      site_ids: selectedSites.value
    }
    
    if (bulkAction.value === 'status') {
      updateData.status = bulkStatus.value
    } else if (bulkAction.value === 'crew') {
      updateData.crew_assigned = bulkCrew.value
    } else if (bulkAction.value === 'complete') {
      updateData.status = 'completed'
      updateData.completed_date = new Date().toISOString().split('T')[0]
    }
    
    const response = await progressAPI.bulkUpdate(store.workspace, updateData)
    
    if (response.data.success) {
      console.log('Bulk update successful:', response.data.message)
      // Reload progress data
      await loadProgress()
      clearSelection()
    } else {
      error.value = response.data.error || 'Failed to apply bulk action'
    }
  } catch (err) {
    console.error('Failed to apply bulk action:', err)
    error.value = 'Failed to apply bulk action'
  } finally {
    loading.value = false
  }
}

// Inline edit methods
function startEdit(site) {
  editingSite.value = site.site_id
  editForm.value = {
    status: site.status,
    crew_assigned: site.crew_assigned || '',
    notes: site.notes || ''
  }
}

function cancelEdit() {
  editingSite.value = null
  editForm.value = {
    status: '',
    crew_assigned: '',
    notes: ''
  }
}

async function saveEdit(siteId) {
  loading.value = true
  error.value = ''
  
  try {
    const updateData = {
      status: editForm.value.status,
      crew_assigned: editForm.value.crew_assigned || null,
      notes: editForm.value.notes || ''
    }
    
    const response = await progressAPI.update(store.workspace, siteId, updateData)
    
    if (response.data.success) {
      console.log('Site updated successfully')
      // Reload progress data
      await loadProgress()
      cancelEdit()
    } else {
      error.value = response.data.error || 'Failed to update site'
    }
  } catch (err) {
    console.error('Failed to update site:', err)
    error.value = 'Failed to update site'
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(async () => {
  if (store.workspace) {
    await loadStates()
    
    // Auto-select state from Planning/Teams tab if available
    if (store.stateAbbr && !selectedState.value) {
      selectedState.value = store.stateAbbr
    }
    
    // Load progress data
    await loadProgress()
  }
})
</script>

<style scoped>
.progress {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

h2 {
  color: #1e3a8a;
  margin-bottom: 1.5rem;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.selector-group {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.selector label {
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
}

.workspace-display {
  padding: 0.5rem 0.75rem;
  background: #f3f4f6;
  border-radius: 6px;
  color: #1f2937;
  font-weight: 500;
}

.select-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #1f2937;
  font-size: 0.9rem;
  min-width: 200px;
  cursor: pointer;
}

.select-input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.btn-secondary {
  background-color: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background-color: #4b5563;
}

.loading, .no-selection {
  text-align: center;
  padding: 3rem;
  background: #f9fafb;
  border-radius: 8px;
  color: #6b7280;
}

.progress-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.summary-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 1.5rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.card {
  background: #f9fafb;
  border-radius: 6px;
  padding: 1rem;
  text-align: center;
  border: 2px solid #e5e7eb;
}

.card h4 {
  margin: 0 0 0.5rem 0;
  color: #6b7280;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.card .stat {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
}

.card-pending {
  border-color: #93c5fd;
  background: #eff6ff;
}

.card-pending .stat {
  color: #1e40af;
}

.card-in-progress {
  border-color: #fcd34d;
  background: #fefce8;
}

.card-in-progress .stat {
  color: #b45309;
}

.card-completed {
  border-color: #86efac;
  background: #f0fdf4;
}

.card-completed .stat {
  color: #15803d;
}

.card-blocked {
  border-color: #fca5a5;
  background: #fef2f2;
}

.card-blocked .stat {
  color: #b91c1c;
}

.no-data {
  text-align: center;
  padding: 3rem;
  background: #f9fafb;
  border-radius: 8px;
  color: #6b7280;
}

.no-data p {
  margin: 0.5rem 0;
}

.no-data .btn {
  margin-top: 1.5rem;
}

.table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  overflow-x: auto;
}

.progress-table {
  width: 100%;
  border-collapse: collapse;
}

.progress-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.progress-table th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.progress-table tbody tr {
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s;
}

.progress-table tbody tr:hover {
  background-color: #f9fafb;
}

.progress-table td {
  padding: 0.75rem;
  color: #1f2937;
}

.site-id {
  font-family: monospace;
  font-size: 0.85rem;
  color: #6b7280;
  font-weight: 500;
}

.state {
  font-weight: 600;
  color: #1e3a8a;
}

.city {
  color: #374151;
  font-size: 0.9rem;
}

.cluster {
  text-align: center;
  font-weight: 600;
  color: #6b7280;
  font-size: 0.9rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-pending {
  background: #dbeafe;
  color: #1e40af;
}

.status-in_progress {
  background: #fef3c7;
  color: #b45309;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-blocked {
  background: #fee2e2;
  color: #991b1b;
}

.crew {
  font-weight: 500;
  color: #4b5563;
}

.date {
  font-size: 0.9rem;
  color: #6b7280;
}

.notes {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.85rem;
  color: #6b7280;
}

.timestamp {
  font-size: 0.75rem;
  color: #9ca3af;
  white-space: nowrap;
}

/* Bulk Actions Styling */
.bulk-actions-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 1rem;
  margin-bottom: 1rem;
}

.bulk-actions-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.selection-info {
  font-weight: 500;
  color: #374151;
}

.bulk-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.bulk-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #1f2937;
  font-size: 0.9rem;
  cursor: pointer;
}

.bulk-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  min-width: 200px;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
}

/* Checkbox Column */
.checkbox-col {
  width: 40px;
  text-align: center;
}

.checkbox-col input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.selected-row {
  background-color: #eff6ff !important;
}

/* Inline Editing */
.edit-select,
.edit-input {
  padding: 0.25rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.85rem;
  width: 100%;
  max-width: 150px;
}

.edit-select:focus,
.edit-input:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 2px rgba(30, 58, 138, 0.1);
}

/* Action Buttons */
.actions-col {
  width: 80px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
  justify-content: center;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0.25rem;
  transition: transform 0.2s;
  border-radius: 4px;
}

.btn-icon:hover {
  transform: scale(1.2);
  background: #f3f4f6;
}

.btn-save {
  color: #15803d;
}

.btn-save:hover {
  background: #f0fdf4;
}

.btn-cancel {
  color: #991b1b;
}

.btn-cancel:hover {
  background: #fef2f2;
}

.error {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee2e2;
  border-radius: 6px;
  color: #991b1b;
}

@media (max-width: 768px) {
  .controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .selector-group {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
