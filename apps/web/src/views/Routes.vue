<template>
  <div class="routes">
    <h2>Route Planning Results</h2>
    
    <!-- Workspace and State Display -->
    <div v-if="workspaceFromResult && stateFromResult" class="context-display">
      <div class="context-item">
        <span class="context-label">Workspace:</span>
        <span class="context-value">{{ workspaceFromResult }}</span>
      </div>
      <div class="context-item">
        <span class="context-label">State:</span>
        <span class="context-value">{{ stateFromResult }}</span>
      </div>
    </div>
    
    <div v-if="!store.planResult" class="no-routes">
      <p>No route planning results available. Please run a plan first.</p>
      <router-link to="/planning" class="btn btn-primary">
        Go to Planning
      </router-link>
    </div>
    
    <div v-else class="routes-container">
      <!-- Plan Configuration -->
      <div v-if="store.planRequest" class="plan-config-section">
        <h3>📋 Plan Configuration</h3>
        <div class="config-grid">
          <!-- Planning Mode -->
          <div class="config-card">
            <div class="config-header">
              <span class="config-icon">⚙️</span>
              <h4>Planning Mode</h4>
            </div>
            <div class="config-content">
              <div class="mode-badge" :class="planningModeClass">
                {{ planningModeLabel }}
              </div>
              <p class="config-description">{{ planningModeDescription }}</p>
            </div>
          </div>

          <!-- Date Configuration -->
          <div class="config-card">
            <div class="config-header">
              <span class="config-icon">📅</span>
              <h4>Schedule</h4>
            </div>
            <div class="config-content">
              <div class="config-row">
                <span class="config-label">Start Date:</span>
                <span class="config-value">{{ formatDate(store.planRequest.start_date) || 'Not set' }}</span>
              </div>
              <div v-if="store.planRequest.end_date" class="config-row">
                <span class="config-label">End Date:</span>
                <span class="config-value">{{ formatDate(store.planRequest.end_date) }}</span>
              </div>
              <div v-if="store.planRequest.holidays && store.planRequest.holidays.length > 0" class="config-row">
                <span class="config-label">Holidays:</span>
                <span class="config-value">{{ store.planRequest.holidays.length }} excluded</span>
              </div>
            </div>
          </div>

          <!-- Team Configuration -->
          <div class="config-card">
            <div class="config-header">
              <span class="config-icon">👥</span>
              <h4>Team Configuration</h4>
            </div>
            <div class="config-content">
              <div class="config-row">
                <span class="config-label">Teams:</span>
                <span class="config-value-highlight">{{ store.planRequest.team_config?.teams || 0 }}</span>
              </div>
              <div v-if="store.planRequest.use_clusters" class="config-row">
                <span class="config-label">Clustering:</span>
                <span class="config-value">✓ Enabled</span>
              </div>
            </div>
          </div>

          <!-- Route Constraints -->
          <div class="config-card">
            <div class="config-header">
              <span class="config-icon">⏱️</span>
              <h4>Route Constraints</h4>
            </div>
            <div class="config-content">
              <div class="config-row">
                <span class="config-label">Max Route Time:</span>
                <span class="config-value">{{ store.planRequest.max_route_minutes }} min</span>
              </div>
              <div class="config-row">
                <span class="config-label">Break Time:</span>
                <span class="config-value">{{ store.planRequest.break_minutes }} min</span>
              </div>
              <div class="config-row">
                <span class="config-label">Service Time/Site:</span>
                <span class="config-value">{{ store.planRequest.service_minutes_per_site }} min</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="card">
          <h4>Total Sites</h4>
          <p class="stat">{{ totalSites }}</p>
        </div>
        <div class="card">
          <h4>Team-Days</h4>
          <p class="stat">{{ store.planResult.team_days?.length || 0 }}</p>
        </div>
        <div class="card">
          <h4>Unassigned</h4>
          <p class="stat">{{ store.planResult.unassigned || 0 }}</p>
        </div>
        <div class="card">
          <h4>Date Range</h4>
          <p class="stat-small">
            {{ formatDate(store.planResult.start_date) }} - 
            {{ formatDate(store.planResult.end_date) }}
          </p>
        </div>
      </div>
      
      <!-- Route Map -->
      <div class="map-section">
        <h3>Route Map</h3>
        <RouteMap :result="store.planResult" :mapUrl="latestMapUrl" />
      </div>
      
      <!-- Team Schedule -->
      <div class="schedule-section">
        <h3>Team Schedule</h3>
        <TeamSchedule :teamDays="store.planResult.team_days" />
      </div>
      
      <!-- File History Section -->
      <div v-if="workspaceFromResult && stateFromResult" class="file-history-section">
        <h3>📁 Generated Files</h3>
        <div v-if="loadingFiles" class="loading">Loading files...</div>
        <div v-else-if="groupedFiles.length > 0" class="file-history">
          <!-- Current Plan -->
          <div v-if="groupedFiles[0]" class="plan-group current-plan">
            <div class="plan-header">
              <div class="plan-title">
                <span class="current-badge">Current Plan</span>
                <span class="plan-timestamp">{{ formatPlanTimestamp(groupedFiles[0].timestamp) }}</span>
              </div>
            </div>
            <div class="plan-files">
              <div v-for="file in groupedFiles[0].files" :key="file.filename" class="file-item">
                <div class="file-info">
                  <span class="file-icon">{{ file.type === 'map' ? '🗺️' : '📄' }}</span>
                  <div class="file-details">
                    <a :href="file.url" target="_blank" class="file-link">
                      {{ file.filename }}
                    </a>
                    <span class="file-meta">
                      {{ formatFileSize(file.size) }}
                    </span>
                  </div>
                </div>
                <a :href="file.url" target="_blank" class="btn btn-sm btn-primary">
                  {{ file.type === 'map' ? 'View Map' : 'Download' }}
                </a>
              </div>
            </div>
          </div>

          <!-- Previous Plans -->
          <div v-if="groupedFiles.length > 1" class="previous-plans">
            <h4>Previous Plans</h4>
            <div v-for="(group, index) in groupedFiles.slice(1)" :key="group.timestamp" class="plan-group">
              <div class="plan-header">
                <div class="plan-title">
                  <span class="plan-timestamp">{{ formatPlanTimestamp(group.timestamp) }}</span>
                </div>
                <button 
                  @click="deletePlan(group)" 
                  class="btn-delete"
                  :disabled="deletingPlan === group.timestamp"
                  title="Delete this plan and all its files"
                >
                  {{ deletingPlan === group.timestamp ? 'Deleting...' : '🗑️ Delete' }}
                </button>
              </div>
              <div class="plan-files">
                <div v-for="file in group.files" :key="file.filename" class="file-item">
                  <div class="file-info">
                    <span class="file-icon">{{ file.type === 'map' ? '🗺️' : '📄' }}</span>
                    <div class="file-details">
                      <a :href="file.url" target="_blank" class="file-link">
                        {{ file.filename }}
                      </a>
                      <span class="file-meta">
                        {{ formatFileSize(file.size) }}
                      </span>
                    </div>
                  </div>
                  <a :href="file.url" target="_blank" class="btn btn-sm btn-secondary">
                    {{ file.type === 'map' ? 'View' : 'Download' }}
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="no-files">
          <p>No output files generated yet. Run a plan to generate route maps and results.</p>
        </div>
      </div>

      <!-- Export Options -->
      <div class="export-section">
        <button @click="exportJSON" class="btn btn-secondary">
          Export JSON
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { outputAPI, workspaceAPI } from '../services/api'
import RouteMap from '../components/RouteMap.vue'
import TeamSchedule from '../components/TeamSchedule.vue'

const store = usePlanningStore()
const outputFiles = ref([])
const loadingFiles = ref(false)
const loadingResult = ref(false)
const deletingPlan = ref(null)

// Group files by timestamp (pairs of JSON + HTML with same timestamp)
const groupedFiles = computed(() => {
  if (!outputFiles.value || outputFiles.value.length === 0) return []
  
  // Extract timestamp from filename (e.g., route_plan_20260108_163917.json -> 20260108_163917)
  const groups = {}
  
  outputFiles.value.forEach(file => {
    const match = file.filename.match(/(\d{8}_\d{6})/)
    if (match) {
      const timestamp = match[1]
      if (!groups[timestamp]) {
        groups[timestamp] = {
          timestamp,
          files: []
        }
      }
      groups[timestamp].files.push(file)
    }
  })
  
  // Convert to array and sort by timestamp (newest first)
  return Object.values(groups).sort((a, b) => b.timestamp.localeCompare(a.timestamp))
})

const totalSites = computed(() => {
  if (!store.planResult?.team_days) return 0
  return store.planResult.team_days.reduce((sum, td) => sum + (td.site_ids?.length || 0), 0)
})

// Get workspace and state from planRequest (which is populated when planning)
const workspaceFromResult = computed(() => {
  return store.planRequest?.workspace || store.workspace
})

const stateFromResult = computed(() => {
  return store.planRequest?.state_abbr || store.stateAbbr
})

// Planning mode display
const planningModeLabel = computed(() => {
  if (!store.planRequest) return 'Unknown'
  // Fixed Calendar mode has an end_date, Fixed Crew mode does not
  return store.planRequest.end_date ? 'Fixed Calendar' : 'Fixed Crew'
})

const planningModeClass = computed(() => {
  return store.planRequest?.end_date ? 'mode-calendar' : 'mode-crew'
})

const planningModeDescription = computed(() => {
  if (!store.planRequest) return ''
  return store.planRequest.end_date 
    ? 'System calculated minimum crews needed to complete by end date'
    : 'System calculated completion time with specified number of crews'
})

const latestMapUrl = computed(() => {
  if (!outputFiles.value || outputFiles.value.length === 0) {
    return null
  }
  
  // Find the most recent map file (files are already sorted by modified time, newest first)
  const latestMap = outputFiles.value.find(file => file.type === 'map')
  
  if (!latestMap) return null
  
  // Append authentication token to URL for iframe loading
  const token = localStorage.getItem('auth_token')
  if (token) {
    const separator = latestMap.url.includes('?') ? '&' : '?'
    return `${latestMap.url}${separator}token=${token}`
  }
  
  return latestMap.url
})

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  // Parse date string directly to avoid timezone conversion issues
  // Date strings from backend are in YYYY-MM-DD format
  const [year, month, day] = dateStr.split('-').map(Number)
  const date = new Date(year, month - 1, day) // month is 0-indexed
  return date.toLocaleDateString()
}

function formatPlanTimestamp(timestamp) {
  // timestamp format: 20260108_163917 (YYYYMMDD_HHMMSS)
  const dateStr = timestamp.substring(0, 8)
  const timeStr = timestamp.substring(9)
  
  const year = dateStr.substring(0, 4)
  const month = dateStr.substring(4, 6)
  const day = dateStr.substring(6, 8)
  
  const hour = timeStr.substring(0, 2)
  const minute = timeStr.substring(2, 4)
  
  const date = new Date(year, month - 1, day, hour, minute)
  return date.toLocaleString()
}

async function deletePlan(group) {
  const confirmMsg = `Delete this plan and all ${group.files.length} file(s)?\n\nThis action cannot be undone.`
  
  if (!confirm(confirmMsg)) {
    return
  }
  
  deletingPlan.value = group.timestamp
  
  try {
    const workspace = workspaceFromResult.value
    const state = stateFromResult.value
    
    // Delete all files in the group
    for (const file of group.files) {
      await outputAPI.deleteFile(workspace, state, file.filename)
    }
    
    // Refresh the file list
    await fetchOutputFiles()
    
    alert(`Plan deleted successfully (${group.files.length} file(s) removed)`)
  } catch (error) {
    console.error('Failed to delete plan:', error)
    alert('Failed to delete plan. Please try again.')
  } finally {
    deletingPlan.value = null
  }
}

function exportJSON() {
  const dataStr = JSON.stringify(store.planResult, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `route_plan_${new Date().toISOString()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

async function fetchOutputFiles() {
  const workspace = workspaceFromResult.value
  const state = stateFromResult.value
  
  if (!workspace || !state) {
    console.log('Workspace or state not set, skipping file fetch')
    return
  }
  
  loadingFiles.value = true
  try {
    console.log(`Fetching files from: /workspaces/${workspace}/output/${state}`)
    const response = await outputAPI.listFiles(workspace, state)
    console.log('API response:', response.data)
    
    // Add authentication token to all file URLs
    const token = localStorage.getItem('auth_token')
    const files = response.data.files || []
    
    if (token) {
      files.forEach(file => {
        // Add token as query parameter
        file.url = `${file.url}?token=${token}`
      })
    }
    
    outputFiles.value = files
    console.log('Output files set:', outputFiles.value.length, 'files')
  } catch (error) {
    console.error('Error fetching output files:', error)
    outputFiles.value = []
  } finally {
    loadingFiles.value = false
  }
}

async function loadLatestResult() {
  const workspace = workspaceFromResult.value
  const state = stateFromResult.value
  
  // Check for empty strings as well as falsy values
  if (!workspace || workspace.trim() === '' || !state || state.trim() === '') {
    console.log('Workspace or state not set, skipping result load', { workspace, state })
    return
  }
  
  loadingResult.value = true
  try {
    console.log(`Loading latest result for: ${workspace}/${state}`)
    const response = await outputAPI.getLatestResult(workspace, state)
    
    if (response.data.result && !response.data.error) {
      // Update store with the loaded result and metadata
      store.setPlanResult(response.data.result)
      
      // Also update planRequest with metadata if available
      if (response.data.metadata) {
        store.updatePlanRequest({
          workspace: response.data.metadata.workspace,
          state_abbr: response.data.metadata.state_abbr,
          use_clusters: response.data.metadata.use_clusters,
          max_route_minutes: response.data.metadata.max_route_minutes,
          service_minutes_per_site: response.data.metadata.service_minutes_per_site
        })
      }
      
      console.log('Latest result loaded successfully')
    } else {
      console.log('No previous results found', response.data)
    }
  } catch (error) {
    console.error('Error loading latest result:', error)
  } finally {
    loadingResult.value = false
  }
}

async function autoSelectFirstState() {
  // If workspace is set but state is not, auto-select the first state
  const hasWorkspace = store.workspace && store.workspace.trim() !== ''
  const hasState = store.stateAbbr && store.stateAbbr.trim() !== ''
  
  console.log('autoSelectFirstState check:', { hasWorkspace, hasState, workspace: store.workspace, state: store.stateAbbr })
  
  if (hasWorkspace && !hasState) {
    try {
      console.log(`Fetching states for workspace: ${store.workspace}`)
      const response = await workspaceAPI.getStates(store.workspace)
      const states = response.data.states || []
      
      console.log(`Found ${states.length} states:`, states)
      
      if (states.length > 0) {
        const firstState = states[0].state_abbr
        console.log(`Auto-selecting first state: ${firstState}`)
        store.setStateAbbr(firstState)
      }
    } catch (error) {
      console.error('Error fetching states for auto-select:', error)
    }
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp * 1000) // Convert Unix timestamp to milliseconds
  return date.toLocaleString()
}

// On mount, auto-select first state if needed, then load results
onMounted(async () => {
  console.log('Results page mounted')
  console.log('Store workspace:', store.workspace)
  console.log('Store stateAbbr:', store.stateAbbr)
  
  // If we already have both workspace and state (from localStorage), load results immediately
  if (store.workspace && store.stateAbbr) {
    console.log('Loading results for existing workspace/state')
    await loadLatestResult()
    await fetchOutputFiles()
  } else {
    // Otherwise, try to auto-select first state
    console.log('Auto-selecting first state')
    await autoSelectFirstState()
    // After auto-select, load results if we now have both
    if (store.workspace && store.stateAbbr) {
      await loadLatestResult()
      await fetchOutputFiles()
    }
  }
})

// Watch for workspace changes - auto-select first state and load results
watch(() => store.workspace, async (newWorkspace, oldWorkspace) => {
  console.log('Workspace changed:', oldWorkspace, '->', newWorkspace)
  if (newWorkspace) {
    await autoSelectFirstState()
    if (store.stateAbbr) {
      await loadLatestResult()
      await fetchOutputFiles()
    }
  }
})

// Watch for state changes - load results for the new state
watch(() => store.stateAbbr, async (newState, oldState) => {
  console.log('State changed:', oldState, '->', newState)
  if (newState && store.workspace) {
    await loadLatestResult()
    await fetchOutputFiles()
  }
})

// Refresh output files and results when workspace/state from result changes
watch([workspaceFromResult, stateFromResult], async ([newWorkspace, newState], [oldWorkspace, oldState]) => {
  console.log('workspaceFromResult or stateFromResult changed')
  // Only reload if values actually changed and both are present
  if ((newWorkspace !== oldWorkspace || newState !== oldState) && newWorkspace && newState) {
    await loadLatestResult()
    await fetchOutputFiles()
  }
})

// Refresh output files when a new plan is created
watch(() => store.planResult, () => {
  if (store.planResult) {
    // Wait a moment for the file to be written
    setTimeout(() => fetchOutputFiles(), 1000)
  }
})
</script>

<style scoped>
.routes {
  max-width: 1200px;
  margin: 0 auto;
}

.routes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

h2 {
  color: #1e3a8a;
  margin: 0 0 1rem 0;
}

.context-display {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: #f3f4f6;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.context-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.context-label {
  font-weight: 600;
  color: #6b7280;
  font-size: 0.9rem;
}

.context-value {
  font-weight: 500;
  color: #1e3a8a;
  font-size: 0.95rem;
}

.selector-group {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.selector label {
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
  white-space: nowrap;
}

.select-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #1f2937;
  font-size: 0.9rem;
  min-width: 180px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.select-input:hover:not(:disabled) {
  border-color: #1e3a8a;
}

.select-input:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

.select-input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.6;
}

.no-routes {
  text-align: center;
  padding: 3rem;
  background: #f9fafb;
  border-radius: 8px;
}

.routes-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.plan-config-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.plan-config-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1e3a8a;
  font-size: 1.25rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.config-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 1rem;
  transition: all 0.2s;
}

.config-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.config-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.config-icon {
  font-size: 1.25rem;
}

.config-header h4 {
  margin: 0;
  color: #374151;
  font-size: 0.95rem;
  font-weight: 600;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.config-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.config-label {
  font-size: 0.85rem;
  color: #6b7280;
  font-weight: 500;
}

.config-value {
  font-size: 0.9rem;
  color: #1f2937;
  font-weight: 500;
}

.config-value-highlight {
  font-size: 1.5rem;
  color: #1e3a8a;
  font-weight: 700;
}

.mode-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: 0.5rem;
}

.mode-crew {
  background: #dbeafe;
  color: #1e40af;
  border: 2px solid #93c5fd;
}

.mode-calendar {
  background: #fef3c7;
  color: #b45309;
  border: 2px solid #fcd34d;
}

.config-description {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
  line-height: 1.4;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  text-align: center;
}

.card h4 {
  margin: 0 0 0.5rem 0;
  color: #6b7280;
  font-size: 0.9rem;
  font-weight: 500;
  text-transform: uppercase;
}

.stat {
  font-size: 2rem;
  font-weight: bold;
  color: #1e3a8a;
  margin: 0;
}

.stat-small {
  font-size: 1rem;
  color: #1e3a8a;
  margin: 0;
}

.map-section,
.schedule-section,
.file-history-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.map-section h3,
.schedule-section h3,
.file-history-section h3 {
  margin-top: 0;
  color: #1e3a8a;
}

/* File History Styles */
.file-history {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.plan-group {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  background: #f9fafb;
  transition: all 0.2s;
}

.plan-group:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.current-plan {
  border-color: #3b82f6;
  background: #eff6ff;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.current-plan .plan-header {
  border-bottom-color: #93c5fd;
}

.plan-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.current-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #3b82f6;
  color: white;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.plan-timestamp {
  font-size: 0.95rem;
  color: #374151;
  font-weight: 600;
}

.btn-delete {
  padding: 0.5rem 1rem;
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.btn-delete:hover:not(:disabled) {
  background: #fecaca;
  border-color: #f87171;
}

.btn-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.plan-files {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.previous-plans {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.previous-plans h4 {
  margin: 0 0 0.5rem 0;
  color: #6b7280;
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.export-section {
  display: flex;
  gap: 1rem;
  justify-content: center;
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
  text-decoration: none;
  display: inline-block;
}

.btn-primary:hover {
  background-color: #1e40af;
}

.btn-secondary {
  background-color: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background-color: #4b5563;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

.output-files-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.output-files-section h3 {
  margin-top: 0;
  color: #1e3a8a;
  margin-bottom: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

.no-files {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
  background: #f9fafb;
  border-radius: 6px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.file-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.file-icon {
  font-size: 1.5rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-link {
  color: #1e3a8a;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
}

.file-link:hover {
  text-decoration: underline;
}

.file-meta {
  font-size: 0.8rem;
  color: #6b7280;
}
</style>
