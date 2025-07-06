import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FiPlay, 
  FiSettings, 
  FiBookOpen, 
  FiMic, 
  FiVolume2,
  FiSliders,
  FiClock,
  FiLayers,
  FiUser,
  FiZap
} from 'react-icons/fi'
import { useAppStore } from '../store/appStore'
import { courseAPI, getSocket } from '../api/client'
import { toast } from 'react-hot-toast'

const HomePage = () => {
  const navigate = useNavigate()
  const { 
    courseConfig, 
    updateCourseConfig, 
    setGenerating, 
    setProgress,
    setCurrentSession,
    setCurrentCourse,
    isGenerating,
    progress,
    availableVoices,
    courseTemplates,
    userSettings,
    loadAvailableVoices,
    loadCourseTemplates,
    loadUserSettings,
    saveUserSettings,
    applyTemplate
  } = useAppStore()
  
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const [showAdvancedCustomizations, setShowAdvancedCustomizations] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [estimatedTime, setEstimatedTime] = useState(null)
  const [progressDetails, setProgressDetails] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [enhancedProgress, setEnhancedProgress] = useState(null)
  const [processingStats, setProcessingStats] = useState(null)

  // Initialize data on component mount
  useEffect(() => {
    loadUserSettings()
    loadAvailableVoices()
    loadCourseTemplates()
  }, [loadUserSettings, loadAvailableVoices, loadCourseTemplates])

  useEffect(() => {
    const socket = getSocket()
    
    // Enhanced connection monitoring with health checks
    let healthCheckInterval = null
    let lastHeartbeat = Date.now()
    
    const startHealthCheck = () => {
      healthCheckInterval = setInterval(() => {
        const now = Date.now()
        const timeSinceLastHeartbeat = now - lastHeartbeat
        
        console.log(`[Health Check] Connection: ${connectionStatus}, Last heartbeat: ${timeSinceLastHeartbeat}ms ago`)
        console.log(`[Health Check] Socket connected: ${socket.connected}`)
        
        // If no heartbeat for more than 30 seconds, reconnect
        if (timeSinceLastHeartbeat > 30000 && socket.connected) {
          console.warn('[Health Check] No heartbeat for 30s, forcing reconnection...')
          socket.disconnect()
          socket.connect()
        }
        
        // If not connected for more than 10 seconds, try reconnecting
        if (!socket.connected && connectionStatus !== 'connected') {
          console.warn('[Health Check] Socket disconnected, attempting reconnection...')
          socket.connect()
        }
      }, 5000) // Check every 5 seconds
    }
    
    const stopHealthCheck = () => {
      if (healthCheckInterval) {
        clearInterval(healthCheckInterval)
        healthCheckInterval = null
      }
    }
    
    // Connection status tracking
    socket.on('connect', () => {
      console.log('[WebSocket] Connected to server, Socket ID:', socket.id)
      setConnectionStatus('connected')
      lastHeartbeat = Date.now()
      startHealthCheck()
    })
    
    socket.on('disconnect', (reason) => {
      console.log('[WebSocket] Disconnected from server, Reason:', reason)
      setConnectionStatus('disconnected')
      stopHealthCheck()
    })
    
    socket.on('connect_error', (error) => {
      console.error('[WebSocket] Connection error:', error)
      setConnectionStatus('error')
      stopHealthCheck()
    })
    
    socket.on('reconnect', (attemptNumber) => {
      setConnectionStatus('connected')
      console.log('[WebSocket] Reconnected to server after', attemptNumber, 'attempts')
      lastHeartbeat = Date.now()
      startHealthCheck()
    })
    
    socket.on('reconnect_error', (error) => {
      console.error('[WebSocket] Reconnection error:', error)
    })
    
    socket.on('reconnect_failed', () => {
      console.error('[WebSocket] Reconnection failed completely')
      setConnectionStatus('error')
    })
    
    // Progress updates with detailed information
    socket.on('course_progress', (data) => {
      console.log('[WebSocket] Progress update received:', {
        progress: data.progress,
        step: data.step,
        stage: data.stage,
        hasDetails: !!data.details,
        timestamp: new Date().toISOString()
      })
      lastHeartbeat = Date.now() // Update heartbeat on any message
      
      setProgress(data.progress, data.step)
      setCurrentStep(data.step)
      setEstimatedTime(data.estimated_time)
      
      // Set detailed progress information
      if (data.details || data.current_slide || data.current_image) {
        setProgressDetails({
          stage: data.stage,
          details: data.details,
          current_slide: data.current_slide,
          total_slides: data.total_slides,
          current_image: data.current_image,
          total_images: data.total_images,
          topics_count: data.topics_count,
          timestamp: data.timestamp
        })
      }
      
      // Set processing statistics if available
      if (data.statistics) {
        setProcessingStats(data.statistics)
      }
    })
    
    // Enhanced progress updates
    socket.on('enhanced_progress', (data) => {
      console.log('[WebSocket] Enhanced progress update received:', {
        overall_progress: data.overall_progress,
        current_stage: data.current_stage?.name,
        stage_id: data.current_stage?.id,
        hasStatistics: !!data.statistics,
        timestamp: new Date().toISOString()
      })
      lastHeartbeat = Date.now() // Update heartbeat on any message
      
      setEnhancedProgress(data)
      
      // Update legacy state for backward compatibility
      setProgress(data.overall_progress, data.current_stage?.name)
      setCurrentStep(data.current_stage?.name)
      
      if (data.timing?.estimated_remaining) {
        setEstimatedTime(data.timing.estimated_remaining)
      }
    })
    
    // Course completion
    socket.on('course_complete', (data) => {
      console.log('[WebSocket] Course completed:', data)
      lastHeartbeat = Date.now()
      setCurrentSession(data.session_id)
      setCurrentCourse(data.course_data)
      setGenerating(false)
      setProgressDetails(null)
      stopHealthCheck()
      
      // Show completion message with summary
      if (data.summary) {
        toast.success(
          `Course generated successfully! ${data.summary.total_slides} slides, ${data.summary.audio_files_count} audio files created.`
        )
      } else {
        toast.success('Course generated successfully!')
      }
      
      navigate(`/presentation/${data.session_id}`)
    })
    
    // Error handling
    socket.on('course_error', (data) => {
      console.error('[WebSocket] Course generation error:', data)
      lastHeartbeat = Date.now()
      setGenerating(false)
      setProgressDetails(null)
      stopHealthCheck()
      toast.error(data.error || 'Failed to generate course')
    })
    
    // Enhanced event handlers
    socket.on('connected', (data) => {
      console.log('[WebSocket] Server connection confirmed:', data)
      lastHeartbeat = Date.now()
    })
    
    socket.on('session_joined', (data) => {
      console.log('[WebSocket] Session joined confirmation:', data)
      lastHeartbeat = Date.now()
    })
    
    // Heartbeat handling
    socket.on('heartbeat', (data) => {
      const heartbeatTime = new Date(data.timestamp * 1000).toLocaleTimeString()
      console.log('[WebSocket] Heartbeat received:', {
        time: heartbeatTime,
        sessionId: data.session_id,
        status: data.status,
        serverTime: data.server_time
      })
      lastHeartbeat = Date.now()
    })
    
    // Try to connect if not already connected
    if (!socket.connected) {
      console.log('[WebSocket] Initial connection attempt...')
      socket.connect()
    }
    
    return () => {
      console.log('[WebSocket] Cleaning up event listeners and health check')
      stopHealthCheck()
      socket.off('connect')
      socket.off('disconnect')
      socket.off('connect_error')
      socket.off('reconnect')
      socket.off('reconnect_error')
      socket.off('reconnect_failed')
      socket.off('connected')
      socket.off('session_joined')
      socket.off('course_progress')
      socket.off('enhanced_progress')
      socket.off('course_complete')
      socket.off('course_error')
      socket.off('heartbeat')
    }
  }, [navigate, setProgress, setGenerating, setCurrentSession, setCurrentCourse])

  const handleStartGeneration = async () => {
    if (!courseConfig.topic.trim()) {
      toast.error('Please enter a topic to learn')
      return
    }
    
    try {
      console.log('[Course Generation] Starting course generation with config:', courseConfig)
      setGenerating(true)
      
      const socket = getSocket()
      console.log('[Course Generation] Socket connected:', socket.connected)
      
      if (!socket.connected) {
        console.log('[Course Generation] Socket not connected, attempting connection...')
        socket.connect()
        
        // Wait for connection with timeout
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('Socket connection timeout'))
          }, 15000) // 15 second timeout
          
          if (socket.connected) {
            clearTimeout(timeout)
            resolve()
          } else {
            socket.once('connect', () => {
              clearTimeout(timeout)
              console.log('[Course Generation] Socket connected successfully')
              resolve()
            })
            socket.once('connect_error', (error) => {
              clearTimeout(timeout)
              reject(error)
            })
          }
        })
      }
      
      console.log('[Course Generation] Making API request...')
      const response = await courseAPI.generateCourse(courseConfig)
      console.log('[Course Generation] API response received:', response.data)
      
      // Join the session room for real-time updates
      if (response.data && response.data.session_id) {
        console.log('[Course Generation] Joining session room:', response.data.session_id)
        socket.emit('join_session', { session_id: response.data.session_id })
        setCurrentSession(response.data.session_id)
      }
      
    } catch (error) {
      console.error('[Course Generation] Error occurred:', error)
      setGenerating(false)
      
      if (error.message === 'Socket connection timeout') {
        toast.error('Connection timeout - please check your network and try again')
      } else if (error.response?.status === 500) {
        toast.error('Server error - please try again in a moment')
      } else {
        toast.error('Failed to start course generation')
      }
    }
  }

  const complexityOptions = [
    { value: 'beginner', label: 'Beginner', description: 'Basic concepts and fundamentals' },
    { value: 'intermediate', label: 'Intermediate', description: 'Moderate depth with examples' },
    { value: 'advanced', label: 'Advanced', description: 'Complex topics with detailed analysis' },
    { value: 'expert', label: 'Expert', description: 'Professional-level comprehensive coverage' }
  ]

  const learningStyleOptions = [
    { value: 'visual', label: 'Visual', icon: FiLayers, description: 'Charts, diagrams, and images' },
    { value: 'auditory', label: 'Auditory', icon: FiVolume2, description: 'Detailed explanations and examples' },
    { value: 'mixed', label: 'Mixed', icon: FiZap, description: 'Combination of visual and auditory' }
  ]

  const durationOptions = [
    { value: '15-30 minutes', label: '15-30 min', description: 'Quick overview' },
    { value: '30-45 minutes', label: '30-45 min', description: 'Standard lesson' },
    { value: '45-60 minutes', label: '45-60 min', description: 'Comprehensive course' },
    { value: '60+ minutes', label: '60+ min', description: 'In-depth exploration' }
  ]

  return (
    <div className="min-h-screen pt-20 pb-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="text-gradient">AI Teacher</span>
          </h1>
          <p className="text-xl text-dark-text-secondary max-w-2xl mx-auto">
            Generate personalized, interactive presentations with AI-powered teaching
          </p>
        </motion.div>

        {/* Main Form */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-8 mb-8"
        >
          {/* Topic Input */}
          <div className="mb-8">
            <label className="block text-sm font-medium mb-3 text-dark-text">
              What would you like to learn today?
            </label>
            <input
              type="text"
              value={courseConfig.topic}
              onChange={(e) => updateCourseConfig({ topic: e.target.value })}
              placeholder="e.g., Machine Learning Fundamentals, Ancient History, Quantum Physics..."
              className="input-field w-full text-lg py-4"
              disabled={isGenerating}
            />
          </div>

          {/* Quick Settings */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Complexity */}
            <div>
              <label className="block text-sm font-medium mb-3 text-dark-text">
                Complexity Level
              </label>
              <select
                value={courseConfig.complexity}
                onChange={(e) => updateCourseConfig({ complexity: e.target.value })}
                className="input-field w-full"
                disabled={isGenerating}
              >
                {complexityOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Duration */}
            <div>
              <label className="block text-sm font-medium mb-3 text-dark-text">
                Duration
              </label>
              <select
                value={courseConfig.duration}
                onChange={(e) => updateCourseConfig({ duration: e.target.value })}
                className="input-field w-full"
                disabled={isGenerating}
              >
                {durationOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Learning Style */}
            <div>
              <label className="block text-sm font-medium mb-3 text-dark-text">
                Learning Style
              </label>
              <select
                value={courseConfig.learningStyle}
                onChange={(e) => updateCourseConfig({ learningStyle: e.target.value })}
                className="input-field w-full"
                disabled={isGenerating}
              >
                {learningStyleOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Advanced Settings Toggle */}
          <div className="mb-8">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-ios-blue hover:text-blue-400 transition-colors"
              disabled={isGenerating}
            >
              <FiSettings className="w-4 h-4" />
              Advanced Settings
            </button>
          </div>

          {/* Advanced Settings */}
          <AnimatePresence>
            {showAdvanced && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 p-6 bg-dark-card/50 rounded-xl border border-dark-border"
              >
                {/* Slide Count */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Slide Count
                  </label>
                  <select
                    value={courseConfig.slideCount}
                    onChange={(e) => updateCourseConfig({ slideCount: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="auto">Auto (Recommended)</option>
                    <option value="10-15">10-15 slides</option>
                    <option value="15-20">15-20 slides</option>
                    <option value="20-30">20-30 slides</option>
                    <option value="30+">30+ slides</option>
                  </select>
                </div>

                {/* Content Density */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Content Density
                  </label>
                  <select
                    value={courseConfig.contentDensity}
                    onChange={(e) => updateCourseConfig({ contentDensity: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="light">Light (Less content per slide)</option>
                    <option value="medium">Medium (Balanced)</option>
                    <option value="dense">Dense (More content per slide)</option>
                  </select>
                </div>

                {/* Batch Size */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Generation Batch Size
                  </label>
                  <select
                    value={courseConfig.batchSize}
                    onChange={(e) => updateCourseConfig({ batchSize: parseInt(e.target.value) })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="1">1 slide at a time (More detailed)</option>
                    <option value="3">3 slides at a time</option>
                    <option value="5">5 slides at a time (Recommended)</option>
                    <option value="10">10 slides at a time (Faster)</option>
                  </select>
                </div>

                {/* TTS Voice Selection */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    TTS Voice
                  </label>
                  <select
                    value={courseConfig.voice}
                    onChange={(e) => updateCourseConfig({ voice: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="default">Default Voice</option>
                    {availableVoices.map(voice => (
                      <option key={voice.id} value={voice.id}>
                        {voice.name} ({voice.gender || 'Unknown'})
                      </option>
                    ))}
                  </select>
                </div>

                {/* TTS Speed */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Speech Speed
                  </label>
                  <select
                    value={courseConfig.speed}
                    onChange={(e) => updateCourseConfig({ speed: parseFloat(e.target.value) })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="0.5">0.5x (Slower)</option>
                    <option value="0.75">0.75x</option>
                    <option value="1.0">1.0x (Normal)</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x (Faster)</option>
                  </select>
                </div>

                {/* Prerequisites Handling */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Prerequisites Handling
                  </label>
                  <select
                    value={courseConfig.prerequisitesHandling}
                    onChange={(e) => updateCourseConfig({ prerequisitesHandling: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="auto">Auto (Include as needed)</option>
                    <option value="include">Include Basics</option>
                    <option value="skip">Skip Prerequisites</option>
                    <option value="custom">Custom Prerequisites</option>
                  </select>
                </div>

                {/* Specialized Focus */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Focus Area
                  </label>
                  <select
                    value={courseConfig.specializedFocus}
                    onChange={(e) => updateCourseConfig({ specializedFocus: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="balanced">Balanced (Theory + Practice)</option>
                    <option value="theoretical">Theoretical Concepts</option>
                    <option value="practical">Practical Applications</option>
                    <option value="conceptual">Conceptual Understanding</option>
                    <option value="applied">Applied Learning</option>
                  </select>
                </div>

                {/* Presentation Style */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Presentation Style
                  </label>
                  <select
                    value={courseConfig.presentationStyle}
                    onChange={(e) => updateCourseConfig({ presentationStyle: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="professional">Professional</option>
                    <option value="academic">Academic</option>
                    <option value="casual">Casual/Conversational</option>
                    <option value="interactive">Interactive</option>
                  </select>
                </div>

                {/* Visual Style */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Visual Style
                  </label>
                  <select
                    value={courseConfig.visualStyle}
                    onChange={(e) => updateCourseConfig({ visualStyle: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="modern">Modern</option>
                    <option value="classic">Classic</option>
                    <option value="minimal">Minimal</option>
                    <option value="vibrant">Vibrant</option>
                  </select>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Course Templates */}
          <div className="mb-8">
            <button
              onClick={() => setShowTemplates(!showTemplates)}
              className="flex items-center gap-2 text-ios-blue hover:text-blue-400 transition-colors"
              disabled={isGenerating}
            >
              <FiBookOpen className="w-4 h-4" />
              Course Templates
            </button>
          </div>

          <AnimatePresence>
            {showTemplates && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="mb-8 p-6 bg-dark-card/50 rounded-xl border border-dark-border"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {courseTemplates.map(template => (
                    <button
                      key={template.id}
                      onClick={() => {
                        applyTemplate(template)
                        toast.success(`Applied ${template.name} template`)
                        setShowTemplates(false)
                      }}
                      disabled={isGenerating}
                      className="text-left p-4 rounded-lg border border-dark-border hover:border-ios-blue transition-colors"
                    >
                      <h3 className="font-semibold text-ios-blue mb-1">{template.name}</h3>
                      <p className="text-sm text-dark-text-secondary mb-2">{template.description}</p>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="px-2 py-1 rounded bg-ios-blue/10 text-ios-blue">
                          {template.complexity}
                        </span>
                        <span className="px-2 py-1 rounded bg-green-500/10 text-green-400">
                          {template.duration}
                        </span>
                        <span className="px-2 py-1 rounded bg-purple-500/10 text-purple-400">
                          {template.category}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Advanced Presentation Customizations */}
          <div className="mb-8">
            <button
              onClick={() => setShowAdvancedCustomizations(!showAdvancedCustomizations)}
              className="flex items-center gap-2 text-ios-blue hover:text-blue-400 transition-colors"
              disabled={isGenerating}
            >
              <FiSliders className="w-4 h-4" />
              Presentation Customizations
            </button>
          </div>

          <AnimatePresence>
            {showAdvancedCustomizations && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 p-6 bg-dark-card/50 rounded-xl border border-dark-border"
              >
                {/* Theme */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Presentation Theme
                  </label>
                  <select
                    value={courseConfig.theme}
                    onChange={(e) => updateCourseConfig({ theme: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="dark">Dark Theme</option>
                    <option value="light">Light Theme</option>
                    <option value="blue">Blue Theme</option>
                    <option value="green">Green Theme</option>
                    <option value="purple">Purple Theme</option>
                  </select>
                </div>

                {/* Layout */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Slide Layout
                  </label>
                  <select
                    value={courseConfig.layout}
                    onChange={(e) => updateCourseConfig({ layout: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="modern">Modern Layout</option>
                    <option value="classic">Classic Layout</option>
                    <option value="minimal">Minimal Layout</option>
                    <option value="split">Split Layout</option>
                    <option value="full-image">Full Image Layout</option>
                  </select>
                </div>

                {/* Animations */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Slide Animations
                  </label>
                  <select
                    value={courseConfig.animations}
                    onChange={(e) => updateCourseConfig({ animations: e.target.value === 'true' })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="true">Enable Animations</option>
                    <option value="false">Disable Animations</option>
                  </select>
                </div>

                {/* Auto Advance */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Auto Advance
                  </label>
                  <select
                    value={courseConfig.autoAdvance}
                    onChange={(e) => updateCourseConfig({ autoAdvance: e.target.value === 'true' })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="true">Auto Advance Slides</option>
                    <option value="false">Manual Control</option>
                  </select>
                </div>

                {/* Color Scheme */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-dark-text">
                    Color Scheme
                  </label>
                  <select
                    value={courseConfig.colorScheme}
                    onChange={(e) => updateCourseConfig({ colorScheme: e.target.value })}
                    className="input-field w-full"
                    disabled={isGenerating}
                  >
                    <option value="default">Default Colors</option>
                    <option value="high-contrast">High Contrast</option>
                    <option value="warm">Warm Colors</option>
                    <option value="cool">Cool Colors</option>
                    <option value="monochrome">Monochrome</option>
                  </select>
                </div>

                {/* Save Settings Button */}
                <div className="md:col-span-2">
                  <button
                    onClick={() => {
                      saveUserSettings()
                      toast.success('Settings saved!')
                    }}
                    className="btn-secondary w-full"
                    disabled={isGenerating}
                  >
                    Save as Default Settings
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Generate Button */}
          <div className="text-center">
            <button
              onClick={handleStartGeneration}
              disabled={isGenerating || !courseConfig.topic.trim()}
              className="btn-primary text-lg px-8 py-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGenerating ? (
                <div className="flex items-center gap-3">
                  <div className="loading-spinner" />
                  Generating Course...
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <FiPlay className="w-5 h-5" />
                  Generate Course
                </div>
              )}
            </button>
          </div>
        </motion.div>

        {/* Progress Display */}
        <AnimatePresence>
          {isGenerating && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="card p-6 mb-8"
            >
              {/* Connection Status */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-green-500' : 
                    connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                  }`} />
                  <span className="text-sm text-dark-text-secondary">
                    {connectionStatus === 'connected' ? 'Connected' : 
                     connectionStatus === 'error' ? 'Connection Error' : 'Connecting...'}
                  </span>
                </div>
                <div className="text-sm text-dark-text-secondary">
                  {progress}% complete
                </div>
              </div>

              <div className="text-center mb-4">
                <h3 className="text-lg font-semibold mb-2">
                  {currentStep || 'Preparing...'}
                </h3>
                
                {/* Enhanced Progress Information */}
                {enhancedProgress ? (
                  <div className="text-sm text-dark-text-secondary space-y-2">
                    <p className="font-medium">{enhancedProgress.current_stage?.description}</p>
                    
                    {/* Statistics */}
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      {enhancedProgress.statistics?.total_topics > 0 && (
                        <div className="flex items-center gap-1">
                          <span>📚</span>
                          <span>{enhancedProgress.statistics.total_topics} topics</span>
                        </div>
                      )}
                      
                      {enhancedProgress.statistics?.total_slides > 0 && (
                        <div className="flex items-center gap-1">
                          <span>📄</span>
                          <span>{enhancedProgress.statistics.slides_generated}/{enhancedProgress.statistics.total_slides} slides</span>
                        </div>
                      )}
                      
                      {enhancedProgress.statistics?.total_images > 0 && (
                        <div className="flex items-center gap-1">
                          <span>🖼️</span>
                          <span>{enhancedProgress.statistics.images_processed}/{enhancedProgress.statistics.total_images} images</span>
                        </div>
                      )}
                      
                      {enhancedProgress.statistics?.processing_speed && (
                        <div className="flex items-center gap-1">
                          <span>⚡</span>
                          <span>{enhancedProgress.statistics.processing_speed}</span>
                        </div>
                      )}
                    </div>
                    
                    {/* Timing Information */}
                    <div className="text-xs">
                      <div className="flex justify-between">
                        <span>Elapsed: {enhancedProgress.timing?.elapsed_time_formatted}</span>
                        <span>Remaining: {enhancedProgress.timing?.estimated_remaining}</span>
                      </div>
                    </div>
                  </div>
                ) : progressDetails && (
                  <div className="text-sm text-dark-text-secondary space-y-1">
                    {progressDetails.details && (
                      <p>{progressDetails.details}</p>
                    )}
                    
                    {progressDetails.topics_count && (
                      <p>📚 Generated {progressDetails.topics_count} main topics</p>
                    )}
                    
                    {progressDetails.total_slides && (
                      <p>📄 Planning {progressDetails.total_slides} slides</p>
                    )}
                    
                    {progressDetails.current_slide !== undefined && progressDetails.total_slides && (
                      <p>✍️ Slide {progressDetails.current_slide} of {progressDetails.total_slides}</p>
                    )}
                    
                    {progressDetails.current_image !== undefined && progressDetails.total_images && (
                      <p>🖼️ Image {progressDetails.current_image} of {progressDetails.total_images}</p>
                    )}
                  </div>
                )}
                
                {estimatedTime && (
                  <p className="text-dark-text-secondary mt-2">
                    Estimated time remaining: {estimatedTime}
                  </p>
                )}
              </div>
              
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              
              {/* Enhanced Stage Progress Visualization */}
              {enhancedProgress?.stages_summary ? (
                <div className="mt-4 space-y-2">
                  <div className="text-xs font-medium text-dark-text-secondary">Processing Stages</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {enhancedProgress.stages_summary.map((stage, index) => (
                      <div key={stage.id} className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          stage.completed ? 'bg-green-500' : 
                          stage.progress > 0 ? 'bg-blue-500' : 'bg-dark-border'
                        }`} />
                        <span className={`${stage.completed ? 'text-green-400' : 
                          stage.progress > 0 ? 'text-blue-400' : 'text-dark-text-secondary'
                        }`}>
                          {stage.name}
                        </span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Current stage detailed progress */}
                  {enhancedProgress.current_stage?.progress > 0 && enhancedProgress.current_stage?.progress < 100 && (
                    <div className="mt-3">
                      <div className="flex justify-between mb-1 text-xs">
                        <span>{enhancedProgress.current_stage.name}</span>
                        <span>{Math.round(enhancedProgress.current_stage.progress)}%</span>
                      </div>
                      <div className="w-full bg-dark-border rounded-full h-1.5">
                        <div 
                          className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${enhancedProgress.current_stage.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ) : progressDetails && (
                <div className="mt-4 space-y-2">
                  {progressDetails.current_slide !== undefined && progressDetails.total_slides && (
                    <div className="text-xs">
                      <div className="flex justify-between mb-1">
                        <span>Slide Generation</span>
                        <span>{progressDetails.current_slide}/{progressDetails.total_slides}</span>
                      </div>
                      <div className="w-full bg-dark-border rounded-full h-1.5">
                        <div 
                          className="bg-blue-500 h-1.5 rounded-full"
                          style={{ width: `${(progressDetails.current_slide / progressDetails.total_slides) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {progressDetails.current_image !== undefined && progressDetails.total_images && (
                    <div className="text-xs">
                      <div className="flex justify-between mb-1">
                        <span>Image Processing</span>
                        <span>{progressDetails.current_image}/{progressDetails.total_images}</span>
                      </div>
                      <div className="w-full bg-dark-border rounded-full h-1.5">
                        <div 
                          className="bg-purple-500 h-1.5 rounded-full"
                          style={{ width: `${(progressDetails.current_image / progressDetails.total_images) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Quick Actions */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6"
        >
          <button
            onClick={() => navigate('/library')}
            className="card card-hover p-6 text-left"
            disabled={isGenerating}
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-ios-blue/10 rounded-xl flex items-center justify-center">
                <FiBookOpen className="w-6 h-6 text-ios-blue" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Course Library</h3>
                <p className="text-dark-text-secondary">
                  Access your saved courses and presentations
                </p>
              </div>
            </div>
          </button>

          <div className="card p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-ios-accent/10 rounded-xl flex items-center justify-center">
                <FiMic className="w-6 h-6 text-ios-accent" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Voice Interaction</h3>
                <p className="text-dark-text-secondary">
                  Ask questions during presentations
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default HomePage