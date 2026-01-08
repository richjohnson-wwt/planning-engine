<template>
  <div class="planning-form">
    <form @submit.prevent="handleSubmit">
      <!-- Date Configuration -->
      <div class="form-section">
        <h4>Planning Dates</h4>
        
        <div class="form-group">
          <label>
            <input type="radio" v-model="planningMode" value="fixed-crew" />
            Fixed Crew Mode
          </label>
          <p class="help-text">System calculates how long it will take with the specified number of crews</p>
        </div>
        
        <div class="form-group">
          <label>
            <input type="radio" v-model="planningMode" value="fixed-calendar" />
            Fixed Calendar Mode
          </label>
          <p class="help-text">System calculates how many crews are needed to complete by the end date</p>
        </div>
        
        <div class="form-group">
          <label for="start-date">
            Start Date
            <span v-if="planningMode === 'fixed-crew'" class="optional-label">(optional - defaults to today)</span>
            <span v-else class="required-label">*</span>
          </label>
          <input
            id="start-date"
            v-model="formData.start_date"
            type="date"
            class="form-control"
            :placeholder="planningMode === 'fixed-crew' ? 'Leave blank for today' : ''"
          />
        </div>
        
        <div v-if="planningMode === 'fixed-calendar'" class="form-group">
          <label for="end-date">
            End Date <span class="required-label">*</span>
          </label>
          <input
            id="end-date"
            v-model="formData.end_date"
            type="date"
            class="form-control"
          />
        </div>
      </div>
      
      <!-- Route Configuration -->
      <div class="form-section">
        <h4>Route Configuration</h4>
        
        <div class="form-group">
          <label for="max-route">Max Route Minutes</label>
          <input
            id="max-route"
            v-model.number="formData.max_route_minutes"
            type="number"
            min="60"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label for="service-time">Service Minutes per Site</label>
          <input
            id="service-time"
            v-model.number="formData.service_minutes_per_site"
            type="number"
            min="1"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label for="break-time">Break Minutes</label>
          <input
            id="break-time"
            v-model.number="formData.break_minutes"
            type="number"
            min="0"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="formData.use_clusters" />
            Use Clustering
          </label>
          <p v-if="clusterInfo?.clustered_file_exists && !formData.use_clusters" class="warning-text">
            ⚠️ Clustering is available ({{ clusterInfo.cluster_count }} clusters, {{ clusterInfo.total_sites }} sites).
            Disabling clustering may cause planning failures for geographically dispersed sites.
          </p>
          <p v-if="clusterInfo?.clustered_file_exists && formData.use_clusters" class="info-text">
            ✓ Using {{ clusterInfo.cluster_count }} clusters for {{ clusterInfo.total_sites }} sites
          </p>
        </div>
      </div>
      
      <!-- Team Configuration -->
      <div class="form-section">
        <h4>Team Configuration</h4>
        
        <div v-if="!isTeamsOutput" class="form-group">
          <label for="teams">
            Number of Teams
            <span v-if="isTeamsLocked" class="locked-label">🔒 Locked</span>
          </label>
          <input
            id="teams"
            v-model.number="formData.team_config.teams"
            type="number"
            min="1"
            class="form-control"
            :disabled="isTeamsLocked"
            :class="{ 'locked-field': isTeamsLocked }"
          />
          <p class="help-text">{{ teamsHelpText }}</p>
        </div>
        
        <div v-else class="form-group">
          <label>Number of Teams</label>
          <p class="output-text">Will be calculated based on date range</p>
          <p class="help-text">{{ teamsHelpText }}</p>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label for="workday-start">Workday Start</label>
            <input
              id="workday-start"
              v-model="formData.team_config.workday.start"
              type="time"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label for="workday-end">Workday End</label>
            <input
              id="workday-end"
              v-model="formData.team_config.workday.end"
              type="time"
              class="form-control"
            />
          </div>
        </div>
      </div>
      
      <button type="submit" class="btn btn-primary btn-large" :disabled="isLoading">
        <span v-if="!isLoading">Generate Plan</span>
        <span v-else>Generating Plan...</span>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { usePlanningStore } from '../stores/planning'
import api from '../services/api'

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit'])
const store = usePlanningStore()

const planningMode = ref('fixed-crew')
const formData = ref({ ...store.planRequest })
const clusterInfo = ref(null)
const loadingClusterInfo = ref(false)

// Computed property to determine if teams field should be locked
const isTeamsLocked = computed(() => {
  return formData.value.use_clusters && 
         planningMode.value === 'fixed-crew' && 
         clusterInfo.value?.clustered_file_exists
})

// Computed property to determine if teams field should be hidden (output only)
const isTeamsOutput = computed(() => {
  return planningMode.value === 'fixed-calendar'
})

// Computed property for teams field help text
const teamsHelpText = computed(() => {
  if (isTeamsLocked.value) {
    return `Locked to cluster count (${clusterInfo.value.cluster_count} clusters detected)`
  }
  if (isTeamsOutput.value) {
    return 'System will calculate the minimum crews needed for the date range'
  }
  return 'Number of crews/teams available to work'
})

// Fetch cluster info when clustering is enabled and workspace/state are set
async function fetchClusterInfo() {
  if (!formData.value.workspace || !formData.value.state_abbr) {
    return
  }
  
  loadingClusterInfo.value = true
  try {
    const response = await api.get(
      `/workspaces/${formData.value.workspace}/states/${formData.value.state_abbr}/cluster-info`
    )
    clusterInfo.value = response.data
    
    // If teams should be locked, set it to cluster count
    if (isTeamsLocked.value) {
      formData.value.team_config.teams = clusterInfo.value.cluster_count
    }
  } catch (error) {
    console.error('Failed to fetch cluster info:', error)
    clusterInfo.value = null
  } finally {
    loadingClusterInfo.value = false
  }
}

// Watch for changes that should trigger cluster info fetch
watch([
  () => formData.value.use_clusters,
  () => formData.value.workspace,
  () => formData.value.state_abbr
], () => {
  if (formData.value.use_clusters) {
    fetchClusterInfo()
  } else {
    clusterInfo.value = null
  }
}, { immediate: true })

// Watch planning mode to clear end_date when switching to fixed-crew
watch(planningMode, (newMode) => {
  if (newMode === 'fixed-crew') {
    formData.value.end_date = null
  }
})

// Watch for cluster lock changes to update teams
watch(isTeamsLocked, (locked) => {
  if (locked && clusterInfo.value) {
    formData.value.team_config.teams = clusterInfo.value.cluster_count
  }
})

// Watch for cluster info changes to update team count
// This handles the case where clustering is already enabled and cluster info gets updated
watch(() => clusterInfo.value?.cluster_count, (newCount) => {
  if (isTeamsLocked.value && newCount !== undefined && newCount !== null) {
    formData.value.team_config.teams = newCount
  }
})

// Watch store for workspace and state changes
watch(() => store.workspace, (newWorkspace) => {
  formData.value.workspace = newWorkspace
})

watch(() => store.stateAbbr, (newState) => {
  formData.value.state_abbr = newState
})

function handleSubmit() {
  // Ensure latest workspace and state from store
  formData.value.workspace = store.workspace
  formData.value.state_abbr = store.stateAbbr
  
  // Ensure end_date is null for fixed-crew mode
  if (planningMode.value === 'fixed-crew') {
    formData.value.end_date = null
    
    // Default start_date to today if not provided
    if (!formData.value.start_date) {
      const today = new Date()
      formData.value.start_date = today.toISOString().split('T')[0]
    }
  }
  
  // Update store with form data
  store.updatePlanRequest(formData.value)
  emit('submit')
}
</script>

<style scoped>
.planning-form {
  max-width: 600px;
}

.form-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.form-section:last-of-type {
  border-bottom: none;
}

.form-section h4 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
}

.form-control {
  width: 100%;
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

input[type="checkbox"],
input[type="radio"] {
  margin-right: 0.5rem;
}

.help-text {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #6b7280;
  font-weight: 400;
}

.optional-label {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 400;
  font-style: italic;
}

.required-label {
  color: #dc2626;
  font-weight: 600;
}

.locked-label {
  font-size: 0.8rem;
  color: #f59e0b;
  font-weight: 600;
  margin-left: 0.5rem;
}

.locked-field {
  background-color: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.7;
}

.output-text {
  margin: 0.5rem 0;
  padding: 0.75rem;
  background-color: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  color: #0369a1;
  font-weight: 500;
  font-size: 0.95rem;
}

.warning-text {
  margin: 0.5rem 0 0 0;
  padding: 0.5rem;
  background-color: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 4px;
  color: #92400e;
  font-size: 0.85rem;
  font-weight: 500;
}

.info-text {
  margin: 0.5rem 0 0 0;
  padding: 0.5rem;
  background-color: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 4px;
  color: #065f46;
  font-size: 0.85rem;
  font-weight: 500;
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

.btn-primary:hover {
  background-color: #1e40af;
}

.btn-primary:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-primary:disabled:hover {
  background-color: #9ca3af;
}

.btn-large {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
}
</style>
