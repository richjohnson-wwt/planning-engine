<template>
  <div class="workflow-steps">
    <div class="step" :class="{ completed: step.completed }" v-for="step in steps" :key="step.id">
      <div class="step-number">{{ step.number }}</div>
      <div class="step-content">
        <h4>{{ step.title }}</h4>
        <p>{{ step.description }}</p>
        <button v-if="step.action" @click="step.action" class="btn-small">
          {{ step.actionLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { excelAPI, geocodeAPI, clusterAPI } from '../services/api'

const store = usePlanningStore()

const steps = ref([
  {
    id: 1,
    number: 1,
    title: 'Geocode & Cluster',
    description: 'Convert addresses to GPS coordinates and group sites geographically (runs automatically)',
    completed: false,
    actionLabel: 'Process',
    action: async () => {
      try {
        await geocodeAPI.geocode(store.workspace, store.stateAbbr)
        await clusterAPI.cluster(store.workspace, store.stateAbbr)
        steps.value[0].completed = true
        alert('Geocoding and clustering completed!')
      } catch (err) {
        alert(`Error: ${err.response?.data?.detail || err.message}`)
      }
    }
  }
])
</script>

<style scoped>
.workflow-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.step {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #d1d5db;
  transition: all 0.2s;
}

.step.completed {
  border-left-color: #10b981;
  background: #f0fdf4;
}

.step-number {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e5e7eb;
  border-radius: 50%;
  font-weight: bold;
  color: #6b7280;
}

.step.completed .step-number {
  background: #10b981;
  color: white;
}

.step-content {
  flex: 1;
}

.step-content h4 {
  margin: 0 0 0.25rem 0;
  color: #1f2937;
  font-size: 0.95rem;
}

.step-content p {
  margin: 0 0 0.5rem 0;
  color: #6b7280;
  font-size: 0.85rem;
}

.btn-small {
  padding: 0.375rem 0.75rem;
  font-size: 0.85rem;
  background: #1e3a8a;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-small:hover {
  background: #1e40af;
}
</style>
