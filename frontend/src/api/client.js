import axios from 'axios'
import { io } from 'socket.io-client'

// API Client
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : 'http://127.0.0.1:5000/api'

console.log('[API] Configured base URL:', API_BASE_URL)

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Socket.IO Client
let socket = null

export const initializeSocket = () => {
  if (socket) return socket
  
  // Determine the backend URL based on environment
  const backendUrl = process.env.NODE_ENV === 'production' 
    ? window.location.origin 
    : 'http://127.0.0.1:5000'
  
  console.log('[WebSocket] Initializing connection to:', backendUrl)
  
  socket = io(backendUrl, {
    transports: ['websocket', 'polling'],
    upgrade: true,
    autoConnect: false,
    timeout: 30000, // 30 seconds timeout
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    maxReconnectionAttempts: 10,
    forceNew: false
  })
  
  socket.on('connect', () => {
    console.log('Socket connected:', socket.id)
  })
  
  socket.on('disconnect', (reason) => {
    console.log('Socket disconnected:', reason)
  })
  
  socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error)
  })
  
  socket.on('reconnect', (attemptNumber) => {
    console.log('Socket reconnected after', attemptNumber, 'attempts')
  })
  
  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log('Socket reconnection attempt:', attemptNumber)
  })
  
  socket.on('reconnect_error', (error) => {
    console.error('Socket reconnection error:', error)
  })
  
  // Handle heartbeat messages
  socket.on('heartbeat', (data) => {
    console.log('Received heartbeat:', data.timestamp)
  })
  
  return socket
}

export const getSocket = () => {
  if (!socket) {
    return initializeSocket()
  }
  return socket
}

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

// API Endpoints
export const courseAPI = {
  // Generate new course
  generateCourse: (courseData) => 
    apiClient.post('/generate-course', courseData),
  
  // Get course by session ID
  getCourse: (sessionId) => 
    apiClient.get(`/course/${sessionId}`),
  
  // Get course slide images (triggers PPTX to image conversion if needed)
  getCourseSlides: (sessionId) => 
    apiClient.get(`/course/${sessionId}/slides`),
  
  // List all courses
  listCourses: (params = {}) => 
    apiClient.get('/courses', { params }),
  
  // Delete course
  deleteCourse: (sessionId) => 
    apiClient.delete(`/course/${sessionId}`),
  
  // Export course
  exportCourse: (sessionId, format = 'zip') => 
    apiClient.get(`/course/${sessionId}/export`, { 
      params: { format },
      responseType: 'blob'
    }),
  
  // Import course
  importCourse: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/import-course', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // Enhanced progress tracking endpoints
  getDetailedProgress: (sessionId) => 
    apiClient.get(`/session/${sessionId}/progress/detailed`),
  
  getProgressStatistics: (sessionId) => 
    apiClient.get(`/session/${sessionId}/progress/statistics`),
  
  getProgressStages: (sessionId) => 
    apiClient.get(`/session/${sessionId}/progress/stages`),
  
  getSessionLogs: (sessionId) => 
    apiClient.get(`/session/${sessionId}/logs`),
  
  getSessionTranscripts: (sessionId) => 
    apiClient.get(`/session/${sessionId}/transcripts`),
  
  // Session status
  getSessionStatus: (sessionId) => 
    apiClient.get(`/session/${sessionId}/status`)
}

export const audioAPI = {
  // Get TTS voices
  getVoices: () => 
    apiClient.get('/tts/voices'),
  
  // Generate audio for slide
  generateAudio: (slideData, options = {}) => 
    apiClient.post('/audio/generate', { slideData, options }, {
      responseType: 'blob'
    }),
  
  // Transcribe audio (STT)
  transcribeAudio: (audioBlob) => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.wav')
    return apiClient.post('/stt/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export const conversationAPI = {
  // Start conversation
  startConversation: (sessionId, slideContext) => 
    apiClient.post('/conversation/start', { sessionId, slideContext }),
  
  // Ask question - fix parameter mapping
  askQuestion: (conversationSessionId, question, slideContext = {}) => 
    apiClient.post('/conversation/ask', { 
      session_id: conversationSessionId, 
      question, 
      slide_context: slideContext 
    }),
  
  // Get conversation history
  getHistory: (sessionId) => 
    apiClient.get(`/conversation/${sessionId}/history`),
  
  // End conversation
  endConversation: (sessionId) => 
    apiClient.post(`/conversation/${sessionId}/end`),
  
}

export const fileAPI = {
  // Get storage stats
  getStorageStats: () => 
    apiClient.get('/files/stats'),
  
  // Cleanup old files
  cleanupFiles: (maxAge = 30) => 
    apiClient.post('/files/cleanup', { maxAge }),
  
  // Get file info
  getFileInfo: (filePath) => 
    apiClient.get('/files/info', { params: { path: filePath } })
}

export const settingsAPI = {
  // Get user settings
  getSettings: () => 
    apiClient.get('/settings'),
  
  // Save user settings
  saveSettings: (settings) => 
    apiClient.post('/settings', settings)
}

export const templatesAPI = {
  // Get course templates
  getCourseTemplates: () => 
    apiClient.get('/course-templates')
}

// Utility functions
export const downloadFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export const uploadFile = (file, onProgress) => {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)
    
    apiClient.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percentCompleted)
        }
      }
    })
    .then(resolve)
    .catch(reject)
  })
}

// Error handling utilities
export const handleAPIError = (error, defaultMessage = 'An error occurred') => {
  if (error.response?.data?.error) {
    return error.response.data.error
  }
  if (error.response?.data?.message) {
    return error.response.data.message
  }
  if (error.message) {
    return error.message
  }
  return defaultMessage
}

export const isNetworkError = (error) => {
  return !error.response && error.request
}

export const isTimeoutError = (error) => {
  return error.code === 'ECONNABORTED' || error.message.includes('timeout')
}

export default apiClient