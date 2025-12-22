<template>
  <div class="planning-form">
    <form @submit.prevent="handleSubmit">
      <!-- Team Configuration -->
      <div class="form-section">
        <h4>Team Configuration</h4>
        
        <div class="form-group">
          <label for="teams">Number of Teams</label>
          <input
            id="teams"
            v-model.number="formData.team_config.teams"
            type="number"
            min="1"
            class="form-control"
          />
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label for="workday-start">Workday Start</label>
            <input
              id="workday-start"
              v-model="formData.team_config.workday.start"
              type="time"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label for="workday-end">Workday End</label>
            <input
              id="workday-end"
              v-model="formData.team_config.workday.end"
              type="time"
              class="form-control"
            />
          </div>
        </div>
      </div>
      
      <!-- Date Configuration -->
      <div class="form-section">
        <h4>Planning Dates</h4>
        
        <div class="form-group">
          <label>
            <input type="radio" v-model="planningMode" value="fixed-crew" />
            Fixed Crew Mode (calculate end date)
          </label>
        </div>
        
        <div class="form-group">
          <label>
            <input type="radio" v-model="planningMode" value="fixed-calendar" />
            Fixed Calendar Mode (calculate crews needed)
          </label>
        </div>
        
        <div class="form-group">
          <label for="start-date">Start Date</label>
          <input
            id="start-date"
            v-model="formData.start_date"
            type="date"
            class="form-control"
          />
        </div>
        
        <div v-if="planningMode === 'fixed-calendar'" class="form-group">
          <label for="end-date">End Date</label>
          <input
            id="end-date"
            v-model="formData.end_date"
            type="date"
            class="form-control"
          />
        </div>
      </div>
      
      <!-- Route Configuration -->
      <div class="form-section">
        <h4>Route Configuration</h4>
        
        <div class="form-group">
          <label for="max-route">Max Route Minutes</label>
          <input
            id="max-route"
            v-model.number="formData.max_route_minutes"
            type="number"
            min="60"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label for="service-time">Service Minutes per Site</label>
          <input
            id="service-time"
            v-model.number="formData.service_minutes_per_site"
            type="number"
            min="1"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label for="break-time">Break Minutes</label>
          <input
            id="break-time"
            v-model.number="formData.break_minutes"
            type="number"
            min="0"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="formData.use_clusters" />
            Use Clustering
          </label>
        </div>
        
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="formData.fast_mode" />
            Fast Mode
          </label>
        </div>
      </div>
      
      <button type="submit" class="btn btn-primary btn-large">
        Generate Plan
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { usePlanningStore } from '../stores/planning'

const emit = defineEmits(['submit'])
const store = usePlanningStore()

const planningMode = ref('fixed-crew')
const formData = ref({ ...store.planRequest })

// Watch planning mode to clear end_date when switching to fixed-crew
watch(planningMode, (newMode) => {
  if (newMode === 'fixed-crew') {
    formData.value.end_date = null
  }
})

// Watch store for workspace and state changes
watch(() => store.workspace, (newWorkspace) => {
  formData.value.workspace = newWorkspace
})

watch(() => store.stateAbbr, (newState) => {
  formData.value.state_abbr = newState
})

function handleSubmit() {
  // Ensure latest workspace and state from store
  formData.value.workspace = store.workspace
  formData.value.state_abbr = store.stateAbbr
  
  // Update store with form data
  store.updatePlanRequest(formData.value)
  emit('submit')
}
</script>

<style scoped>
.planning-form {
  max-width: 600px;
}

.form-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.form-section:last-of-type {
  border-bottom: none;
}

.form-section h4 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

input[type="checkbox"],
input[type="radio"] {
  margin-right: 0.5rem;
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
}

.btn-primary:hover {
  background-color: #1e40af;
}

.btn-large {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
}
</style>
