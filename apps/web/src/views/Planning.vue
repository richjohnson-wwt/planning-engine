<template>
  <div class="planning">
    <h2>Route Planning</h2>
    
    <!-- Workspace and State Selection -->
    <div class="selection-bar">
      <div class="selection-item">
        <label>Workspace:</label>
        <span class="value">{{ store.workspace || 'Not selected' }}</span>
      </div>
      <div class="selection-item">
        <label for="state-select">State:</label>
        <input
          id="state-select"
          v-model="stateInput"
          type="text"
          placeholder="e.g., TX, Texas, LA, Louisiana"
          class="state-input"
          @blur="updateState"
        />
      </div>
    </div>
    
    <div class="planning-container">
      <!-- Workflow Steps -->
      <div class="workflow-section">
        <h3>Workflow Steps</h3>
        <WorkflowSteps />
      </div>
      
      <!-- Planning Configuration -->
      <div class="config-section">
        <h3>Planning Configuration</h3>
        <PlanningForm @submit="handlePlanSubmit" />
      </div>
    </div>
    
    <!-- Loading/Error States -->
    <div v-if="store.loading" class="loading">
      <p>Planning in progress...</p>
    </div>
    
    <div v-if="store.error" class="error">
      <p>Error: {{ store.error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlanningStore } from '../stores/planning'
import { planningAPI } from '../services/api'
import { useRouter } from 'vue-router'
import WorkflowSteps from '../components/WorkflowSteps.vue'
import PlanningForm from '../components/PlanningForm.vue'

const store = usePlanningStore()
const router = useRouter()
const stateInput = ref('')

// Initialize state input from store
onMounted(() => {
  stateInput.value = store.stateAbbr
})

function updateState() {
  if (stateInput.value.trim()) {
    store.setStateAbbr(stateInput.value.trim())
  }
}

async function handlePlanSubmit() {
  try {
    store.setLoading(true)
    store.setError(null)
    
    const response = await planningAPI.plan(store.planRequest)
    store.setPlanResult(response.data)
    
    // Navigate to results page
    router.push('/results')
  } catch (err) {
    store.setError(err.response?.data?.detail || err.message)
  } finally {
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

.selection-bar {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
  align-items: center;
}

.selection-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.selection-item label {
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.selection-item .value {
  color: #1e3a8a;
  font-weight: 500;
}

.state-input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
  min-width: 200px;
}

.state-input:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

.planning-container {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
}

.workflow-section,
.config-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.workflow-section h3,
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
