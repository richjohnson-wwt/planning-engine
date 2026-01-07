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

      <!-- 3. State Selection Table -->
      <div class="control-section">
        <label class="control-label">States</label>
        <p class="help-text" v-if="!excelComplete">Parse Excel data first to see available states</p>
        <p class="help-text" v-else-if="loadingStates">Loading states...</p>
        <p class="help-text" v-else-if="availableStates.length === 0">No states found in parsed data</p>
        
        <div v-if="excelComplete && availableStates.length > 0" class="state-table-container">
          <table class="state-table">
            <thead>
              <tr>
                <th class="col-select">Select</th>
                <th class="col-state">State</th>
                <th class="col-sites">Sites</th>
                <th class="col-clusters">Clusters</th>
                <th class="col-geocode">Geocode</th>
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
                <td class="col-errors">
                  <span v-if="state.geocode_errors > 0" class="error-count">{{ state.geocode_errors }}</span>
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
      <p>Planning in progress...</p>
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

const store = usePlanningStore()
const router = useRouter()
const stateInput = ref('')
const availableStates = ref([])
const loadingStates = ref(false)
const excelComplete = ref(false)
const showExcelModal = ref(false)
const showErrorDialog = ref(false)
const geocodingState = ref(null)

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
      await clusterAPI.cluster(store.workspace, stateName)
      
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
  background: #f59e0b;
  color: white;
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
  padding: 1rem;
  background: #dbeafe;
  border-radius: 6px;
  text-align: center;
  color: #1e40af;
}

.error {
  margin-top: 2rem;
  padding: 1rem;
  background: #fee2e2;
  border-radius: 6px;
  color: #991b1b;
}

@media (max-width: 768px) {
  .planning-container {
    grid-template-columns: 1fr;
  }
}
</style>
