import axios from 'axios'

// API client for FastAPI backend
// In production, use VITE_API_URL env var; in development, use proxy
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth data and redirect to login
      localStorage.removeItem('auth_token')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Authentication API
export const authAPI = {
  login(username, password) {
    return api.post('/auth/login', { username, password })
  },
  
  logout() {
    return api.post('/auth/logout')
  },
  
  getCurrentUser() {
    return api.get('/auth/me')
  },
  
  listUsers() {
    return api.get('/auth/users')
  },
  
  createUser(username, password, isAdmin = false) {
    return api.post('/auth/users', {
      username,
      password,
      is_admin: isAdmin
    })
  },
  
  deleteUser(username) {
    return api.delete(`/auth/users/${username}`)
  }
}

// Workspace API
export const workspaceAPI = {
  create(workspaceName) {
    return api.post('/workspace', { workspace_name: workspaceName })
  },
  
  list() {
    return api.get('/workspaces')
  },
  
  getStates(workspaceName) {
    return api.get(`/workspaces/${workspaceName}/states`)
  }
}

// Excel parsing API
export const excelAPI = {
  parse(workspaceName, filePath, sheetName, columnMapping) {
    return api.post('/parse-excel', {
      workspace_name: workspaceName,
      file_path: filePath,
      sheet_name: sheetName,
      column_mapping: columnMapping
    })
  },
  parseWithFile(workspaceName, file, sheetName, columnMapping) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('workspace_name', workspaceName)
    formData.append('sheet_name', sheetName)
    formData.append('column_mapping', JSON.stringify(columnMapping))
    
    return api.post('/parse-excel-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}

// Geocoding API
export const geocodeAPI = {
  geocode(workspaceName, stateAbbr) {
    return api.post('/geocode', {
      workspace_name: workspaceName,
      state_abbr: stateAbbr
    })
  },
  
  // Get geocoding errors for a state
  getErrors(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/geocode-errors/${stateAbbr}`)
  },
  
  // Retry geocoding a single corrected address
  retryAddress(workspaceName, stateAbbr, addressData) {
    return api.post(`/workspaces/${workspaceName}/geocode-errors/${stateAbbr}/retry`, addressData)
  },
  
  // Delete a geocoding error
  deleteError(workspaceName, stateAbbr, siteId) {
    return api.delete(`/workspaces/${workspaceName}/geocode-errors/${stateAbbr}/${siteId}`)
  },
  
  // Get a single geocoded site by site_id
  getSite(workspaceName, stateAbbr, siteId) {
    return api.get(`/workspaces/${workspaceName}/geocoded/${stateAbbr}/${siteId}`)
  },
  
  // Update a geocoded site's address and coordinates
  updateSite(workspaceName, stateAbbr, siteId, siteData) {
    return api.put(`/workspaces/${workspaceName}/geocoded/${stateAbbr}/${siteId}`, siteData)
  }
}

// Clustering API
export const clusterAPI = {
  cluster(workspaceName, stateAbbr, numClusters = null) {
    return api.post('/cluster', {
      workspace_name: workspaceName,
      state_abbr: stateAbbr,
      num_clusters: numClusters
    })
  }
}

// Planning API
export const planningAPI = {
  plan(planRequest) {
    return api.post('/plan', planRequest)
  }
}

// Output Files API
export const outputAPI = {
  listFiles(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/output/${stateAbbr}`)
  },
  
  getFileUrl(workspaceName, stateAbbr, filename) {
    return `${import.meta.env.VITE_API_URL || '/api'}/workspaces/${workspaceName}/output/${stateAbbr}/${filename}`
  },
  
  getLatestResult(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/output/${stateAbbr}/latest`)
  }
}

// Team Management API
export const teamAPI = {
  list(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/states/${stateAbbr}/teams`)
  },
  
  create(workspaceName, stateAbbr, team) {
    return api.post(`/workspaces/${workspaceName}/states/${stateAbbr}/teams`, team)
  },
  
  update(workspaceName, stateAbbr, teamId, team) {
    return api.put(`/workspaces/${workspaceName}/states/${stateAbbr}/teams/${teamId}`, team)
  },
  
  delete(workspaceName, stateAbbr, teamId) {
    return api.delete(`/workspaces/${workspaceName}/states/${stateAbbr}/teams/${teamId}`)
  },
  
  generateId(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/states/${stateAbbr}/teams/generate-id`)
  },
  
  getCities(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/states/${stateAbbr}/cities`)
  },
  
  getPlanningTeamIds(workspaceName, stateAbbr) {
    return api.get(`/workspaces/${workspaceName}/states/${stateAbbr}/planning-team-ids`)
  }
}

// Progress Tracking API
export const progressAPI = {
  list(workspaceName, stateFilter = null) {
    const params = stateFilter ? { state: stateFilter } : {}
    return api.get(`/workspaces/${workspaceName}/progress`, { params })
  },
  
  initialize(workspaceName, forceRefresh = false) {
    return api.post(`/workspaces/${workspaceName}/progress/init`, null, {
      params: { force_refresh: forceRefresh }
    })
  },
  
  update(workspaceName, siteId, updateData) {
    return api.put(`/workspaces/${workspaceName}/progress/${siteId}`, updateData)
  },
  
  bulkUpdate(workspaceName, updateData) {
    return api.put(`/workspaces/${workspaceName}/progress/bulk`, updateData)
  }
}

export default api
