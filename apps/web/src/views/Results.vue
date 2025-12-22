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
      
      <!-- Export Options -->
      <div class="export-section">
        <button @click="exportJSON" class="btn btn-secondary">
          Export JSON
        </button>
        <button @click="downloadMap" class="btn btn-secondary">
          Download Map
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePlanningStore } from '../stores/planning'
import RouteMap from '../components/RouteMap.vue'
import TeamSchedule from '../components/TeamSchedule.vue'

const store = usePlanningStore()

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

function downloadMap() {
  // Note: Map HTML file is generated server-side
  // This would need to fetch the map file from the server
  alert('Map download functionality - to be implemented with server-side map file access')
}
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
</style>
