<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Geocoding Errors - {{ stateName }} ({{ errors.length }} address{{ errors.length !== 1 ? 'es' : '' }})</h3>
        <button class="close-button" @click="closeModal">✕</button>
      </div>
      
      <div class="modal-body">
        <div v-if="loading" class="loading-state">
          <p>Loading errors...</p>
        </div>
        
        <div v-else-if="errors.length === 0" class="empty-state">
          <p>✓ All addresses have been successfully geocoded!</p>
        </div>
        
        <div v-else class="errors-list">
          <p class="help-text">
            ⚠️ The following addresses could not be geocoded. Edit the address and click Retry to geocode.
          </p>
          
          <div 
            v-for="error in errors" 
            :key="error.site_id" 
            class="error-card"
            :class="{ 'processing': processingIds.has(error.site_id) }"
          >
            <div class="error-header">
              <span class="site-id">Site ID: {{ error.site_id }}</span>
              <div class="error-actions">
                <button 
                  class="btn-retry"
                  @click="retryGeocode(error)"
                  :disabled="processingIds.has(error.site_id)"
                >
                  {{ processingIds.has(error.site_id) ? 'Geocoding...' : 'Retry' }}
                </button>
                <button 
                  class="btn-delete"
                  @click="deleteError(error.site_id)"
                  :disabled="processingIds.has(error.site_id)"
                  title="Remove this error (exclude from planning)"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div class="address-fields">
              <div class="field-row">
                <label>Street 1:</label>
                <input 
                  v-model="error.street1" 
                  type="text" 
                  placeholder="Street address"
                  :disabled="processingIds.has(error.site_id)"
                />
              </div>
              
              <div class="field-row">
                <label>Street 2:</label>
                <input 
                  v-model="error.street2" 
                  type="text" 
                  placeholder="Apt, Suite, etc. (optional)"
                  :disabled="processingIds.has(error.site_id)"
                />
              </div>
              
              <div class="field-row-group">
                <div class="field-row">
                  <label>City:</label>
                  <input 
                    v-model="error.city" 
                    type="text" 
                    placeholder="City"
                    :disabled="processingIds.has(error.site_id)"
                  />
                </div>
                
                <div class="field-row field-small">
                  <label>State:</label>
                  <input 
                    v-model="error.state" 
                    type="text" 
                    placeholder="ST"
                    maxlength="2"
                    :disabled="processingIds.has(error.site_id)"
                  />
                </div>
                
                <div class="field-row">
                  <label>Zip:</label>
                  <input 
                    v-model="error.zip" 
                    type="text" 
                    placeholder="Zip code"
                    :disabled="processingIds.has(error.site_id)"
                  />
                </div>
              </div>
            </div>
            
            <div v-if="errorMessages[error.site_id]" class="status-message error-message">
              ⚠️ {{ errorMessages[error.site_id] }}
            </div>
            
            <div v-if="successMessages[error.site_id]" class="status-message success-message">
              ✓ {{ successMessages[error.site_id] }}
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn-close" @click="closeModal">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
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

const errors = ref([])
const loading = ref(false)
const processingIds = ref(new Set())
const errorMessages = ref({})
const successMessages = ref({})

// Watch for modal opening to load errors
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    loadErrors()
  } else {
    // Clear messages when modal closes
    errorMessages.value = {}
    successMessages.value = {}
  }
})

async function loadErrors() {
  loading.value = true
  try {
    const response = await geocodeAPI.getErrors(props.workspaceName, props.stateName)
    // Normalize the error data to handle NaN values and ensure proper types
    errors.value = response.data.errors.map(error => ({
      site_id: String(error.site_id || ''),
      street1: String(error.street1 || ''),
      street2: error.street2 === null || isNaN(error.street2) ? '' : String(error.street2),
      city: String(error.city || ''),
      state: String(error.state || ''),
      zip: error.zip === null || isNaN(error.zip) ? '' : String(Math.round(error.zip))
    }))
  } catch (error) {
    console.error('Failed to load geocoding errors:', error)
    errors.value = []
  } finally {
    loading.value = false
  }
}

async function retryGeocode(error) {
  // Clear previous messages
  delete errorMessages.value[error.site_id]
  delete successMessages.value[error.site_id]
  
  // Mark as processing
  processingIds.value.add(error.site_id)
  
  try {
    const response = await geocodeAPI.retryAddress(
      props.workspaceName,
      props.stateName,
      {
        site_id: error.site_id,
        street1: error.street1,
        street2: error.street2 || '',
        city: error.city,
        state: error.state,
        zip: error.zip
      }
    )
    
    if (response.data.success) {
      // Show success message
      successMessages.value[error.site_id] = response.data.message
      
      // Remove from errors list after a short delay
      setTimeout(() => {
        errors.value = errors.value.filter(e => e.site_id !== error.site_id)
        delete successMessages.value[error.site_id]
        
        // Emit update event to refresh state table
        emit('updated')
        
        // Close modal if no more errors
        if (errors.value.length === 0) {
          setTimeout(() => closeModal(), 500)
        }
      }, 1500)
    } else {
      // Show error message
      errorMessages.value[error.site_id] = response.data.message
    }
  } catch (error) {
    console.error('Failed to retry geocoding:', error)
    errorMessages.value[error.site_id] = 'Failed to geocode address. Please try again.'
  } finally {
    processingIds.value.delete(error.site_id)
  }
}

async function deleteError(siteId) {
  if (!confirm('Are you sure you want to remove this error? The address will be excluded from route planning.')) {
    return
  }
  
  processingIds.value.add(siteId)
  
  try {
    await geocodeAPI.deleteError(props.workspaceName, props.stateName, siteId)
    
    // Remove from errors list
    errors.value = errors.value.filter(e => e.site_id !== siteId)
    
    // Emit update event to refresh state table
    emit('updated')
    
    // Close modal if no more errors
    if (errors.value.length === 0) {
      setTimeout(() => closeModal(), 500)
    }
  } catch (error) {
    console.error('Failed to delete error:', error)
    alert('Failed to remove error. Please try again.')
  } finally {
    processingIds.value.delete(siteId)
  }
}

function closeModal() {
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
  max-width: 800px;
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

.loading-state,
.empty-state {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

.empty-state {
  color: #10b981;
  font-weight: 500;
}

.help-text {
  margin: 0 0 1.5rem 0;
  padding: 1rem;
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  color: #92400e;
  font-size: 0.9rem;
  border-radius: 4px;
}

.errors-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.error-card {
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  padding: 1rem;
  background: white;
  transition: all 0.2s;
}

.error-card.processing {
  opacity: 0.6;
  pointer-events: none;
}

.error-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.site-id {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.95rem;
}

.error-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-retry {
  padding: 0.375rem 0.75rem;
  background-color: #1e3a8a;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-retry:hover:not(:disabled) {
  background-color: #1e40af;
}

.btn-retry:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-delete {
  padding: 0.375rem 0.5rem;
  background-color: #dc2626;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-delete:hover:not(:disabled) {
  background-color: #b91c1c;
}

.btn-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.address-fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-row label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #374151;
}

.field-row input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.field-row input:focus {
  outline: none;
  border-color: #1e3a8a;
}

.field-row input:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

.field-row-group {
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr;
  gap: 0.75rem;
}

.field-small input {
  text-transform: uppercase;
}

.status-message {
  margin-top: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.error-message {
  background: #fee2e2;
  color: #991b1b;
  border-left: 4px solid #dc2626;
}

.success-message {
  background: #d1fae5;
  color: #065f46;
  border-left: 4px solid #10b981;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
}

.btn-close {
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

.btn-close:hover {
  background-color: #4b5563;
}

@media (max-width: 768px) {
  .modal-content {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .field-row-group {
    grid-template-columns: 1fr;
  }
}
</style>
