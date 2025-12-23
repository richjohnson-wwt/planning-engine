import axios from 'axios'

// API client for FastAPI backend
// In production, use VITE_API_URL env var; in development, use proxy
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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
  }
}

export default api
