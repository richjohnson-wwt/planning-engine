<template>
  <div class="route-map">
    <div v-if="!result || !result.team_days || result.team_days.length === 0" class="no-map">
      <p>No route data available to display on map.</p>
    </div>
    
    <div v-else-if="!mapUrl" class="map-container">
      <div class="map-placeholder">
        <p>🗺️ Map Visualization</p>
        <p class="small">
          No map file found. The map is generated automatically when you run a plan.
        </p>
      </div>
    </div>
    
    <div v-else class="map-container">
      <div class="map-controls">
        <span class="map-label">📍 Interactive Route Map</span>
        <a :href="mapUrl" target="_blank" class="btn-open-new">Open in New Tab ↗</a>
      </div>
      
      <!-- Embedded interactive map -->
      <iframe :src="mapUrl" class="map-iframe" title="Route Map"></iframe>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  result: {
    type: Object,
    required: true
  },
  mapUrl: {
    type: String,
    default: null
  }
})
</script>

<style scoped>
.route-map {
  min-height: 400px;
}

.no-map {
  padding: 2rem;
  text-align: center;
  background: #f9fafb;
  border-radius: 6px;
  color: #6b7280;
}

.map-container {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.map-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
}

.map-label {
  font-weight: 500;
  color: #1e3a8a;
  font-size: 0.95rem;
}

.btn-open-new {
  padding: 0.5rem 1rem;
  background: #1e3a8a;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-open-new:hover {
  background: #1e40af;
}

.map-placeholder {
  padding: 3rem;
  background: #f9fafb;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  text-align: center;
}

.map-placeholder p {
  margin: 0.5rem 0;
  color: #6b7280;
}

.map-placeholder p:first-child {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.small {
  font-size: 0.9rem;
}

.map-iframe {
  width: 100%;
  height: 600px;
  border: 1px solid #e5e7eb;
  border-radius: 0 0 6px 6px;
  border-top: none;
}
</style>
