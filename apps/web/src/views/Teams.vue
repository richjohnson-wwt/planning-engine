<template>
  <div class="teams">
    <h2>Team Management</h2>
    
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
            @change="loadTeams"
            class="select-input"
            :disabled="!store.workspace || loadingStates"
          >
            <option value="">Select a state...</option>
            <option v-for="state in availableStates" :key="state.name" :value="state.name">
              {{ state.name }} ({{ state.site_count }} sites)
            </option>
          </select>
        </div>
      </div>
      
      <button 
        @click="showAddTeamModal = true" 
        class="btn btn-primary"
        :disabled="!selectedState"
      >
        + Add Team
      </button>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <p>Loading teams...</p>
    </div>
    
    <!-- No State Selected -->
    <div v-else-if="!selectedState" class="no-selection">
      <p>Please select a workspace and state to manage teams.</p>
      <router-link to="/" class="btn btn-secondary">Go to Home</router-link>
    </div>
    
    <!-- Teams Table -->
    <div v-else class="teams-container">
      <div v-if="teams.length === 0" class="no-teams">
        <p>No teams found for {{ selectedState }}.</p>
        <p>Click "Add Team" to create your first team.</p>
      </div>
      
      <div v-else class="teams-table-container">
        <table class="teams-table">
          <thead>
            <tr>
              <th>Team ID</th>
              <th>Team Name</th>
              <th>City</th>
              <th>Cluster</th>
              <th>Contact</th>
              <th>Phone</th>
              <th>Availability</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="team in teams" :key="team.team_id">
              <td class="team-id">{{ team.team_id }}</td>
              <td class="team-name">{{ team.team_name }}</td>
              <td>{{ team.city }}</td>
              <td class="cluster-id">
                {{ team.cluster_id !== null && team.cluster_id !== undefined ? `Cluster ${team.cluster_id}` : '-' }}
              </td>
              <td>{{ team.contact_name || '-' }}</td>
              <td>{{ team.contact_phone || '-' }}</td>
              <td class="availability">
                <span v-if="team.availability_start && team.availability_end">
                  {{ formatDate(team.availability_start) }} - {{ formatDate(team.availability_end) }}
                </span>
                <span v-else>-</span>
              </td>
              <td class="actions">
                <button @click="editTeam(team)" class="btn-icon" title="Edit">
                  ✏️
                </button>
                <button @click="confirmDelete(team)" class="btn-icon btn-danger" title="Delete">
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Add/Edit Team Modal -->
    <div v-if="showAddTeamModal || editingTeam" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingTeam ? 'Edit Team' : 'Add New Team' }}</h3>
          <button @click="closeModal" class="btn-close">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label for="team-id">Team ID</label>
            <input 
              id="team-id"
              v-model="formData.team_id" 
              type="text" 
              class="form-input"
              :readonly="!!editingTeam"
              placeholder="Auto-generated"
            />
          </div>
          
          <div class="form-group">
            <label for="team-name">Team Name *</label>
            <input 
              id="team-name"
              v-model="formData.team_name" 
              type="text" 
              class="form-input"
              required
              placeholder="e.g., Team Alpha"
            />
          </div>
          
          <div class="form-group">
            <label for="city">City *</label>
            <select 
              id="city"
              v-model="formData.city" 
              class="form-input"
              required
            >
              <option value="">Select a city...</option>
              <option v-for="city in availableCities" :key="city" :value="city">
                {{ city }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="cluster-id">Cluster (Optional)</label>
            <input 
              id="cluster-id"
              v-model.number="formData.cluster_id" 
              type="number" 
              class="form-input"
              placeholder="Leave empty if not cluster-specific"
              min="0"
            />
          </div>
          
          <div class="form-group">
            <label for="contact-name">Contact Name</label>
            <input 
              id="contact-name"
              v-model="formData.contact_name" 
              type="text" 
              class="form-input"
              placeholder="Team lead or contact person"
            />
          </div>
          
          <div class="form-group">
            <label for="contact-phone">Contact Phone</label>
            <input 
              id="contact-phone"
              v-model="formData.contact_phone" 
              type="tel" 
              class="form-input"
              placeholder="555-0123"
            />
          </div>
          
          <div class="form-group">
            <label for="contact-email">Contact Email</label>
            <input 
              id="contact-email"
              v-model="formData.contact_email" 
              type="email" 
              class="form-input"
              placeholder="contact@example.com"
            />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label for="availability-start">Available From</label>
              <input 
                id="availability-start"
                v-model="formData.availability_start" 
                type="date" 
                class="form-input"
              />
            </div>
            
            <div class="form-group">
              <label for="availability-end">Available Until</label>
              <input 
                id="availability-end"
                v-model="formData.availability_end" 
                type="date" 
                class="form-input"
              />
            </div>
          </div>
          
          <div class="form-group">
            <label for="notes">Notes</label>
            <textarea 
              id="notes"
              v-model="formData.notes" 
              class="form-input"
              rows="3"
              placeholder="Additional notes about this team..."
            ></textarea>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Cancel</button>
          <button @click="saveTeam" class="btn btn-primary" :disabled="!isFormValid">
            {{ editingTeam ? 'Update Team' : 'Add Team' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Delete Confirmation Modal -->
    <div v-if="deletingTeam" class="modal-overlay" @click.self="deletingTeam = null">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>Confirm Delete</h3>
          <button @click="deletingTeam = null" class="btn-close">×</button>
        </div>
        
        <div class="modal-body">
          <p>Are you sure you want to delete <strong>{{ deletingTeam.team_name }}</strong> ({{ deletingTeam.team_id }})?</p>
          <p class="warning-text">This action cannot be undone.</p>
        </div>
        
        <div class="modal-footer">
          <button @click="deletingTeam = null" class="btn btn-secondary">Cancel</button>
          <button @click="deleteTeam" class="btn btn-danger">Delete Team</button>
        </div>
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
import { teamAPI, workspaceAPI } from '../services/api'

const store = usePlanningStore()

// State
const selectedState = ref('')
const teams = ref([])
const availableStates = ref([])
const availableCities = ref([])
const loading = ref(false)
const loadingStates = ref(false)
const error = ref('')

// Modal state
const showAddTeamModal = ref(false)
const editingTeam = ref(null)
const deletingTeam = ref(null)

// Form data
const formData = ref({
  team_id: '',
  team_name: '',
  city: '',
  cluster_id: null,
  contact_name: '',
  contact_phone: '',
  contact_email: '',
  availability_start: '',
  availability_end: '',
  notes: ''
})

// Computed
const isFormValid = computed(() => {
  return formData.value.team_name && formData.value.city
})

// Methods
async function loadStates() {
  if (!store.workspace) return
  
  loadingStates.value = true
  try {
    const response = await workspaceAPI.getStates(store.workspace)
    availableStates.value = response.data.states || []
    
    // Auto-select state if only one available
    if (availableStates.value.length === 1) {
      selectedState.value = availableStates.value[0].name
      await loadTeams()
    }
  } catch (err) {
    console.error('Failed to load states:', err)
    error.value = 'Failed to load states'
  } finally {
    loadingStates.value = false
  }
}

async function loadTeams() {
  if (!store.workspace || !selectedState.value) return
  
  loading.value = true
  error.value = ''
  
  try {
    const response = await teamAPI.list(store.workspace, selectedState.value)
    teams.value = response.data.teams || []
    
    // Load available cities for the dropdown
    await loadCities()
  } catch (err) {
    console.error('Failed to load teams:', err)
    error.value = 'Failed to load teams'
    teams.value = []
  } finally {
    loading.value = false
  }
}

async function loadCities() {
  if (!store.workspace || !selectedState.value) return
  
  try {
    const response = await teamAPI.getCities(store.workspace, selectedState.value)
    availableCities.value = response.data.cities || []
  } catch (err) {
    console.error('Failed to load cities:', err)
    availableCities.value = []
  }
}

async function generateTeamId() {
  if (!store.workspace || !selectedState.value) return ''
  
  try {
    const response = await teamAPI.generateId(store.workspace, selectedState.value)
    return response.data.team_id || ''
  } catch (err) {
    console.error('Failed to generate team ID:', err)
    return ''
  }
}

function editTeam(team) {
  editingTeam.value = team
  formData.value = { ...team }
  
  // Convert null to empty string for cluster_id
  if (formData.value.cluster_id === null || formData.value.cluster_id === undefined) {
    formData.value.cluster_id = ''
  }
}

function confirmDelete(team) {
  deletingTeam.value = team
}

async function saveTeam() {
  if (!isFormValid.value) return
  
  loading.value = true
  error.value = ''
  
  try {
    // Prepare team data
    const teamData = { ...formData.value }
    
    // Convert empty cluster_id to null
    if (teamData.cluster_id === '' || teamData.cluster_id === null) {
      teamData.cluster_id = null
    }
    
    // Convert empty strings to null for optional fields
    if (!teamData.contact_name) teamData.contact_name = null
    if (!teamData.contact_phone) teamData.contact_phone = null
    if (!teamData.contact_email) teamData.contact_email = null
    if (!teamData.availability_start) teamData.availability_start = null
    if (!teamData.availability_end) teamData.availability_end = null
    
    if (editingTeam.value) {
      // Update existing team
      await teamAPI.update(store.workspace, selectedState.value, teamData.team_id, teamData)
    } else {
      // Create new team (auto-generate ID if not provided)
      if (!teamData.team_id) {
        teamData.team_id = await generateTeamId()
      }
      await teamAPI.create(store.workspace, selectedState.value, teamData)
    }
    
    // Reload teams
    await loadTeams()
    closeModal()
  } catch (err) {
    console.error('Failed to save team:', err)
    error.value = err.response?.data?.error || 'Failed to save team'
  } finally {
    loading.value = false
  }
}

async function deleteTeam() {
  if (!deletingTeam.value) return
  
  loading.value = true
  error.value = ''
  
  try {
    await teamAPI.delete(store.workspace, selectedState.value, deletingTeam.value.team_id)
    
    // Reload teams
    await loadTeams()
    deletingTeam.value = null
  } catch (err) {
    console.error('Failed to delete team:', err)
    error.value = 'Failed to delete team'
  } finally {
    loading.value = false
  }
}

function closeModal() {
  showAddTeamModal.value = false
  editingTeam.value = null
  formData.value = {
    team_id: '',
    team_name: '',
    city: '',
    cluster_id: null,
    contact_name: '',
    contact_phone: '',
    contact_email: '',
    availability_start: '',
    availability_end: '',
    notes: ''
  }
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

// Lifecycle
onMounted(async () => {
  if (store.workspace) {
    await loadStates()
    
    // Auto-select state from Planning tab if available
    if (store.stateAbbr && !selectedState.value) {
      selectedState.value = store.stateAbbr
      await loadTeams()
    }
  }
})
</script>

<style scoped>
.teams {
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
}

.btn-primary {
  background-color: #1e3a8a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background-color: #4b5563;
}

.btn-danger {
  background-color: #dc2626;
  color: white;
}

.btn-danger:hover {
  background-color: #b91c1c;
}

.loading, .no-selection, .no-teams {
  text-align: center;
  padding: 3rem;
  background: #f9fafb;
  border-radius: 8px;
  color: #6b7280;
}

.teams-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  overflow: hidden;
}

.teams-table-container {
  overflow-x: auto;
}

.teams-table {
  width: 100%;
  border-collapse: collapse;
}

.teams-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.teams-table th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.teams-table tbody tr {
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s;
}

.teams-table tbody tr:hover {
  background-color: #f9fafb;
}

.teams-table td {
  padding: 0.75rem;
  color: #1f2937;
}

.team-id {
  font-family: monospace;
  font-size: 0.85rem;
  color: #6b7280;
}

.team-name {
  font-weight: 500;
}

.cluster-id {
  font-size: 0.9rem;
  color: #6b7280;
}

.availability {
  font-size: 0.85rem;
  color: #6b7280;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0.25rem;
  transition: transform 0.2s;
}

.btn-icon:hover {
  transform: scale(1.2);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-small {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  color: #1e3a8a;
}

.btn-close {
  background: none;
  border: none;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 2rem;
  height: 2rem;
}

.btn-close:hover {
  color: #1f2937;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
}

.form-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
}

.form-input:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

.form-input:disabled,
.form-input[readonly] {
  background: #f3f4f6;
  cursor: not-allowed;
}

textarea.form-input {
  resize: vertical;
  font-family: inherit;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.warning-text {
  color: #dc2626;
  font-weight: 500;
  margin-top: 0.5rem;
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
  
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
