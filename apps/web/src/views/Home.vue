<template>
  <div class="home">
    <h2>Welcome to Route Planning Engine</h2>
    
    <div class="workflow-steps">
      <div class="step">
        <h3>1. Create Workspace</h3>
        <p>Set up a workspace to organize your planning data</p>
      </div>
      
      <div class="step">
        <h3>2. Upload Sites</h3>
        <p>Import site addresses from Excel file</p>
      </div>
      
      <div class="step">
        <h3>3. Geocode</h3>
        <p>Convert addresses to GPS coordinates</p>
      </div>
      
      <div class="step">
        <h3>4. Plan Routes</h3>
        <p>Generate optimized routes for your teams</p>
      </div>
    </div>
    
    <div class="quick-start">
      <h3>Quick Start</h3>
      <WorkspaceSelector />
      <router-link to="/planning" class="btn btn-primary">
        Start Planning
      </router-link>
    </div>
  </div>
</template>

<script setup>
import WorkspaceSelector from '../components/WorkspaceSelector.vue'
</script>

<style scoped>
.home {
  max-width: 900px;
  margin: 0 auto;
}

h2 {
  color: #1e3a8a;
  margin-bottom: 2rem;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.step {
  background: #f9fafb;
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid #1e3a8a;
}

.step h3 {
  color: #1e3a8a;
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.step p {
  color: #6b7280;
  margin: 0;
  font-size: 0.9rem;
}

.quick-start {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.quick-start h3 {
  margin-top: 0;
  color: #1e3a8a;
}

.btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
  margin-top: 1rem;
}

.btn-primary {
  background-color: #1e3a8a;
  color: white;
}

.btn-primary:hover {
  background-color: #1e40af;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
</style>
