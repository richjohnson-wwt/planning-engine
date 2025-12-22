import axios from 'axios'

// API client for FastAPI backend
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Workspace API
export const workspaceAPI = {
  create(workspaceName) {
    return api.post('/workspace', { workspace_name: workspaceName })
  },
  
  list() {
    // Note: This endpoint may need to be added to FastAPI backend
    return api.get('/workspaces')
  }
}

// Excel parsing API
export const excelAPI = {
  parse(workspaceName, stateAbbr, file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/parse-excel?workspace_name=${workspaceName}&state_abbr=${stateAbbr}`, formData, {
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

export default api
