import { create } from 'zustand'

export const useAppStore = create((set, get) => ({
  // UI State
  isGenerating: false,
  currentStep: null,
  progress: 0,
  
  // Course Generation State
  courseConfig: {
    topic: '',
    complexity: 'intermediate',
    duration: '45-60 minutes',
    learningStyle: 'visual',
    slideCount: 'auto',
    contentDensity: 'medium',
    batchSize: 5,
    voice: 'default',
    speed: 1.0,
    
    // Missing customizations from full_app_description
    prerequisitesHandling: 'auto',
    specializedFocus: 'balanced',
    presentationStyle: 'professional',
    visualStyle: 'modern',
    colorScheme: 'default',
    
    // Advanced presentation settings
    theme: 'dark',
    layout: 'modern',
    animations: true,
    autoAdvance: true,
    
    customizations: {}
  },
  
  // User Settings
  userSettings: {
    tts: {
      voice: 'default',
      speed: 1.0,
      volume: 0.8
    },
    presentation: {
      theme: 'dark',
      layout: 'modern',
      animations: true,
      auto_advance: true
    },
    course_defaults: {
      complexity: 'intermediate',
      duration: '45-60 minutes',
      learning_style: 'visual',
      content_density: 'medium',
      batch_size: 5
    },
    advanced: {
      prerequisites_handling: 'auto',
      specialized_focus: 'balanced',
      presentation_style: 'professional'
    }
  },
  
  // Available options
  availableVoices: [],
  courseTemplates: [],
  
  // Current Session
  currentSession: null,
  currentCourse: null,
  
  // Library
  courses: [],
  
  // Presentation State
  currentSlide: 0,
  isPlaying: false,
  audioProgress: 0,
  
  // Conversation State
  isConversationActive: false,
  conversationHistory: [],
  
  // Actions
  setGenerating: (generating) => set({ isGenerating: generating }),
  
  setProgress: (progress, step) => set({ 
    progress,
    currentStep: step 
  }),
  
  updateCourseConfig: (config) => set((state) => ({
    courseConfig: { ...state.courseConfig, ...config }
  })),
  
  setCurrentSession: (session) => set({ currentSession: session }),
  
  setCurrentCourse: (course) => set({ currentCourse: course }),
  
  setCourses: (courses) => set({ courses }),
  
  addCourse: (course) => set((state) => ({
    courses: [course, ...state.courses]
  })),
  
  removeCourse: (sessionId) => set((state) => ({
    courses: state.courses.filter(course => course.session_id !== sessionId)
  })),
  
  // Presentation Actions
  setCurrentSlide: (slide) => set({ currentSlide: slide }),
  
  setPlaying: (playing) => set({ isPlaying: playing }),
  
  setAudioProgress: (progress) => set({ audioProgress: progress }),
  
  nextSlide: () => set((state) => {
    const maxSlide = state.currentCourse?.slides_content?.length - 1 || 0
    return {
      currentSlide: Math.min(state.currentSlide + 1, maxSlide)
    }
  }),
  
  previousSlide: () => set((state) => ({
    currentSlide: Math.max(state.currentSlide - 1, 0)
  })),
  
  // Conversation Actions
  setConversationActive: (active) => set({ isConversationActive: active }),
  
  addConversationMessage: (message) => set((state) => ({
    conversationHistory: [...state.conversationHistory, message]
  })),
  
  clearConversationHistory: () => set({ conversationHistory: [] }),
  
  // Settings Actions
  setUserSettings: (settings) => set({ userSettings: settings }),
  
  updateUserSettings: (settingsUpdate) => set((state) => ({
    userSettings: { ...state.userSettings, ...settingsUpdate }
  })),
  
  setAvailableVoices: (voices) => set({ availableVoices: voices }),
  
  setCourseTemplates: (templates) => set({ courseTemplates: templates }),
  
  // Apply template to course config
  applyTemplate: (template) => set((state) => ({
    courseConfig: {
      ...state.courseConfig,
      complexity: template.complexity,
      duration: template.duration,
      prerequisitesHandling: template.prerequisites.length > 0 ? 'custom' : 'auto',
      specializedFocus: template.focus_areas.includes('theoretical') ? 'theoretical' : 
                       template.focus_areas.includes('practical') ? 'practical' : 'balanced'
    }
  })),
  
  // Load settings from backend and apply them
  loadUserSettings: async () => {
    const state = get()
    try {
      const { settingsAPI } = await import('../api/client')
      const response = await settingsAPI.getSettings()
      const settings = response.data
      
      // Update user settings
      state.setUserSettings(settings)
      
      // Apply settings to course config defaults
      state.updateCourseConfig({
        complexity: settings.course_defaults.complexity,
        duration: settings.course_defaults.duration,
        learningStyle: settings.course_defaults.learning_style,
        contentDensity: settings.course_defaults.content_density,
        batchSize: settings.course_defaults.batch_size,
        voice: settings.tts.voice,
        speed: settings.tts.speed,
        theme: settings.presentation.theme,
        layout: settings.presentation.layout,
        animations: settings.presentation.animations,
        autoAdvance: settings.presentation.auto_advance,
        prerequisitesHandling: settings.advanced.prerequisites_handling,
        specializedFocus: settings.advanced.specialized_focus,
        presentationStyle: settings.advanced.presentation_style
      })
    } catch (error) {
      console.error('Failed to load user settings:', error)
    }
  },
  
  // Save settings to backend
  saveUserSettings: async () => {
    const state = get()
    try {
      const { settingsAPI } = await import('../api/client')
      await settingsAPI.saveSettings(state.userSettings)
    } catch (error) {
      console.error('Failed to save user settings:', error)
    }
  },
  
  // Load available voices
  loadAvailableVoices: async () => {
    const state = get()
    try {
      const { audioAPI } = await import('../api/client')
      const response = await audioAPI.getVoices()
      console.log('TTS voices API response:', response.data)
      const voices = response.data.voices || []
      console.log('Setting available voices:', voices)
      state.setAvailableVoices(voices)
    } catch (error) {
      console.error('Failed to load TTS voices:', error)
    }
  },
  
  // Load course templates
  loadCourseTemplates: async () => {
    const state = get()
    try {
      const { templatesAPI } = await import('../api/client')
      const response = await templatesAPI.getCourseTemplates()
      state.setCourseTemplates(response.data.templates || [])
    } catch (error) {
      console.error('Failed to load course templates:', error)
    }
  },
  
  // Reset functions
  resetCourseGeneration: () => set({
    isGenerating: false,
    currentStep: null,
    progress: 0,
    currentSession: null,
    currentCourse: null
  }),
  
  resetPresentation: () => set({
    currentSlide: 0,
    isPlaying: false,
    audioProgress: 0,
    isConversationActive: false,
    conversationHistory: []
  }),
  
  // Utility functions
  getCurrentSlideData: () => {
    const state = get()
    if (!state.currentCourse?.slides_content) return null
    return state.currentCourse.slides_content[state.currentSlide] || null
  },
  
  hasNextSlide: () => {
    const state = get()
    const maxSlide = state.currentCourse?.slides_content?.length - 1 || 0
    return state.currentSlide < maxSlide
  },
  
  hasPreviousSlide: () => {
    const state = get()
    return state.currentSlide > 0
  }
}))