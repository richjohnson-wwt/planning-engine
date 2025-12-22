import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePlanningStore = defineStore('planning', () => {
  // State
  const workspace = ref('')
  const stateAbbr = ref('')
  const planRequest = ref({
    workspace: '',
    state_abbr: '',
    use_clusters: false,
    team_config: {
      teams: 2,
      workday: {
        start: '08:00:00',
        end: '17:00:00'
      }
    },
    start_date: null,
    end_date: null,
    max_route_minutes: 480,
    service_minutes_per_site: 30,
    break_minutes: 30,
    holidays: [],
    fast_mode: false
  })
  
  const planResult = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Actions
  function setWorkspace(name) {
    workspace.value = name
    planRequest.value.workspace = name
  }

  function setStateAbbr(abbr) {
    stateAbbr.value = abbr
    planRequest.value.state_abbr = abbr
  }

  function updatePlanRequest(updates) {
    planRequest.value = { ...planRequest.value, ...updates }
  }

  function setPlanResult(result) {
    planResult.value = result
  }

  function setLoading(value) {
    loading.value = value
  }

  function setError(err) {
    error.value = err
  }

  function reset() {
    workspace.value = ''
    stateAbbr.value = ''
    planResult.value = null
    error.value = null
  }

  return {
    workspace,
    stateAbbr,
    planRequest,
    planResult,
    loading,
    error,
    setWorkspace,
    setStateAbbr,
    updatePlanRequest,
    setPlanResult,
    setLoading,
    setError,
    reset
  }
})
