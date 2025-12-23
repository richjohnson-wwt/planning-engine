<template>
  <div class="results">
    <h2>Planning Results</h2>
    
    <div v-if="!store.planResult" class="no-results">
      <p>No planning results available. Please run a plan first.</p>
      <router-link to="/planning" class="btn btn-primary">
        Go to Planning
      </router-link>
    </div>
    
    <div v-else class="results-container">
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
        <RouteMap :result="store.planResult" />
      </div>
      
      <!-- Team Schedule -->
      <div class="schedule-section">
        <h3>Team Schedule</h3>
        <TeamSchedule :teamDays="store.planResult.team_days" />
      </div>
      
      <!-- Output Files Section -->
      <div v-if="store.selectedWorkspace && store.selectedState" class="output-files-section">
        <h3>Generated Files</h3>
        <div v-if="loadingFiles" class="loading">Loading files...</div>
        <div v-else-if="outputFiles.length > 0" class="files-list">
          <div v-for="file in outputFiles" :key="file.filename" class="file-item">
            <div class="file-info">
              <span class="file-icon">{{ file.type === 'map' ? '🗺️' : '📄' }}</span>
              <div class="file-details">
                <a :href="file.url" target="_blank" class="file-link">
                  {{ file.filename }}
                </a>
                <span class="file-meta">
                  {{ formatFileSize(file.size) }} • {{ formatTimestamp(file.modified) }}
                </span>
              </div>
            </div>
            <a :href="file.url" target="_blank" class="btn btn-sm btn-primary">
              {{ file.type === 'map' ? 'View Map' : 'Download' }}
            </a>
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
import { outputAPI } from '../services/api'
import RouteMap from '../components/RouteMap.vue'
import TeamSchedule from '../components/TeamSchedule.vue'

const store = usePlanningStore()
const outputFiles = ref([])
const loadingFiles = ref(false)

const totalSites = computed(() => {
  if (!store.planResult?.team_days) return 0
  return store.planResult.team_days.reduce((sum, td) => sum + (td.site_ids?.length || 0), 0)
})

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString()
}

function exportJSON() {
  const dataStr = JSON.stringify(store.planResult, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `route_plan_${new Date().toISOString().split('T')[0]}.json`
  link.click()
  URL.revokeObjectURL(url)
}

async function fetchOutputFiles() {
  if (!store.selectedWorkspace || !store.selectedState) return
  
  loadingFiles.value = true
  try {
    const response = await outputAPI.listFiles(store.selectedWorkspace, store.selectedState)
    outputFiles.value = response.data.files || []
  } catch (error) {
    console.error('Error fetching output files:', error)
    outputFiles.value = []
  } finally {
    loadingFiles.value = false
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

// Fetch output files when component mounts or when workspace/state changes
onMounted(() => {
  fetchOutputFiles()
})

watch([() => store.selectedWorkspace, () => store.selectedState], () => {
  fetchOutputFiles()
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
.results {
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  color: #1e3a8a;
  margin-bottom: 2rem;
}

.no-results {
  text-align: center;
  padding: 3rem;
  background: #f9fafb;
  border-radius: 8px;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
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
.schedule-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.map-section h3,
.schedule-section h3 {
  margin-top: 0;
  color: #1e3a8a;
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
