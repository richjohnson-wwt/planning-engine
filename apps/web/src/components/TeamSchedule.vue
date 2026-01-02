<template>
  <div class="team-schedule">
    <div v-if="!teamDays || teamDays.length === 0" class="no-schedule">
      <p>No team schedule data available.</p>
    </div>
    
    <div v-else class="schedule-table">
      <table>
        <thead>
          <tr>
            <th>Team ID</th>
            <th>Date</th>
            <th>Sites</th>
            <th>Service Time</th>
            <th>Total Route Time</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(td, index) in teamDays" :key="index">
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
import { ref } from 'vue'

const props = defineProps({
  teamDays: {
    type: Array,
    required: true
  }
})

const selectedTeamDay = ref(null)

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
