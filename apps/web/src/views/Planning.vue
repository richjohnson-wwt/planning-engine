<template>
  <div class="planning">
    <h2>Route Planning</h2>
    
    <!-- Workflow Controls -->
    <div class="workflow-controls">
      <!-- 1. Workspace Display -->
      <div class="control-section">
        <label class="control-label">Workspace</label>
        <div class="workspace-display">
          {{ store.workspace || 'Not selected' }}
        </div>
        <p v-if="!store.workspace" class="help-text">Please select a workspace from the home page</p>
      </div>

      <!-- 2. Excel Upload Status -->
      <div class="control-section">
        <label class="control-label">Excel Data</label>
        <button 
          class="excel-button"
          :class="{ 'complete': excelComplete, 'incomplete': !excelComplete }"
          :disabled="!store.workspace"
          @click="handleExcelUpdate"
        >
          <span class="status-icon">{{ excelComplete ? '✓' : '!' }}</span>
          <span class="button-text">
            {{ excelComplete ? 'Excel Parsed - Update' : 'Upload Excel' }}
          </span>
          <span class="status-badge" :class="{ 'complete': excelComplete, 'incomplete': !excelComplete }">
            {{ excelComplete ? 'Complete' : 'Incomplete' }}
          </span>
        </button>
        <p class="help-text">{{ getExcelHelpText() }}</p>
      </div>

      <!-- 3. Geocode Editor -->
      <div class="control-section">
        <label class="control-label">Geocode Editor</label>
        <button 
          class="btn-editor"
          :disabled="!store.workspace || availableStates.length === 0"
          @click="openEditorModal"
          title="Edit geocoded site addresses and coordinates"
        >
          <span class="icon">✏️</span>
          Edit Geocoded Sites
        </button>
        <p class="help-text">Fix incorrectly geocoded addresses or coordinates</p>
      </div>

      <!-- 4. Clustering Settings -->
      <div class="control-section">
        <label class="control-label">Clustering Settings</label>
        <div class="cluster-settings">
          <label class="setting-label">Max Cluster Diameter</label>
          <div class="preset-buttons">
            <button 
              @click="maxDiameterMiles = 50" 
              :class="{ 'active': maxDiameterMiles === 50 }"
              class="preset-btn"
              type="button"
            >
              Tight (50 mi)
            </button>
            <button 
              @click="maxDiameterMiles = 75" 
              :class="{ 'active': maxDiameterMiles === 75 }"
              class="preset-btn"
              type="button"
            >
              Medium (75 mi)
            </button>
            <button 
              @click="maxDiameterMiles = 100" 
              :class="{ 'active': maxDiameterMiles === 100 }"
              class="preset-btn"
              type="button"
            >
              Normal (100 mi) ✓
            </button>
            <button 
              @click="maxDiameterMiles = 150" 
              :class="{ 'active': maxDiameterMiles === 150 }"
              class="preset-btn"
              type="button"
            >
              Loose (150 mi)
            </button>
          </div>
          <p class="help-text">
            Controls how geographically spread clusters can be. Tighter clusters create more focused team territories.
            Current setting: <strong>{{ maxDiameterMiles }} miles</strong>
          </p>
        </div>
      </div>

      <!-- 5. State Selection and Geocoding -->
      <div class="control-section">
        <label class="control-label">States</label>
        <p class="help-text" v-if="!excelComplete">Parse Excel data first to see available states</p>
        <p class="help-text" v-else-if="loadingStates">Loading states...</p>
        <p class="help-text" v-else-if="availableStates.length === 0">No states found in parsed data</p>
        
        <!-- Bulk Geocode Button -->
        <div v-if="excelComplete && availableStates.length > 0" class="bulk-actions">
          <button
            @click="handleGeocodeAll"
            class="btn-geocode-all"
            :disabled="geocodingAllStates || geocodingState !== null"
          >
            <span v-if="!geocodingAllStates">🌍 Geocode All States</span>
            <span v-else>
              Geocoding {{ currentGeocodeState }}... ({{ geocodeProgress.current }}/{{ geocodeProgress.total }})
            </span>
          </button>
          <p v-if="geocodingAllStates" class="progress-text">
            This may take several minutes. Please wait...
          </p>
        </div>
        
        <div v-if="excelComplete && availableStates.length > 0" class="state-table-container">
          <table class="state-table">
            <thead>
              <tr>
                <th class="col-select">Select</th>
                <th class="col-state">State</th>
                <th class="col-sites">Sites</th>
                <th class="col-clusters">Clusters</th>
                <th class="col-geocode">Geocode</th>
                <th class="col-cluster">Cluster</th>
                <th class="col-errors">Errors</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="state in availableStates" 
                :key="state.name"
                :class="{ 'selected': stateInput === state.name }"
              >
                <td class="col-select">
                  <input
                    type="radio"
                    :id="`state-${state.name}`"
                    :value="state.name"
                    v-model="stateInput"
                    @change="updateState"
                    name="state-selection"
                  />
                </td>
                <td class="col-state">
                  <label :for="`state-${state.name}`">{{ state.name }}</label>
                </td>
                <td class="col-sites">{{ state.site_count }}</td>
                <td class="col-clusters">{{ state.cluster_count !== null && state.cluster_count !== undefined ? state.cluster_count : '-' }}</td>
                <td class="col-geocode">
                  <button
                    v-if="!state.geocoded"
                    @click="handleGeocode(state.name)"
                    class="btn-geocode"
                    :disabled="geocodingState === state.name"
                  >
                    {{ geocodingState === state.name ? 'Geocoding...' : 'Geocode' }}
                  </button>
                  <span v-else class="status-complete">✓ Complete</span>
                </td>
                <td class="col-cluster">
                  <button
                    v-if="state.geocoded"
                    @click="handleRecluster(state.name)"
                    class="btn-cluster"
                    :disabled="clusteringState === state.name"
                  >
                    {{ clusteringState === state.name ? 'Clustering...' : 'Re-cluster' }}
                  </button>
                  <span v-else>-</span>
                </td>
                <td class="col-errors">
                  <span 
                    v-if="state.geocode_errors > 0" 
                    class="error-count clickable"
                    @click="openErrorModal(state.name)"
                    title="Click to view and fix errors"
                  >
                    {{ state.geocode_errors }}
                  </span>
                  <span v-else-if="state.geocoded" class="no-errors">0</span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <div class="planning-container">
      <!-- Planning Configuration -->
      <div class="config-section">
        <h3>Planning Configuration</h3>
        <PlanningForm @submit="handlePlanSubmit" :is-loading="store.loading" />
      </div>
    </div>
    
    <!-- Loading/Error States -->
    <div v-if="store.loading" class="loading">
      <div class="loading-header">
        <div class="spinner"></div>
        <h3>Planning in progress...</h3>
      </div>
      <div class="loading-details">
        <div class="detail-row">
          <span class="detail-label">Workspace:</span>
          <span class="detail-value">{{ store.workspace }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">State:</span>
          <span class="detail-value">{{ store.stateAbbr }}</span>
        </div>
        <div class="detail-row" v-if="getPlanningStateInfo()">
          <span class="detail-label">Sites:</span>
          <span class="detail-value">{{ getPlanningStateInfo()?.site_count || 'N/A' }}</span>
        </div>
        <div class="detail-row" v-if="getPlanningStateInfo()?.cluster_count">
          <span class="detail-label">Clusters:</span>
          <span class="detail-value">{{ getPlanningStateInfo().cluster_count }}</span>
        </div>
      </div>
      <p class="loading-estimate">This may take 2-3 minutes for large datasets.</p>
    </div>
    
    <div v-if="store.error" class="error">
      <p>Error: {{ store.error }}</p>
    </div>

    <!-- Excel Upload Modal -->
    <ExcelUploadModal
      :is-open="showExcelModal"
      :workspace="store.workspace"
      @close="showExcelModal = false"
      @success="handleExcelSuccess"
    />

    <!-- Planning Error Dialog -->
    <PlanningErrorDialog
      :is-open="showErrorDialog"
      :error="store.error"
      :plan-request="store.planRequest"
      @close="showErrorDialog = false"
    />

    <!-- Geocode Error Modal -->
    <GeocodeErrorModal
      :is-open="showErrorModal"
      :workspace-name="store.workspace"
      :state-name="errorModalState"
      @close="showErrorModal = false"
      @updated="handleErrorsUpdated"
    />

    <!-- Geocode Editor Modal -->
    <GeocodeEditorModal
      :is-open="showEditorModal"
      :workspace-name="store.workspace"
      :state-name="editorModalState"
      @close="showEditorModal = false"
      @updated="handleEditorUpdated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { planningAPI, workspaceAPI, geocodeAPI, clusterAPI } from '../services/api'
import { useRouter } from 'vue-router'
import PlanningForm from '../components/PlanningForm.vue'
import ExcelUploadModal from '../components/ExcelUploadModal.vue'
import PlanningErrorDialog from '../components/PlanningErrorDialog.vue'
import GeocodeErrorModal from '../components/GeocodeErrorModal.vue'
import GeocodeEditorModal from '../components/GeocodeEditorModal.vue'

const store = usePlanningStore()
const router = useRouter()
const stateInput = ref('')

// Geocode error modal state
const showErrorModal = ref(false)
const errorModalState = ref('')

// Geocode editor modal state
const showEditorModal = ref(false)
const editorModalState = ref('')
const availableStates = ref([])
const loadingStates = ref(false)
const excelComplete = ref(false)
const showExcelModal = ref(false)
const showErrorDialog = ref(false)
const geocodingState = ref(null)
const clusteringState = ref(null) // Track which state is currently clustering
const maxDiameterMiles = ref(100) // Default to 100 miles (Normal preset)
const geocodingAllStates = ref(false) // Track if bulk geocoding is in progress
const currentGeocodeState = ref('') // Current state being geocoded in bulk operation
const geocodeProgress = ref({ current: 0, total: 0 }) // Progress tracking for bulk geocode

// Initialize state input from store
onMounted(() => {
  stateInput.value = store.stateAbbr
  // Load states if workspace is already selected
  if (store.workspace) {
    loadStates(store.workspace)
    checkExcelStatus(store.workspace)
  }
})

// Watch for workspace changes to reload available states and check Excel status
watch(() => store.workspace, (newWorkspace) => {
  if (newWorkspace) {
    loadStates(newWorkspace)
    checkExcelStatus(newWorkspace)
  } else {
    availableStates.value = []
    stateInput.value = ''
    excelComplete.value = false
  }
})

async function checkExcelStatus(workspaceName) {
  try {
    // Check if any states exist (which means Excel has been parsed)
    const response = await workspaceAPI.getStates(workspaceName)
    excelComplete.value = response.data.states && response.data.states.length > 0
  } catch (err) {
    console.error('Error checking Excel status:', err)
    excelComplete.value = false
  }
}

async function loadStates(workspaceName) {
  try {
    loadingStates.value = true
    const response = await workspaceAPI.getStates(workspaceName)
    availableStates.value = response.data.states || []
    
    // If current state is not in the list, clear it
    const stateNames = availableStates.value.map(s => s.name)
    if (stateInput.value && !stateNames.includes(stateInput.value)) {
      stateInput.value = ''
      store.setStateAbbr('')
    }
  } catch (err) {
    console.error('Error loading states:', err)
    availableStates.value = []
  } finally {
    loadingStates.value = false
  }
}

async function handleGeocode(stateName) {
  let geocodeSuccess = false
  let geocodeMessage = ''
  
  try {
    geocodingState.value = stateName
    
    // Automatically select this state's radio button
    stateInput.value = stateName
    updateState()
    
    // Call geocode API
    const geocodeResponse = await geocodeAPI.geocode(store.workspace, stateName)
    geocodeSuccess = true
    geocodeMessage = geocodeResponse.data?.message || 'Geocoding completed'
    
  } catch (err) {
    console.error('Error geocoding:', err)
    alert(`Error: ${err.response?.data?.detail || err.message}`)
    geocodingState.value = null
    return
  }
  
  // If geocoding succeeded (even with some errors), run clustering
  if (geocodeSuccess) {
    try {
      // Automatically run clustering after geocoding (it's fast and always useful)
      await clusterAPI.cluster(store.workspace, stateName, maxDiameterMiles.value)
      
      // Refresh state list to update geocode status
      await loadStates(store.workspace)
      
      // Show appropriate message based on whether there were geocoding errors
      if (geocodeMessage.includes('error')) {
        alert(`Geocoding completed with some errors. Clustering completed for successfully geocoded addresses in ${stateName}.\n\nCheck the "Errors" column for details.`)
      } else {
        alert(`Geocoding and clustering completed for ${stateName}!`)
      }
    } catch (clusterErr) {
      console.error('Error clustering:', clusterErr)
      // Refresh state list anyway to show geocoding is complete
      await loadStates(store.workspace)
      alert(`Geocoding completed but clustering failed: ${clusterErr.response?.data?.detail || clusterErr.message}`)
    }
  }
  
  geocodingState.value = null
}

async function handleGeocodeAll() {
  if (!store.workspace) {
    alert('Please select a workspace first')
    return
  }

  // Get all states that need geocoding (not already geocoded)
  const statesToGeocode = availableStates.value.filter(state => !state.geocoded)
  
  if (statesToGeocode.length === 0) {
    alert('All states are already geocoded!')
    return
  }

  const confirmMessage = `This will geocode ${statesToGeocode.length} state(s): ${statesToGeocode.map(s => s.name).join(', ')}.\n\nThis may take several minutes. Continue?`
  if (!confirm(confirmMessage)) {
    return
  }

  geocodingAllStates.value = true
  geocodeProgress.value = { current: 0, total: statesToGeocode.length }
  
  const results = {
    success: [],
    failed: [],
    withErrors: []
  }

  for (let i = 0; i < statesToGeocode.length; i++) {
    const state = statesToGeocode[i]
    currentGeocodeState.value = state.name
    geocodeProgress.value.current = i + 1

    try {
      // Geocode the state
      const geocodeResponse = await geocodeAPI.geocode(store.workspace, state.name)
      const geocodeMessage = geocodeResponse.data?.message || 'Geocoding completed'
      
      // Automatically run clustering after geocoding
      try {
        await clusterAPI.cluster(store.workspace, state.name, maxDiameterMiles.value)
        
        if (geocodeMessage.includes('error')) {
          results.withErrors.push(state.name)
        } else {
          results.success.push(state.name)
        }
      } catch (clusterErr) {
        console.error(`Error clustering ${state.name}:`, clusterErr)
        results.withErrors.push(state.name)
      }
    } catch (err) {
      console.error(`Error geocoding ${state.name}:`, err)
      results.failed.push(state.name)
    }
  }

  // Refresh state list to show updated status
  await loadStates(store.workspace)
  
  // Reset bulk geocoding state
  geocodingAllStates.value = false
  currentGeocodeState.value = ''
  geocodeProgress.value = { current: 0, total: 0 }

  // Show summary message
  let summaryMessage = 'Bulk Geocoding Complete!\n\n'
  if (results.success.length > 0) {
    summaryMessage += `✓ Successfully geocoded and clustered: ${results.success.join(', ')}\n\n`
  }
  if (results.withErrors.length > 0) {
    summaryMessage += `⚠ Geocoded with some errors: ${results.withErrors.join(', ')}\n(Check the Errors column for details)\n\n`
  }
  if (results.failed.length > 0) {
    summaryMessage += `✗ Failed to geocode: ${results.failed.join(', ')}\n\n`
  }
  
  alert(summaryMessage)
}

async function handleRecluster(stateName) {
  if (!store.workspace) {
    alert('Please select a workspace first')
    return
  }

  clusteringState.value = stateName

  try {
    // Run clustering with the current maxDiameterMiles setting
    await clusterAPI.cluster(store.workspace, stateName, maxDiameterMiles.value)
    
    // Refresh state list to update cluster count
    await loadStates(store.workspace)
    
    alert(`Re-clustering completed for ${stateName}! Created clusters with max diameter of ${maxDiameterMiles.value} miles.`)
  } catch (err) {
    console.error('Error clustering:', err)
    alert(`Error: ${err.response?.data?.detail || err.message}`)
  }
  
  clusteringState.value = null
}

function getStatePlaceholder() {
  if (!excelComplete.value) {
    return '-- Parse Excel first --'
  }
  if (loadingStates.value) {
    return 'Loading states...'
  }
  if (availableStates.value.length === 0) {
    return '-- No states available --'
  }
  return '-- Select a state --'
}

function getExcelHelpText() {
  if (!store.workspace) {
    return 'Select a workspace first'
  }
  if (excelComplete.value) {
    return 'Excel data has been parsed. Click to upload new data.'
  }
  return 'Upload and parse an Excel file to continue'
}

function getStateHelpText() {
  if (!excelComplete.value) {
    return 'Parse Excel data first to see available states'
  }
  if (availableStates.value.length === 0) {
    return 'No states found in parsed data'
  }
  return 'Select the state you want to plan routes for'
}

function handleExcelUpdate() {
  console.log('Excel button clicked, opening modal...')
  console.log('Current showExcelModal value:', showExcelModal.value)
  console.log('Current workspace:', store.workspace)
  // Show the Excel upload modal
  showExcelModal.value = true
  console.log('After setting, showExcelModal value:', showExcelModal.value)
}

async function handleExcelSuccess() {
  // Refresh the Excel status and state list after successful upload
  if (store.workspace) {
    await checkExcelStatus(store.workspace)
    await loadStates(store.workspace)
  }
}

function updateState() {
  if (stateInput.value.trim()) {
    store.setStateAbbr(stateInput.value.trim())
  }
}

function openErrorModal(stateName) {
  errorModalState.value = stateName
  showErrorModal.value = true
}

async function handleErrorsUpdated() {
  // Refresh the state list to update error counts
  if (store.workspace) {
    await loadStates(store.workspace)
  }
}

function getPlanningStateInfo() {
  // Get the state info for the currently selected state
  if (!store.stateAbbr) return null
  return availableStates.value.find(s => s.name === store.stateAbbr)
}

function openEditorModal() {
  // Use the currently selected state, or first available state
  const state = store.stateAbbr || (availableStates.value.length > 0 ? availableStates.value[0].name : '')
  if (state) {
    editorModalState.value = state
    showEditorModal.value = true
  }
}

async function handleEditorUpdated() {
  // Refresh the state list after editing a site
  // This ensures any changes are reflected in the UI
  if (store.workspace) {
    await loadStates(store.workspace)
  }
}

async function handlePlanSubmit() {
  try {
    console.log('handlePlanSubmit: Starting plan submission')
    
    // Validate that a state is selected
    if (!store.stateAbbr || store.stateAbbr.trim() === '') {
      store.setError('Please select a state from the table above before planning routes.')
      return
    }
    
    console.log('handlePlanSubmit: Setting loading to true')
    store.setLoading(true)
    store.setError(null)
    
    console.log('handlePlanSubmit: Calling planningAPI.plan')
    const response = await planningAPI.plan(store.planRequest)
    console.log('handlePlanSubmit: Plan API response received', response.data)
    
    store.setPlanResult(response.data)
    console.log('handlePlanSubmit: Plan result stored, navigating to routes')
    
    // Navigate to routes page
    await router.push('/routes')
    console.log('handlePlanSubmit: Navigation complete')
  } catch (err) {
    console.error('handlePlanSubmit: Error occurred', err)
    const errorMessage = err.response?.data?.detail || err.message
    store.setError(errorMessage)
    // Show error dialog for planning failures
    showErrorDialog.value = true
  } finally {
    console.log('handlePlanSubmit: Setting loading to false')
    store.setLoading(false)
  }
}
</script>

<style scoped>
.planning {
  max-width: 1000px;
  margin: 0 auto;
}

h2 {
  color: #1e3a8a;
  margin-bottom: 1rem;
}

.workflow-controls {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.control-section {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.control-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.control-label {
  display: block;
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.workspace-display {
  padding: 0.75rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  color: #1e3a8a;
  font-weight: 500;
  font-size: 1rem;
}

.excel-button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.excel-button:hover:not(:disabled) {
  border-color: #1e3a8a;
  background: #f9fafb;
}

.excel-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.excel-button.complete {
  border-color: #10b981;
  background: #f0fdf4;
}

.excel-button.incomplete {
  border-color: #f59e0b;
  background: #fffbeb;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.9rem;
}

.excel-button.complete .status-icon {
  background: #10b981;
  color: white;
}

.excel-button.incomplete .status-icon {
  background: #fef3c7;
  color: #92400e;
}

.btn-editor {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-editor:hover:not(:disabled) {
  border-color: #1e3a8a;
  background: #eff6ff;
  color: #1e3a8a;
}

.btn-editor:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-editor .icon {
  font-size: 1.2rem;
}

.button-text {
  flex: 1;
  text-align: left;
  font-weight: 500;
  color: #374151;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.complete {
  background: #10b981;
  color: white;
}

.status-badge.incomplete {
  background: #f59e0b;
  color: white;
}

.help-text {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #6b7280;
}

/* Bulk Actions */
.bulk-actions {
  margin-top: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f0f9ff;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  text-align: center;
}

.btn-geocode-all {
  padding: 0.75rem 1.5rem;
  background-color: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 250px;
}

.btn-geocode-all:hover:not(:disabled) {
  background-color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
}

.btn-geocode-all:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.progress-text {
  margin: 0.75rem 0 0 0;
  font-size: 0.9rem;
  color: #1e40af;
  font-weight: 500;
  font-style: italic;
}

.state-table-container {
  margin-top: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.state-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.state-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.state-table th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.state-table tbody tr {
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s;
}

.state-table tbody tr:last-child {
  border-bottom: none;
}

.state-table tbody tr:hover {
  background-color: #f9fafb;
}

.state-table tbody tr.selected {
  background-color: #eff6ff;
}

.state-table td {
  padding: 0.75rem;
}

.col-select {
  width: 60px;
  text-align: center;
}

.col-select input[type="radio"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.col-state {
  font-weight: 500;
  color: #1f2937;
}

.col-state label {
  cursor: pointer;
  display: block;
  margin: 0;
}

.col-sites {
  width: 100px;
  text-align: center;
  color: #6b7280;
  font-weight: 500;
}

.col-clusters {
  width: 100px;
  text-align: center;
  color: #6b7280;
  font-weight: 500;
}

.col-geocode {
  width: 140px;
  text-align: center;
}

.col-cluster {
  width: 140px;
  text-align: center;
}

.col-errors {
  width: 80px;
  text-align: center;
  color: #6b7280;
  font-weight: 500;
}

.error-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem 0.5rem;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.85rem;
}

.error-count.clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.error-count.clickable:hover {
  background: #fecaca;
  transform: scale(1.05);
}

.no-errors {
  color: #10b981;
  font-weight: 600;
  font-size: 0.9rem;
}

.btn-geocode {
  padding: 0.375rem 0.75rem;
  background-color: #1e3a8a;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-geocode:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn-geocode:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cluster {
  padding: 0.375rem 0.75rem;
  background-color: #059669;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-cluster:hover:not(:disabled) {
  background-color: #047857;
}

.btn-cluster:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-complete {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: #10b981;
  font-weight: 600;
  font-size: 0.9rem;
}

.planning-container {
  margin-top: 2rem;
}

.config-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.config-section h3 {
  margin-top: 0;
  color: #1e3a8a;
}

.loading {
  margin-top: 2rem;
  padding: 2rem;
  background: #dbeafe;
  border-radius: 8px;
  border: 2px solid #3b82f6;
}

.loading-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.loading-header h3 {
  margin: 0;
  color: #1e40af;
  font-size: 1.25rem;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 4px solid #bfdbfe;
  border-top-color: #1e40af;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-details {
  background: white;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: #374151;
}

.detail-value {
  color: #1e40af;
  font-weight: 500;
}

.loading-estimate {
  margin: 0;
  color: #1e40af;
  font-size: 0.9rem;
  font-style: italic;
}

.error {
  margin-top: 2rem;
  padding: 1rem;
  background: #fee2e2;
  border-radius: 6px;
  color: #991b1b;
}

/* Clustering Settings Styles */
.cluster-settings {
  margin-top: 0.5rem;
}

.setting-label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.preset-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.preset-btn {
  flex: 1;
  min-width: 120px;
  padding: 0.625rem 1rem;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-btn:hover {
  border-color: #1e3a8a;
  background: #f9fafb;
}

.preset-btn.active {
  border-color: #1e3a8a;
  background: #dbeafe;
  color: #1e3a8a;
  font-weight: 600;
}

@media (max-width: 768px) {
  .planning-container {
    grid-template-columns: 1fr;
  }
}
</style>
