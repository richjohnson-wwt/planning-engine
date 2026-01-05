<template>
  <div class="team-schedule">
    <div v-if="!teamDays || teamDays.length === 0" class="no-schedule">
      <p>No team schedule data available.</p>
    </div>
    
    <div v-else class="schedule-table">
      <!-- Cluster Summary (if clustering is used) -->
      <div v-if="clusterSummary" class="cluster-summary">
        <h4>📊 Cluster Summary</h4>
        <p class="summary-text">
          <strong>{{ clusterSummary.clusterCount }} clusters</strong> require 
          <strong>max {{ clusterSummary.maxCrews }} crews</strong> to work in parallel
        </p>
        <div class="cluster-details">
          <span v-for="cluster in clusterSummary.clusters" :key="cluster.id" class="cluster-badge">
            Cluster {{ cluster.id }}: {{ cluster.crews }} crew{{ cluster.crews > 1 ? 's' : '' }}
          </span>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th v-if="hasClusters">Cluster</th>
            <th>Team ID</th>
            <th>Date</th>
            <th>Sites</th>
            <th>Service Time</th>
            <th>Total Route Time</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(td, index) in teamDays" :key="index">
            <td v-if="hasClusters" class="cluster-id">{{ td.cluster_id !== null && td.cluster_id !== undefined ? td.cluster_id : '-' }}</td>
            <td class="team-id">Team {{ td.team_id }}</td>
            <td>{{ formatDate(td.date) }}</td>
            <td>{{ td.site_ids?.length || 0 }} sites</td>
            <td>{{ td.service_minutes }} min</td>
            <td>{{ td.route_minutes }} min</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Site Details (expandable) -->
      <div v-if="selectedTeamDay" class="site-details">
        <h4>Site Details</h4>
        <div v-if="selectedTeamDay.sites && selectedTeamDay.sites.length > 0" class="sites-list">
          <div v-for="(site, idx) in selectedTeamDay.sites" :key="idx" class="site-item">
            <span class="site-number">{{ idx + 1 }}</span>
            <div class="site-info">
              <strong>{{ site.name }}</strong>
              <p v-if="site.address">{{ site.address }}</p>
              <p class="coords">{{ site.lat }}, {{ site.lon }}</p>
            </div>
          </div>
        </div>
        <p v-else class="no-details">No site details available</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  teamDays: {
    type: Array,
    required: true
  }
})

const selectedTeamDay = ref(null)

// Check if any team-day has cluster information
const hasClusters = computed(() => {
  return props.teamDays.some(td => td.cluster_id !== null && td.cluster_id !== undefined)
})

// Calculate cluster summary
const clusterSummary = computed(() => {
  if (!hasClusters.value) return null
  
  // Group team-days by cluster
  const clusterMap = new Map()
  
  props.teamDays.forEach(td => {
    const clusterId = td.cluster_id
    if (clusterId === null || clusterId === undefined) return
    
    if (!clusterMap.has(clusterId)) {
      clusterMap.set(clusterId, new Set())
    }
    clusterMap.get(clusterId).add(td.team_id)
  })
  
  // Calculate crews per cluster
  const clusters = Array.from(clusterMap.entries()).map(([id, teamIds]) => ({
    id,
    crews: teamIds.size
  })).sort((a, b) => a.id - b.id)
  
  // Sum the crews needed across all clusters for parallel work
  const totalCrews = clusters.reduce((sum, c) => sum + c.crews, 0)
  
  return {
    clusterCount: clusters.length,
    maxCrews: totalCrews,
    clusters
  }
})

function formatDate(dateStr) {
  if (!dateStr) return 'Not scheduled'
  // Parse date string directly to avoid timezone conversion issues
  // Date strings from backend are in YYYY-MM-DD format
  const [year, month, day] = dateStr.split('-').map(Number)
  const date = new Date(year, month - 1, day) // month is 0-indexed
  return date.toLocaleDateString()
}

function selectTeamDay(td) {
  selectedTeamDay.value = td
}
</script>

<style scoped>
.team-schedule {
  overflow-x: auto;
}

.no-schedule {
  padding: 2rem;
  text-align: center;
  background: #f9fafb;
  border-radius: 6px;
  color: #6b7280;
}

.schedule-table {
  width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

thead {
  background: #f9fafb;
}

th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
}

td {
  padding: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  color: #6b7280;
}

tr:hover {
  background: #f9fafb;
  cursor: pointer;
}

.team-id {
  font-weight: 600;
  color: #1e3a8a;
}

.cluster-id {
  font-weight: 600;
  color: #059669;
  text-align: center;
}

.cluster-summary {
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #0284c7;
  border-radius: 8px;
}

.cluster-summary h4 {
  margin: 0 0 0.75rem 0;
  color: #0c4a6e;
  font-size: 1.1rem;
}

.summary-text {
  margin: 0 0 1rem 0;
  color: #0c4a6e;
  font-size: 1rem;
  line-height: 1.5;
}

.summary-text strong {
  color: #0369a1;
  font-weight: 700;
}

.cluster-details {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.cluster-badge {
  display: inline-block;
  padding: 0.4rem 0.75rem;
  background: white;
  border: 1px solid #0284c7;
  border-radius: 6px;
  color: #0c4a6e;
  font-size: 0.85rem;
  font-weight: 500;
}

.site-details {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 6px;
}

.site-details h4 {
  margin: 0 0 1rem 0;
  color: #1e3a8a;
}

.sites-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.site-item {
  display: flex;
  gap: 1rem;
  padding: 0.75rem;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #1e3a8a;
}

.site-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e3a8a;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.85rem;
}

.site-info {
  flex: 1;
}

.site-info strong {
  display: block;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.site-info p {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.coords {
  font-family: monospace;
  font-size: 0.8rem;
}

.no-details {
  color: #6b7280;
  text-align: center;
  padding: 1rem;
}
</style>
