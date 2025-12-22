<template>
  <div id="app">
    <header class="app-header">
      <div class="container">
        <h1>Route Planning Engine</h1>
        <nav>
          <router-link to="/">Home</router-link>
          <router-link to="/planning">Planning</router-link>
          <router-link to="/results">Results</router-link>
        </nav>
      </div>
    </header>
    
    <main class="app-main">
      <div class="container">
        <router-view />
      </div>
    </main>
    
    <footer class="app-footer">
      <div class="container">
        <p>&copy; 2025 Route Planning Engine</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
// Main app component
// WWT IT Team: Replace with @wwt/atc-ui-components layout components
</script>

<style scoped>
.app-header {
  background-color: #1e3a8a;
  color: white;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.app-header nav {
  margin-top: 0.5rem;
}

.app-header nav a {
  color: white;
  text-decoration: none;
  margin-right: 1.5rem;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.app-header nav a:hover,
.app-header nav a.router-link-active {
  background-color: rgba(255,255,255,0.1);
}

.app-main {
  min-height: calc(100vh - 200px);
  padding: 2rem 0;
}

.app-footer {
  background-color: #f3f4f6;
  padding: 1rem 0;
  text-align: center;
  color: #6b7280;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}
</style>
