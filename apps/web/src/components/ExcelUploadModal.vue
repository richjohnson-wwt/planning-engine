<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Upload Excel File</h3>
        <button class="close-button" @click="closeModal">&times;</button>
      </div>

      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- File Selection -->
          <div class="form-group">
            <label for="file-browse">Excel File <span class="required">*</span></label>
            <div class="file-input-group">
              <input
                id="file-display"
                v-model="fileDisplayName"
                type="text"
                class="form-control"
                placeholder="No file selected"
                readonly
              />
              <button type="button" class="btn-browse" @click="triggerFileBrowser">
                Browse...
              </button>
            </div>
            <input
              ref="fileInput"
              type="file"
              accept=".xlsx,.xls"
              style="display: none"
              @change="handleFileSelect"
              required
            />
            <p class="help-text">
              Click Browse to select your Excel file. The file will be uploaded directly.
            </p>
          </div>

          <!-- Sheet Selection -->
          <div v-if="availableSheets.length > 0" class="form-group">
            <label class="form-label">
              Select Sheet <span class="required">*</span>
            </label>
            <div v-if="availableSheets.length === 1" class="single-sheet-info">
              <span class="sheet-badge">{{ availableSheets[0] }}</span>
              <span class="help-text">(Only one sheet available - auto-selected)</span>
            </div>
            <div v-else class="sheet-selection">
              <label
                v-for="sheet in availableSheets"
                :key="sheet"
                class="sheet-option"
              >
                <input
                  type="radio"
                  :value="sheet"
                  v-model="formData.sheet_name"
                  name="sheet-selection"
                  required
                />
                <span class="sheet-name">{{ sheet }}</span>
              </label>
            </div>
            <p class="help-text">Select which sheet contains the address data</p>
          </div>

          <!-- Column Mapping Section -->
          <div class="form-section">
            <h4>Column Mapping</h4>
            <p class="section-description">Map your Excel column names to the required fields</p>

            <div class="mapping-grid">
              <div class="form-group">
                <label for="site-id">Site ID <span class="required">*</span></label>
                <input
                  id="site-id"
                  v-model="formData.column_mapping.site_id"
                  type="text"
                  class="form-control"
                  placeholder="e.g., Lab name, Location ID"
                  required
                />
              </div>

              <div class="form-group">
                <label for="street1">Street Address 1 <span class="required">*</span></label>
                <input
                  id="street1"
                  v-model="formData.column_mapping.street1"
                  type="text"
                  class="form-control"
                  placeholder="e.g., Address, Street"
                  required
                />
              </div>

              <div class="form-group">
                <label for="street2">Street Address 2</label>
                <input
                  id="street2"
                  v-model="formData.column_mapping.street2"
                  type="text"
                  class="form-control"
                  placeholder="e.g., Address 2, Suite (optional)"
                />
              </div>

              <div class="form-group">
                <label for="city">City <span class="required">*</span></label>
                <input
                  id="city"
                  v-model="formData.column_mapping.city"
                  type="text"
                  class="form-control"
                  placeholder="e.g., City"
                  required
                />
              </div>

              <div class="form-group">
                <label for="state">State <span class="required">*</span></label>
                <input
                  id="state"
                  v-model="formData.column_mapping.state"
                  type="text"
                  class="form-control"
                  placeholder="e.g., State, ST"
                  required
                />
              </div>

              <div class="form-group">
                <label for="zip">Zip Code <span class="required">*</span></label>
                <input
                  id="zip"
                  v-model="formData.column_mapping.zip"
                  type="text"
                  class="form-control"
                  placeholder="e.g., Zip Code, Postal Code"
                  required
                />
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="closeModal">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="uploading">
              {{ uploading ? 'Parsing...' : 'Parse Excel' }}
            </button>
          </div>
        </form>

        <!-- Status Messages -->
        <div v-if="error" class="error-message">
          <strong>Error:</strong> {{ error }}
        </div>
        <div v-if="success" class="success-message">
          <strong>Success!</strong> {{ success }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { excelAPI } from '../services/api'
import * as XLSX from 'xlsx'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  workspace: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close', 'success'])

const formData = ref({
  file_path: '',
  sheet_name: '',
  column_mapping: {
    site_id: '',
    street1: '',
    street2: '',
    city: '',
    state: '',
    zip: ''
  }
})

const uploading = ref(false)
const error = ref(null)
const success = ref(null)
const fileInput = ref(null)
const availableSheets = ref([])
const selectedFile = ref(null)
const fileDisplayName = ref('')

// Reset form when modal opens
watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    resetForm()
  }
})

function triggerFileBrowser() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    selectedFile.value = file
    fileDisplayName.value = file.name
    
    // Read the Excel file to get sheet names
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result)
        const workbook = XLSX.read(data, { type: 'array' })
        availableSheets.value = workbook.SheetNames
        
        // Auto-select if only one sheet
        if (availableSheets.value.length === 1) {
          formData.value.sheet_name = availableSheets.value[0]
        } else {
          formData.value.sheet_name = '' // Clear selection for multiple sheets
        }
        
        // Clear any previous messages
        success.value = null
        error.value = null
      } catch (err) {
        console.error('Error reading Excel file:', err)
        error.value = 'Failed to read Excel file. Please ensure it is a valid .xlsx or .xls file.'
        availableSheets.value = []
        fileDisplayName.value = ''
      }
    }
    reader.readAsArrayBuffer(file)
  }
}

function resetForm() {
  formData.value = {
    sheet_name: '',
    column_mapping: {
      site_id: '',
      street1: '',
      street2: '',
      city: '',
      state: '',
      zip: ''
    }
  }
  availableSheets.value = []
  selectedFile.value = null
  fileDisplayName.value = ''
  error.value = null
  success.value = null
  // Reset file input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function closeModal() {
  emit('close')
}

async function handleSubmit() {
  try {
    uploading.value = true
    error.value = null
    success.value = null

    // Validate file is selected
    if (!selectedFile.value) {
      error.value = 'Please select an Excel file'
      uploading.value = false
      return
    }

    // Filter out empty optional fields from column mapping
    const cleanedMapping = {}
    for (const [key, value] of Object.entries(formData.value.column_mapping)) {
      if (value && value.trim() !== '') {
        cleanedMapping[key] = value.trim()
      }
    }

    // Call the parse-excel API with file upload
    const response = await excelAPI.parseWithFile(
      props.workspace,
      selectedFile.value,
      formData.value.sheet_name,
      cleanedMapping
    )

    success.value = response.data.message || 'Excel file parsed successfully!'
    
    // Emit success event to parent
    setTimeout(() => {
      emit('success')
      closeModal()
    }, 1500)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to parse Excel file'
  } finally {
    uploading.value = false
  }
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
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
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
  color: #1e3a8a;
  font-size: 1.25rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  color: #6b7280;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  color: #1f2937;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.form-section h4 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
  font-size: 1.1rem;
}

.section-description {
  margin: 0 0 1.5rem 0;
  color: #6b7280;
  font-size: 0.9rem;
}

.mapping-grid {
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

.required {
  color: #dc2626;
  font-weight: 600;
}

.file-input-group {
  display: flex;
  gap: 0.5rem;
}

.file-input-group .form-control {
  flex: 1;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.95rem;
}

.form-control:focus {
  outline: none;
  border-color: #1e3a8a;
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
}

.btn-browse {
  padding: 0.5rem 1rem;
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.btn-browse:hover {
  background-color: #e5e7eb;
  border-color: #9ca3af;
}

.sheet-selection {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.sheet-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.sheet-option:hover {
  background-color: #f9fafb;
  border-color: #1e3a8a;
}

.sheet-option input[type="radio"] {
  cursor: pointer;
}

.sheet-name {
  font-weight: 500;
  color: #374151;
}

.single-sheet-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background-color: #f0fdf4;
  border: 1px solid #10b981;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.sheet-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background-color: #10b981;
  color: white;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.help-text {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #e5e7eb;
}

.btn-primary {
  background-color: #1e3a8a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1e40af;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee2e2;
  border-radius: 6px;
  color: #991b1b;
  font-size: 0.9rem;
}

.success-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #d1fae5;
  border-radius: 6px;
  color: #065f46;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .mapping-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    width: 95%;
  }
}
</style>
