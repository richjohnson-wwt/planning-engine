<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content error-modal">
      <div class="modal-header">
        <div class="header-content">
          <span class="error-icon">⚠️</span>
          <h3>Planning Failed</h3>
        </div>
        <button class="close-button" @click="closeModal">&times;</button>
      </div>

      <div class="modal-body">
        <div class="error-summary">
          <p class="error-message">{{ errorSummary }}</p>
        </div>

        <div v-if="recommendations.length > 0" class="recommendations-section">
          <h4>💡 Suggestions to Fix This</h4>
          <ul class="recommendations-list">
            <li v-for="(rec, index) in recommendations" :key="index" class="recommendation-item">
              <span class="rec-icon">{{ rec.icon }}</span>
              <div class="rec-content">
                <strong>{{ rec.title }}</strong>
                <p>{{ rec.description }}</p>
                <div v-if="rec.currentValue" class="current-value">
                  Current: <code>{{ rec.currentValue }}</code>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <div v-if="technicalDetails" class="technical-details">
          <button 
            class="details-toggle" 
            @click="showTechnicalDetails = !showTechnicalDetails"
          >
            {{ showTechnicalDetails ? '▼' : '▶' }} Technical Details
          </button>
          <pre v-if="showTechnicalDetails" class="details-content">{{ technicalDetails }}</pre>
        </div>
      </div>

      <div class="modal-actions">
        <button class="btn btn-primary" @click="closeModal">
          Got it, I'll adjust settings
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  error: {
    type: String,
    default: ''
  },
  planRequest: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

const showTechnicalDetails = ref(false)

// Parse error message and extract recommendations
const parsedError = computed(() => {
  if (!props.error) return null

  const errorText = props.error

  // Extract key information from error message
  const sitesRemainingMatch = errorText.match(/Sites remaining: (\d+)/)
  const sitesScheduledMatch = errorText.match(/Sites scheduled today: (\d+)/)
  const unassignedMatch = errorText.match(/Unassigned: (\d+)/)
  const consecutiveDaysMatch = errorText.match(/after (\d+) consecutive days/)
  const crewsMatch = errorText.match(/with (\d+) crews/)

  return {
    sitesRemaining: sitesRemainingMatch ? parseInt(sitesRemainingMatch[1]) : null,
    sitesScheduledToday: sitesScheduledMatch ? parseInt(sitesScheduledMatch[1]) : 0,
    unassigned: unassignedMatch ? parseInt(unassignedMatch[1]) : null,
    consecutiveDays: consecutiveDaysMatch ? parseInt(consecutiveDaysMatch[1]) : null,
    crews: crewsMatch ? parseInt(crewsMatch[1]) : null,
    fullError: errorText
  }
})

const errorSummary = computed(() => {
  const parsed = parsedError.value
  if (!parsed) return props.error

  if (parsed.sitesRemaining && parsed.consecutiveDays) {
    return `Unable to schedule ${parsed.sitesRemaining} site${parsed.sitesRemaining > 1 ? 's' : ''} after ${parsed.consecutiveDays} days of trying. The current constraints are too tight for the geographic area.`
  }

  return props.error
})

const recommendations = computed(() => {
  const recs = []
  const parsed = parsedError.value
  const request = props.planRequest

  if (!parsed) return recs

  // Check if Fast Mode is enabled
  if (request.fast_mode) {
    recs.push({
      icon: '🚀',
      title: 'Disable Fast Mode',
      description: 'Fast Mode uses quick heuristics that may miss valid solutions. Try disabling it for better optimization.',
      currentValue: 'Fast Mode: ON'
    })
  }

  // Check max route minutes
  if (request.max_route_minutes && request.max_route_minutes < 600) {
    recs.push({
      icon: '⏱️',
      title: 'Increase Max Route Minutes',
      description: 'Your current route time limit may be too short for distant sites. Try increasing to 600-720 minutes (10-12 hours).',
      currentValue: `${request.max_route_minutes} minutes (${(request.max_route_minutes / 60).toFixed(1)} hours)`
    })
  }

  // Check service time
  if (request.service_minutes_per_site && request.service_minutes_per_site > 60) {
    recs.push({
      icon: '🔧',
      title: 'Reduce Service Time Per Site',
      description: 'High service times leave less time for travel. If your actual service time is lower, adjust this setting.',
      currentValue: `${request.service_minutes_per_site} minutes per site`
    })
  }

  // Check crew count for single crew scenarios
  if (parsed.crews === 1 && parsed.sitesRemaining > 5) {
    recs.push({
      icon: '👥',
      title: 'Increase Number of Teams',
      description: 'With only 1 crew, large geographic areas may be infeasible within reasonable time constraints. Consider using 2-3 crews.',
      currentValue: '1 crew'
    })
  }

  // Check clustering
  if (!request.use_clusters && parsed.sitesRemaining > 10) {
    recs.push({
      icon: '🗺️',
      title: 'Enable Regional Clustering',
      description: 'Clustering groups nearby sites into regions, which helps optimize routes in large geographic areas. This is especially helpful with multiple crews.',
      currentValue: 'Clustering: OFF'
    })
  }

  // If no specific recommendations, provide general guidance
  if (recs.length === 0) {
    recs.push({
      icon: '💡',
      title: 'Adjust Constraints',
      description: 'The current combination of settings makes it impossible to schedule all sites. Try relaxing one or more constraints.',
      currentValue: null
    })
  }

  return recs
})

const technicalDetails = computed(() => {
  return parsedError.value?.fullError || props.error
})

function closeModal() {
  showTechnicalDetails.value = false
  emit('close')
}

// Reset technical details when modal closes
watch(() => props.isOpen, (newValue) => {
  if (!newValue) {
    showTechnicalDetails.value = false
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  max-width: 650px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.error-modal .modal-header {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-bottom: 2px solid #f87171;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.error-icon {
  font-size: 2rem;
  line-height: 1;
}

.modal-header h3 {
  margin: 0;
  color: #991b1b;
  font-size: 1.5rem;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  color: #991b1b;
  cursor: pointer;
  line-height: 1;
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
  background-color: rgba(153, 27, 27, 0.1);
}

.modal-body {
  padding: 1.5rem;
}

.error-summary {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #fef2f2;
  border-left: 4px solid #dc2626;
  border-radius: 4px;
}

.error-message {
  margin: 0;
  color: #7f1d1d;
  font-size: 1rem;
  line-height: 1.6;
}

.recommendations-section {
  margin-bottom: 1.5rem;
}

.recommendations-section h4 {
  margin: 0 0 1rem 0;
  color: #1f2937;
  font-size: 1.1rem;
  font-weight: 600;
}

.recommendations-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.recommendation-item {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  transition: all 0.2s;
}

.recommendation-item:hover {
  background: #dcfce7;
  border-color: #4ade80;
  transform: translateX(4px);
}

.rec-icon {
  font-size: 1.5rem;
  line-height: 1;
  flex-shrink: 0;
}

.rec-content {
  flex: 1;
}

.rec-content strong {
  display: block;
  color: #065f46;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.rec-content p {
  margin: 0 0 0.5rem 0;
  color: #047857;
  font-size: 0.9rem;
  line-height: 1.5;
}

.current-value {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #059669;
}

.current-value code {
  background: #d1fae5;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

.technical-details {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.details-toggle {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
  transition: all 0.2s;
  width: 100%;
  text-align: left;
}

.details-toggle:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.details-content {
  margin-top: 0.75rem;
  padding: 1rem;
  background: #1f2937;
  color: #f3f4f6;
  border-radius: 6px;
  font-size: 0.85rem;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
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

.btn-primary {
  background-color: #1e3a8a;
  color: white;
}

.btn-primary:hover {
  background-color: #1e40af;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(30, 58, 138, 0.2);
}

@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
  }

  .recommendation-item {
    flex-direction: column;
    gap: 0.5rem;
  }

  .rec-icon {
    font-size: 1.25rem;
  }
}
</style>
