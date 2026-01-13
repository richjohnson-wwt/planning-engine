import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// Helper functions for localStorage
const STORAGE_KEY_WORKSPACE = 'planning_workspace'
const STORAGE_KEY_STATE = 'planning_state'

function loadFromStorage(key, defaultValue = '') {
  try {
    const value = localStorage.getItem(key)
    return value !== null ? value : defaultValue
  } catch (e) {
    console.warn('Failed to load from localStorage:', e)
    return defaultValue
  }
}

function saveToStorage(key, value) {
  try {
    if (value) {
      localStorage.setItem(key, value)
    } else {
      localStorage.removeItem(key)
    }
  } catch (e) {
    console.warn('Failed to save to localStorage:', e)
  }
}

export const usePlanningStore = defineStore('planning', () => {
  // State - initialize from localStorage
  const workspace = ref(loadFromStorage(STORAGE_KEY_WORKSPACE))
  const stateAbbr = ref(loadFromStorage(STORAGE_KEY_STATE))
  const user = ref(localStorage.getItem('username') || null)
  
  console.log('Planning store initialized')
  console.log('Loaded workspace from localStorage:', workspace.value)
  console.log('Loaded stateAbbr from localStorage:', stateAbbr.value)
  
  const planRequest = ref({
    workspace: workspace.value,
    state_abbr: stateAbbr.value,
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

  // Watch for changes and persist to localStorage
  watch(workspace, (newValue) => {
    saveToStorage(STORAGE_KEY_WORKSPACE, newValue)
  })

  watch(stateAbbr, (newValue) => {
    saveToStorage(STORAGE_KEY_STATE, newValue)
  })

  // Actions
  function setWorkspace(name) {
    // Clear plan result when workspace changes to prevent showing stale data
    if (workspace.value !== name) {
      console.log('Workspace changing, clearing plan result:', workspace.value, '->', name)
      planResult.value = null
    }
    workspace.value = name
    planRequest.value.workspace = name
  }

  function setStateAbbr(abbr) {
    // Clear plan result when state changes to prevent showing stale data
    if (stateAbbr.value !== abbr) {
      console.log('State changing, clearing plan result:', stateAbbr.value, '->', abbr)
      planResult.value = null
    }
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

  function setUser(username) {
    user.value = username
  }

  function logout() {
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('username')
    reset()
  }

  function reset() {
    workspace.value = ''
    stateAbbr.value = ''
    planResult.value = null
    error.value = null
    // Clear localStorage when resetting
    saveToStorage(STORAGE_KEY_WORKSPACE, '')
    saveToStorage(STORAGE_KEY_STATE, '')
  }

  return {
    workspace,
    stateAbbr,
    user,
    planRequest,
    planResult,
    loading,
    error,
    setWorkspace,
    setStateAbbr,
    setUser,
    logout,
    updatePlanRequest,
    setPlanResult,
    setLoading,
    setError,
    reset
  }
})
