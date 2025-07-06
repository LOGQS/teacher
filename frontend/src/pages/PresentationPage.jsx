import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FiPlay, 
  FiPause, 
  FiSkipBack, 
  FiSkipForward,
  FiMic,
  FiMicOff,
  FiVolumeX,
  FiVolume2,
  FiX,
  FiRepeat,
  FiRotateCcw,
  FiHome,
  FiMessageCircle
} from 'react-icons/fi'
import { useAppStore } from '../store/appStore'
import { courseAPI, conversationAPI, audioAPI } from '../api/client'
import { toast } from 'react-hot-toast'
import MessageRenderer from '../components/MessageRenderer'

const PresentationPage = () => {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  
  const {
    currentCourse,
    setCurrentCourse,
    currentSlide,
    setCurrentSlide,
    isPlaying,
    setPlaying,
    audioProgress,
    setAudioProgress,
    isConversationActive,
    setConversationActive,
    conversationHistory,
    addConversationMessage,
    clearConversationHistory,
    nextSlide,
    previousSlide,
    hasNextSlide,
    hasPreviousSlide,
    getCurrentSlideData,
    userSettings,
    loadUserSettings,
    loadAvailableVoices
  } = useAppStore()
  
  const [loading, setLoading] = useState(true)
  const [isRecording, setIsRecording] = useState(false)
  const [audioMuted, setAudioMuted] = useState(false)
  const [conversationSession, setConversationSession] = useState(null)
  const [pausedPosition, setPausedPosition] = useState(0)
  const [showResumeOptions, setShowResumeOptions] = useState(false)
  const [slideImages, setSlideImages] = useState([])
  const [loadingImages, setLoadingImages] = useState(false)
  const [isAISpeaking, setIsAISpeaking] = useState(false)
  const [manuallyResumed, setManuallyResumed] = useState(false)
  
  const audioRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const aiAudioRef = useRef(null)
  
  useEffect(() => {
    loadCourse()
    loadUserSettings()
    loadAvailableVoices()
  }, [sessionId])
  
  useEffect(() => {
    // Auto-start TTS after 1 second when slide changes, but NOT if resume modal is showing or manually resumed
    if (currentCourse && !isConversationActive && !showResumeOptions && !manuallyResumed) {
      const timer = setTimeout(() => {
        startSlideAudio()
      }, 1000)
      
      return () => clearTimeout(timer)
    }
  }, [currentSlide, currentCourse, isConversationActive, showResumeOptions, manuallyResumed])
  
  const loadCourse = async () => {
    try {
      setLoading(true)
      console.log(`Loading course with session ID: ${sessionId}`)
      const response = await courseAPI.getCourse(sessionId)
      console.log('Course loaded successfully:', response.data)
      setCurrentCourse(response.data)
      setCurrentSlide(0)
      
      // Log course info for debugging
      const courseData = response.data
      console.log(`Course: ${courseData.course_title}`)
      console.log(`Slides: ${courseData.slides_content?.length || 0}`)
      console.log(`Audio files: ${courseData.audio_files?.length || 0}`)
      console.log('Audio files:', courseData.audio_files)
      
      // Load slide images
      await loadSlideImages()
      
    } catch (error) {
      console.error('Failed to load course:', error)
      toast.error('Failed to load course')
      navigate('/')
    } finally {
      setLoading(false)
    }
  }
  
  const loadSlideImages = async () => {
    try {
      setLoadingImages(true)
      console.log(`Loading slide images for session: ${sessionId}`)
      
      // Use the courseAPI to ensure consistent API configuration
      const response = await courseAPI.getCourseSlides(sessionId)
      console.log('Slide images loaded:', response.data)
      setSlideImages(response.data.slide_images || [])
      
    } catch (error) {
      console.error('Failed to load slide images:', error)
      
      // If it's a newly generated course, the images might need to be generated
      if (error.response?.status === 404 || error.message.includes('not found')) {
        console.log('Course slides not found - might be a newly generated course')
        toast.info('Generating slide images... This may take a moment.')
        
        // Try again after a short delay to allow backend to process
        setTimeout(async () => {
          try {
            const retryResponse = await courseAPI.getCourseSlides(sessionId)
            console.log('Slide images loaded on retry:', retryResponse.data)
            setSlideImages(retryResponse.data.slide_images || [])
            toast.success('Slide images generated successfully!')
          } catch (retryError) {
            console.error('Failed to load slide images on retry:', retryError)
            toast.error('Failed to generate slide images')
            setSlideImages([])
          }
        }, 3000) // Wait 3 seconds before retry
      } else {
        // Don't show error toast for other errors - fall back to JSON content display
        setSlideImages([])
      }
    } finally {
      setLoadingImages(false)
    }
  }
  
  const startSlideAudio = async (overridePosition = null) => {
    try {
      const slideData = getCurrentSlideData()
      console.log('[Audio] Current slide data:', slideData)
      console.log('[Audio] Slide transcript:', slideData?.transcript)
      console.log('[Audio] Available audio files:', currentCourse?.audio_files)
      console.log('[Audio] Current slide index:', currentSlide)
      
      if (!slideData?.transcript) {
        console.log('[Audio] No transcript available for current slide')
        return
      }
      
      // Try to use pre-generated audio first
      let audioLoadedSuccessfully = false
      
      if (currentCourse.audio_files && currentCourse.audio_files[currentSlide]) {
        const audioFile = currentCourse.audio_files[currentSlide]
        if (audioFile && audioRef.current) {
          console.log(`Loading pre-generated audio: ${audioFile}`)
          
          try {
            // Use pre-generated audio file
            audioRef.current.src = `/api/audio/file/${encodeURIComponent(audioFile)}`
            audioRef.current.currentTime = overridePosition !== null ? overridePosition : pausedPosition
            
            // Set up event listeners for audio
            audioRef.current.onloadstart = () => {
              console.log('Audio loading started')
            }
            
            audioRef.current.oncanplay = () => {
              console.log('Audio can start playing')
            }
            
            audioRef.current.onended = () => {
              console.log('Audio ended, moving to next slide')
              setPlaying(false)
              setPausedPosition(0)
              // Auto-advance to next slide when audio completes
              if (hasNextSlide()) {
                setTimeout(() => {
                  nextSlide()
                }, 1000) // 1 second delay before advancing
              }
            }
            
            audioRef.current.ontimeupdate = () => {
              if (audioRef.current) {
                const progress = (audioRef.current.currentTime / audioRef.current.duration) * 100
                setAudioProgress(progress || 0)
              }
            }
            
            audioRef.current.onerror = (e) => {
              console.error('Pre-generated audio error:', e)
              // Don't show error toast here, let it fall back to real-time generation
            }
            
            await audioRef.current.play()
            setPlaying(true)
            console.log('Audio started playing')
            audioLoadedSuccessfully = true
            
          } catch (playError) {
            console.error('Error playing pre-generated audio:', playError)
            // Don't show error toast here, let it fall back to real-time generation
          }
        }
      }
      
      // Only fall back to real-time TTS if pre-generated audio failed
      if (!audioLoadedSuccessfully) {
        try {
          console.log('Falling back to real-time TTS generation')
          const audioResponse = await audioAPI.generateAudio(slideData, {
            voice: 'default',
            speed: 1.0
          })
          
          if (audioRef.current && audioResponse.data) {
            // The response should be a blob or audio file
            const audioUrl = URL.createObjectURL(audioResponse.data)
            audioRef.current.src = audioUrl
            audioRef.current.currentTime = overridePosition !== null ? overridePosition : pausedPosition
            
            // Set up the same event listeners for generated audio
            audioRef.current.onended = () => {
              setPlaying(false)
              setPausedPosition(0)
              if (hasNextSlide()) {
                setTimeout(() => {
                  nextSlide()
                }, 1000)
              }
            }
            
            audioRef.current.ontimeupdate = () => {
              if (audioRef.current) {
                const progress = (audioRef.current.currentTime / audioRef.current.duration) * 100
                setAudioProgress(progress || 0)
              }
            }
            
            await audioRef.current.play()
            setPlaying(true)
            console.log('Real-time TTS audio started playing')
          }
        } catch (realtimeError) {
          console.error('Real-time TTS generation failed:', realtimeError)
          toast.error('Audio playback temporarily unavailable')
        }
      }
      
    } catch (error) {
      console.error('Audio error:', error)
      toast.error('Failed to play audio')
    }
  }
  
  const pauseAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      setPausedPosition(audioRef.current.currentTime)
      setPlaying(false)
    }
  }
  
  const togglePlayPause = () => {
    if (isPlaying) {
      pauseAudio()
    } else {
      startSlideAudio()
    }
  }
  
  const handleSlideChange = (direction) => {
    // Clean up current audio
    pauseAudio()
    setPausedPosition(0) // Reset audio position for new slide
    setAudioProgress(0) // Reset progress bar
    setManuallyResumed(false) // Reset manual resume flag for new slide
    
    // Remove event listeners to prevent memory leaks
    if (audioRef.current) {
      audioRef.current.onended = null
      audioRef.current.ontimeupdate = null
      audioRef.current.onerror = null
      audioRef.current.onloadstart = null
      audioRef.current.oncanplay = null
    }
    
    if (direction === 'next' && hasNextSlide()) {
      nextSlide()
    } else if (direction === 'prev' && hasPreviousSlide()) {
      previousSlide()
    }
  }
  
  const startConversation = async () => {
    try {
      // Pause audio and save position
      if (isPlaying && audioRef.current) {
        audioRef.current.pause()
        setPausedPosition(audioRef.current.currentTime)
        setPlaying(false)
      }
      
      // Start conversation session
      const slideData = getCurrentSlideData()
      const slideImageUrl = getCurrentSlideImageUrl()
      
      const response = await conversationAPI.startConversation(sessionId, {
        slide_number: currentSlide + 1,
        transcript: slideData?.transcript || '',
        slide_image_url: slideImageUrl
      })
      
      setConversationSession(response.data.conversation_session_id)
      setConversationActive(true)
      
      // Don't start recording automatically - wait for user to press mic button
      
    } catch (error) {
      toast.error('Failed to start conversation')
      console.error('Conversation error:', error)
    }
  }
  
  const endConversation = async () => {
    try {
      // Stop recording if active
      if (isRecording) {
        if (mediaRecorderRef.current) {
          mediaRecorderRef.current.stop()
          setIsRecording(false)
        }
      }
      
      // Stop AI speaking if active
      stopAISpeech()
      
      // End conversation session
      if (conversationSession) {
        await conversationAPI.endConversation(conversationSession)
      }
      
      setConversationActive(false)
      setConversationSession(null)
      
      // Only show resume options if we actually paused audio
      if (pausedPosition > 0) {
        setShowResumeOptions(true)
      }
      
    } catch (error) {
      toast.error('Failed to end conversation')
      console.error('End conversation error:', error)
    }
  }
  
  const toggleRecording = async () => {
    if (isRecording) {
      // Stop recording
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop()
        setIsRecording(false)
      }
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaRecorderRef.current = new MediaRecorder(stream)
        audioChunksRef.current = []
        
        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data)
        }
        
        mediaRecorderRef.current.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
          await processRecording(audioBlob)
          
          // Stop all tracks
          stream.getTracks().forEach(track => track.stop())
        }
        
        mediaRecorderRef.current.start()
        setIsRecording(true)
        
      } catch (error) {
        toast.error('Failed to access microphone')
        console.error('Recording error:', error)
      }
    }
  }
  
  const processRecording = async (audioBlob) => {
    try {
      // Transcribe audio
      const transcriptionResponse = await audioAPI.transcribeAudio(audioBlob)
      
      // Handle different response formats
      let transcriptionText = ''
      if (transcriptionResponse.data) {
        transcriptionText = transcriptionResponse.data.transcription || 
                           transcriptionResponse.data.text || 
                           transcriptionResponse.data
      }
      
      if (transcriptionText && transcriptionText.trim()) {
        // Add user question to conversation
        addConversationMessage({
          role: 'user',
          content: transcriptionText,
          timestamp: new Date().toISOString()
        })
        
        // Get AI response
        const slideData = getCurrentSlideData()
        const slideImageUrl = getCurrentSlideImageUrl()
        
        const response = await conversationAPI.askQuestion(
          conversationSession,
          transcriptionText,
          {
            transcript: slideData?.transcript || '',
            slide_number: currentSlide + 1,
            slide_image_url: slideImageUrl
          }
        )
        
        const aiResponseText = response.data.response || response.data.answer
        
        // Add AI response to conversation
        addConversationMessage({
          role: 'teacher',
          content: aiResponseText,
          timestamp: new Date().toISOString()
        })
        
        // Generate and play TTS for AI response
        await speakAIResponse(aiResponseText)
        
      } else {
        // No speech detected
        toast('No speech detected. Please try again.', { icon: '🎤' })
      }
      
    } catch (error) {
      toast.error('Failed to process recording')
      console.error('Processing error:', error)
    }
  }
  
  const stopAISpeech = () => {
    if (aiAudioRef.current) {
      aiAudioRef.current.pause()
      aiAudioRef.current.currentTime = 0
      setIsAISpeaking(false)
      aiAudioRef.current = null
    }
  }
  
  const speakAIResponse = async (responseText) => {
    try {
      // Stop any existing AI speech
      stopAISpeech()
      
      setIsAISpeaking(true)
      
      // Create a temporary slide data object for TTS
      const tempSlideData = {
        transcript: responseText,
        title: 'AI Response'
      }
      
      const audioResponse = await audioAPI.generateAudio(tempSlideData, {
        voice: userSettings.tts.voice,
        speed: userSettings.tts.speed
      })
      
      // The audio API returns a blob response directly
      if (audioResponse && audioResponse.data) {
        // Check if response.data is already a Blob
        let audioBlob
        if (audioResponse.data instanceof Blob) {
          audioBlob = audioResponse.data
        } else {
          // If it's not a blob, try to create one from the response
          audioBlob = new Blob([audioResponse.data], { type: 'audio/wav' })
        }
        
        const audioUrl = URL.createObjectURL(audioBlob)
        const aiAudio = new Audio(audioUrl)
        
        // Store reference for stopping
        aiAudioRef.current = aiAudio
        
        // Apply user settings
        aiAudio.volume = userSettings.tts.volume
        
        aiAudio.onended = () => {
          setIsAISpeaking(false)
          URL.revokeObjectURL(audioUrl)
          aiAudioRef.current = null
        }
        
        aiAudio.onerror = (e) => {
          console.error('Audio playback error:', e)
          setIsAISpeaking(false)
          URL.revokeObjectURL(audioUrl)
          aiAudioRef.current = null
        }
        
        await aiAudio.play()
      } else {
        console.error('No audio data received from API')
        setIsAISpeaking(false)
      }
      
    } catch (error) {
      console.error('Failed to synthesize AI response:', error)
      setIsAISpeaking(false)
      // Don't show error toast - AI response is still visible as text
    }
  }
  
  const getCurrentSlideImageUrl = () => {
    // Use existing slide images from backend
    if (slideImages.length > 0 && slideImages[currentSlide]) {
      return slideImages[currentSlide].image_url
    }
    return null
  }
  
  const resumeAudio = (fromBeginning = false) => {
    setShowResumeOptions(false)
    setManuallyResumed(true) // Prevent auto-start from triggering
    
    if (fromBeginning) {
      setPausedPosition(0)
      startSlideAudio(0) // Pass 0 directly to override position
    } else {
      startSlideAudio() // Use current pausedPosition
    }
  }
  
  const slideData = getCurrentSlideData()
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="text-center">
          <div className="loading-spinner w-8 h-8 border-ios-blue mx-auto mb-4" />
          <p className="text-dark-text-secondary">Loading presentation...</p>
        </div>
      </div>
    )
  }
  
  if (!currentCourse) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Course not found</h2>
          <button onClick={() => navigate('/')} className="btn-primary">
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-bg relative overflow-hidden">
      {/* Background Audio Element */}
      <audio
        ref={audioRef}
        muted={audioMuted}
      />
      
      {/* Main Slide Content */}
      <div className="flex flex-col h-screen">
        {/* Slide Display Area */}
        <div className="flex-1 flex items-center justify-center p-8">
          <motion.div
            key={currentSlide}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
            className="max-w-6xl w-full bg-dark-card rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Display actual slide image if available */}
            {slideImages.length > 0 && slideImages[currentSlide] ? (
              <div className="relative w-full h-full flex items-center justify-center">
                <img
                  src={slideImages[currentSlide].image_url}
                  alt={`Slide ${currentSlide + 1}`}
                  className="max-w-full max-h-full object-contain rounded-lg"
                  onError={(e) => {
                    console.error('Failed to load slide image:', e)
                    // Hide the image on error and show fallback
                    e.target.style.display = 'none'
                  }}
                />
                {loadingImages && (
                  <div className="absolute inset-0 flex items-center justify-center bg-dark-bg/50">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ios-blue mx-auto mb-2"></div>
                      <p className="text-sm text-dark-text-secondary">Loading slide...</p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Fallback: Display reconstructed content from JSON */
              slideData && (
                <div className="p-12">
                  {/* Slide Title */}
                  {slideData.title && (
                    <h1 className="text-4xl font-bold mb-8 text-center">
                      {slideData.title}
                    </h1>
                  )}
                  
                  {/* Slide Content */}
                  <div className="space-y-6">
                    {slideData.content && (
                      <div className="text-lg leading-relaxed">
                        {Array.isArray(slideData.content) ? (
                          <ul className="list-disc list-inside space-y-2">
                            {slideData.content.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>{slideData.content}</p>
                        )}
                      </div>
                    )}
                    
                    {/* Slide Images */}
                    {slideData.images && slideData.images.length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
                        {slideData.images.map((image, idx) => (
                          <div key={idx} className="text-center">
                            <div className="bg-dark-border rounded-lg p-8 mb-2">
                              <div className="text-dark-text-secondary">
                                📷 {image.description || `Image ${idx + 1}`}
                              </div>
                            </div>
                            {image.caption && (
                              <p className="text-sm text-dark-text-secondary italic">
                                {image.caption}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* Show message if no slide images are available */}
                  {slideImages.length === 0 && !loadingImages && (
                    <div className="text-center mt-8 p-4 bg-dark-border rounded-lg">
                      <p className="text-dark-text-secondary">
                        📄 Displaying slide content (slide images not available)
                      </p>
                    </div>
                  )}
                </div>
              )
            )}
          </motion.div>
        </div>
        
        {/* Audio Progress Bar */}
        <div className="px-8 pb-4">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${audioProgress}%` }}
            />
          </div>
        </div>
        
        {/* Controls */}
        <div className="bg-dark-card border-t border-dark-border p-6">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            {/* Left Controls */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="p-3 rounded-lg hover:bg-dark-border transition-colors"
              >
                <FiHome className="w-5 h-5" />
              </button>
              
              <div className="text-sm text-dark-text-secondary">
                Slide {currentSlide + 1} of {slideImages.length > 0 ? slideImages.length : (currentCourse.slides_content?.length || 0)}
              </div>
            </div>
            
            {/* Center Controls */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => handleSlideChange('prev')}
                disabled={!hasPreviousSlide()}
                className="p-3 rounded-lg hover:bg-dark-border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FiSkipBack className="w-5 h-5" />
              </button>
              
              <button
                onClick={togglePlayPause}
                className="p-4 bg-ios-blue hover:bg-blue-600 rounded-full transition-colors"
              >
                {isPlaying ? (
                  <FiPause className="w-6 h-6 text-white" />
                ) : (
                  <FiPlay className="w-6 h-6 text-white" />
                )}
              </button>
              
              <button
                onClick={() => handleSlideChange('next')}
                disabled={!hasNextSlide()}
                className="p-3 rounded-lg hover:bg-dark-border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FiSkipForward className="w-5 h-5" />
              </button>
            </div>
            
            {/* Right Controls */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => setAudioMuted(!audioMuted)}
                className="p-3 rounded-lg hover:bg-dark-border transition-colors"
              >
                {audioMuted ? (
                  <FiVolumeX className="w-5 h-5" />
                ) : (
                  <FiVolume2 className="w-5 h-5" />
                )}
              </button>
              
              <button
                onClick={isConversationActive ? endConversation : startConversation}
                className={`p-3 rounded-lg transition-colors ${
                  isConversationActive 
                    ? 'bg-ios-destructive hover:bg-red-600 text-white' 
                    : 'bg-ios-accent hover:bg-green-600 text-white'
                }`}
              >
                {isConversationActive ? (
                  <FiX className="w-5 h-5" />
                ) : (
                  <FiMessageCircle className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Conversation Panel */}
      <AnimatePresence>
        {isConversationActive && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25 }}
            className="fixed top-0 right-0 w-96 h-full bg-dark-card border-l border-dark-border shadow-2xl z-50"
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-dark-border">
                <div className="flex items-center gap-2">
                  <FiMessageCircle className="w-5 h-5 text-ios-blue" />
                  <h3 className="font-semibold">Ask Questions</h3>
                </div>
                <button
                  onClick={endConversation}
                  className="p-2 rounded-lg hover:bg-dark-border transition-colors"
                >
                  <FiX className="w-4 h-4" />
                </button>
              </div>
              
              {/* Conversation History */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {conversationHistory.length === 0 ? (
                  <div className="text-center text-dark-text-secondary py-8">
                    <FiMic className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Press the mic button below to ask a question</p>
                  </div>
                ) : (
                  conversationHistory.map((message, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg ${
                        message.role === 'user' 
                          ? 'bg-ios-blue text-white ml-4' 
                          : 'bg-dark-border mr-4'
                      }`}
                    >
                      <div className="text-sm opacity-75 mb-1 flex items-center gap-2">
                        {message.role === 'user' ? 'You' : 'AI Teacher'}
                        {message.role === 'teacher' && isAISpeaking && (
                          <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-ios-accent rounded-full animate-pulse" />
                            <span className="text-xs">Speaking...</span>
                          </div>
                        )}
                      </div>
                      {message.role === 'user' ? (
                        <div>{message.content}</div>
                      ) : (
                        <MessageRenderer 
                          content={message.content} 
                          className="text-sm"
                        />
                      )}
                    </div>
                  ))
                )}
              </div>
              
              {/* Controls Section */}
              <div className="border-t border-dark-border">
                {/* Recording Indicator */}
                {isRecording && (
                  <div className="p-4 bg-ios-destructive/10">
                    <div className="flex items-center gap-2 text-ios-destructive">
                      <div className="w-3 h-3 bg-ios-destructive rounded-full animate-pulse" />
                      <span className="text-sm font-medium">Recording... Release to send</span>
                    </div>
                  </div>
                )}
                
                {/* AI Speaking Indicator */}
                {isAISpeaking && (
                  <button 
                    onClick={stopAISpeech}
                    className="w-full p-4 bg-ios-accent/10 hover:bg-ios-accent/20 transition-colors cursor-pointer border-none text-left"
                  >
                    <div className="flex items-center gap-2 text-ios-accent">
                      <FiVolume2 className="w-4 h-4" />
                      <span className="text-sm font-medium">AI Teacher is speaking... (click to stop)</span>
                    </div>
                  </button>
                )}
                
                {/* Action Buttons */}
                <div className="p-4 space-y-3">
                  {/* Mic Button */}
                  <button
                    onClick={toggleRecording}
                    disabled={isAISpeaking}
                    className={`w-full p-3 rounded-lg transition-colors font-medium ${
                      isRecording 
                        ? 'bg-ios-destructive hover:bg-red-600 text-white'
                        : isAISpeaking
                        ? 'bg-dark-border text-dark-text-secondary cursor-not-allowed'
                        : 'bg-ios-accent hover:bg-green-600 text-white'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      {isRecording ? (
                        <>
                          <FiMicOff className="w-4 h-4" />
                          Click to Stop Recording
                        </>
                      ) : isAISpeaking ? (
                        <>
                          <FiVolume2 className="w-4 h-4" />
                          AI Speaking...
                        </>
                      ) : (
                        <>
                          <FiMic className="w-4 h-4" />
                          Click to Ask Question
                        </>
                      )}
                    </div>
                  </button>
                  
                  {/* Resume Presentation Button */}
                  {pausedPosition > 0 && (
                    <button
                      onClick={endConversation}
                      className="w-full p-2 rounded-lg bg-ios-blue/10 text-ios-blue hover:bg-ios-blue/20 transition-colors text-sm"
                    >
                      <div className="flex items-center justify-center gap-2">
                        <FiPlay className="w-3 h-3" />
                        Resume Presentation
                      </div>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Resume Options Modal */}
      <AnimatePresence>
        {showResumeOptions && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-dark-bg/80 backdrop-blur-sm z-50 flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="card p-8 max-w-md w-full mx-4"
            >
              <h3 className="text-xl font-semibold mb-4 text-center">Resume Audio</h3>
              <p className="text-dark-text-secondary mb-6 text-center">
                How would you like to continue?
              </p>
              
              <div className="space-y-3">
                <button
                  onClick={() => resumeAudio(false)}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  <FiPlay className="w-4 h-4" />
                  Continue from where I left off
                </button>
                
                <button
                  onClick={() => resumeAudio(true)}
                  className="btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <FiRotateCcw className="w-4 h-4" />
                  Restart from beginning
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default PresentationPage