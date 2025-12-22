<template>
  <div class="route-map">
    <div v-if="!result || !result.team_days || result.team_days.length === 0" class="no-map">
      <p>No route data available to display on map.</p>
    </div>
    
    <div v-else class="map-container">
      <p class="map-note">
        <strong>Note:</strong> Interactive map is auto-generated server-side as 
        <code>route_map_{timestamp}.html</code> in the workspace output folder.
      </p>
      
      <!-- Placeholder for map iframe or integration -->
      <div class="map-placeholder">
        <p>🗺️ Map Visualization</p>
        <p class="small">
          The Folium map is generated automatically and saved alongside the JSON results.
          To view: Open the <code>route_map_*.html</code> file from your workspace output folder.
        </p>
      </div>
      
      <!-- Future: Could embed the map here via iframe if served statically -->
      <!-- <iframe v-if="mapUrl" :src="mapUrl" class="map-iframe"></iframe> -->
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: {
    type: Object,
    required: true
  }
})

// Future enhancement: Add mapUrl prop to load the generated HTML map
// const mapUrl = computed(() => {
//   // Construct URL to the generated map file
//   return `/maps/${workspace}/${state}/route_map_${timestamp}.html`
// })
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
  gap: 1rem;
}

.map-note {
  padding: 1rem;
  background: #dbeafe;
  border-left: 4px solid #1e3a8a;
  border-radius: 4px;
  margin: 0;
}

.map-note code {
  background: rgba(0,0,0,0.1);
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
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

/* Future: For iframe embedding */
.map-iframe {
  width: 100%;
  height: 600px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}
</style>
