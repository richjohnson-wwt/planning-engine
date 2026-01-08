<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Edit Geocoded Site</h3>
        <button class="close-button" @click="closeModal">✕</button>
      </div>
      
      <div class="modal-body">
        <!-- Search Section -->
        <div v-if="!siteData" class="search-section">
          <p class="help-text">
            Enter a Site ID to load and edit its geocoded data.
          </p>
          
          <div class="search-form">
            <div class="form-group">
              <label for="site-id-input">Site ID</label>
              <input
                id="site-id-input"
                v-model="searchSiteId"
                type="text"
                placeholder="e.g., F471"
                @keyup.enter="loadSite"
                :disabled="loading"
              />
            </div>
            
            <button 
              class="btn-search"
              @click="loadSite"
              :disabled="!searchSiteId.trim() || loading"
            >
              {{ loading ? 'Loading...' : 'Load Site' }}
            </button>
          </div>
          
          <div v-if="errorMessage" class="error-message">
            ⚠️ {{ errorMessage }}
          </div>
        </div>
        
        <!-- Edit Section -->
        <div v-else class="edit-section">
          <div class="site-header">
            <h4>Site ID: {{ siteData.site_id }}</h4>
            <button class="btn-back" @click="resetForm">← Back to Search</button>
          </div>
          
          <div class="form-section">
            <h5>Address Information</h5>
            
            <div class="form-group">
              <label>Street 1 *</label>
              <input
                v-model="siteData.street1"
                type="text"
                placeholder="Street address"
                :disabled="saving"
              />
            </div>
            
            <div class="form-group">
              <label>Street 2</label>
              <input
                v-model="siteData.street2"
                type="text"
                placeholder="Apt, Suite, etc. (optional)"
                :disabled="saving"
              />
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>City *</label>
                <input
                  v-model="siteData.city"
                  type="text"
                  placeholder="City"
                  :disabled="saving"
                />
              </div>
              
              <div class="form-group form-small">
                <label>State *</label>
                <input
                  v-model="siteData.state"
                  type="text"
                  placeholder="ST"
                  maxlength="2"
                  :disabled="saving"
                />
              </div>
              
              <div class="form-group">
                <label>Zip *</label>
                <input
                  v-model="siteData.zip"
                  type="text"
                  placeholder="Zip code"
                  :disabled="saving"
                />
              </div>
            </div>
          </div>
          
          <div class="form-section">
            <h5>Coordinates</h5>
            
            <div class="form-row">
              <div class="form-group">
                <label>Latitude *</label>
                <input
                  v-model.number="siteData.lat"
                  type="number"
                  step="0.000001"
                  placeholder="e.g., 39.9526"
                  :disabled="saving"
                />
              </div>
              
              <div class="form-group">
                <label>Longitude *</label>
                <input
                  v-model.number="siteData.lon"
                  type="number"
                  step="0.000001"
                  placeholder="e.g., -75.1652"
                  :disabled="saving"
                />
              </div>
            </div>
            
            <button 
              class="btn-geocode"
              @click="geocodeAddress"
              :disabled="saving || geocoding"
            >
              {{ geocoding ? 'Geocoding...' : '🌍 Auto-Geocode from Address' }}
            </button>
          </div>
          
          <div v-if="successMessage" class="success-message">
            ✓ {{ successMessage }}
          </div>
          
          <div v-if="errorMessage" class="error-message">
            ⚠️ {{ errorMessage }}
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn-cancel" @click="closeModal" :disabled="saving">
          Cancel
        </button>
        <button 
          v-if="siteData"
          class="btn-save"
          @click="saveSite"
          :disabled="saving || !isFormValid"
        >
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { geocodeAPI } from '../services/api'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  workspaceName: {
    type: String,
    required: true
  },
  stateName: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])

const searchSiteId = ref('')
const siteData = ref(null)
const loading = ref(false)
const saving = ref(false)
const geocoding = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const isFormValid = computed(() => {
  if (!siteData.value) return false
  return (
    siteData.value.street1?.trim() &&
    siteData.value.city?.trim() &&
    siteData.value.state?.trim() &&
    siteData.value.zip?.trim() &&
    siteData.value.lat !== null &&
    siteData.value.lon !== null &&
    !isNaN(siteData.value.lat) &&
    !isNaN(siteData.value.lon)
  )
})

async function loadSite() {
  const siteId = searchSiteId.value.trim()
  if (!siteId) return
  
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const response = await geocodeAPI.getSite(props.workspaceName, props.stateName, siteId)
    siteData.value = response.data
  } catch (error) {
    console.error('Failed to load site:', error)
    errorMessage.value = error.response?.data?.detail || 'Site not found. Please check the Site ID.'
    siteData.value = null
  } finally {
    loading.value = false
  }
}

async function geocodeAddress() {
  if (!siteData.value) return
  
  geocoding.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const response = await geocodeAPI.retryAddress(
      props.workspaceName,
      props.stateName,
      {
        site_id: siteData.value.site_id,
        street1: siteData.value.street1,
        street2: siteData.value.street2 || '',
        city: siteData.value.city,
        state: siteData.value.state,
        zip: siteData.value.zip
      }
    )
    
    if (response.data.success) {
      // Update coordinates with geocoded values
      siteData.value.lat = response.data.lat
      siteData.value.lon = response.data.lon
      successMessage.value = 'Address geocoded successfully! Coordinates updated.'
    } else {
      errorMessage.value = response.data.message
    }
  } catch (error) {
    console.error('Failed to geocode address:', error)
    errorMessage.value = 'Failed to geocode address. Please enter coordinates manually.'
  } finally {
    geocoding.value = false
  }
}

async function saveSite() {
  if (!isFormValid.value) return
  
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    await geocodeAPI.updateSite(
      props.workspaceName,
      props.stateName,
      siteData.value.site_id,
      {
        street1: siteData.value.street1,
        street2: siteData.value.street2 || '',
        city: siteData.value.city,
        state: siteData.value.state,
        zip: siteData.value.zip,
        lat: parseFloat(siteData.value.lat),
        lon: parseFloat(siteData.value.lon)
      }
    )
    
    successMessage.value = 'Site updated successfully!'
    
    // Emit update event
    emit('updated')
    
    // Close modal after a short delay
    setTimeout(() => {
      closeModal()
    }, 1500)
  } catch (error) {
    console.error('Failed to save site:', error)
    errorMessage.value = error.response?.data?.detail || 'Failed to save changes. Please try again.'
  } finally {
    saving.value = false
  }
}

function resetForm() {
  siteData.value = null
  searchSiteId.value = ''
  errorMessage.value = ''
  successMessage.value = ''
}

function closeModal() {
  resetForm()
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.25rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: #f3f4f6;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.search-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.help-text {
  margin: 0;
  padding: 1rem;
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  color: #1e40af;
  font-size: 0.9rem;
  border-radius: 4px;
}

.search-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
}

.search-form .form-group {
  flex: 1;
}

.btn-search {
  padding: 0.625rem 1.5rem;
  background-color: #1e3a8a;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.btn-search:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn-search:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;
}

.site-header h4 {
  margin: 0;
  color: #1e3a8a;
  font-size: 1.1rem;
}

.btn-back {
  padding: 0.5rem 1rem;
  background-color: #6b7280;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-back:hover {
  background-color: #4b5563;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-section h5 {
  margin: 0;
  color: #374151;
  font-size: 1rem;
  font-weight: 600;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #374151;
}

.form-group input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #1e3a8a;
}

.form-group input:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

.form-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr;
  gap: 1rem;
}

.form-small input {
  text-transform: uppercase;
}

.btn-geocode {
  padding: 0.625rem 1rem;
  background-color: #059669;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-top: 0.5rem;
}

.btn-geocode:hover:not(:disabled) {
  background-color: #047857;
}

.btn-geocode:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.success-message {
  padding: 0.75rem 1rem;
  background: #d1fae5;
  color: #065f46;
  border-left: 4px solid #10b981;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
}

.error-message {
  padding: 0.75rem 1rem;
  background: #fee2e2;
  color: #991b1b;
  border-left: 4px solid #dc2626;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-cancel {
  padding: 0.5rem 1.5rem;
  background-color: #6b7280;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-cancel:hover:not(:disabled) {
  background-color: #4b5563;
}

.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-save {
  padding: 0.5rem 1.5rem;
  background-color: #1e3a8a;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-save:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .modal-content {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .search-form {
    flex-direction: column;
    align-items: stretch;
  }
  
  .btn-search {
    width: 100%;
  }
}
</style>
