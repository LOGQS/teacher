import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FiX, 
  FiVolume2, 
  FiSpeaker, 
  FiMonitor,
  FiEye,
  FiPlay,
  FiSave
} from 'react-icons/fi'
import { useAppStore } from '../store/appStore'
import { toast } from 'react-hot-toast'

const SettingsModal = ({ isOpen, onClose }) => {
  const {
    userSettings,
    updateUserSettings,
    saveUserSettings,
    availableVoices,
    loadAvailableVoices
  } = useAppStore()
  
  const [localSettings, setLocalSettings] = useState(userSettings)
  const [isSaving, setIsSaving] = useState(false)
  
  useEffect(() => {
    if (isOpen) {
      setLocalSettings(userSettings)
      loadAvailableVoices()
    }
  }, [isOpen, userSettings, loadAvailableVoices])
  
  useEffect(() => {
    console.log('Available voices in settings:', availableVoices)
  }, [availableVoices])
  
  const handleSave = async () => {
    try {
      setIsSaving(true)
      updateUserSettings(localSettings)
      await saveUserSettings()
      toast.success('Settings saved successfully!')
      onClose()
    } catch (error) {
      toast.error('Failed to save settings')
      console.error('Settings save error:', error)
    } finally {
      setIsSaving(false)
    }
  }
  
  const updateSetting = (path, value) => {
    setLocalSettings(prev => {
      const newSettings = { ...prev }
      const keys = path.split('.')
      let current = newSettings
      
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]]
      }
      current[keys[keys.length - 1]] = value
      
      return newSettings
    })
  }
  
  const testVoice = async (voice) => {
    try {
      // Create a test audio with the selected voice
      const testText = "This is how this voice sounds."
      const tempSlideData = {
        transcript: testText,
        title: 'Voice Test'
      }
      
      const { audioAPI } = await import('../api/client')
      const audioResponse = await audioAPI.generateAudio(tempSlideData, {
        voice: voice,
        speed: localSettings.tts.speed
      })
      
      if (audioResponse && audioResponse.data) {
        const audioBlob = audioResponse.data instanceof Blob 
          ? audioResponse.data 
          : new Blob([audioResponse.data], { type: 'audio/wav' })
        
        const audioUrl = URL.createObjectURL(audioBlob)
        const audio = new Audio(audioUrl)
        
        audio.onended = () => URL.revokeObjectURL(audioUrl)
        audio.onerror = () => URL.revokeObjectURL(audioUrl)
        
        await audio.play()
        toast.success('Voice test played!')
      }
    } catch (error) {
      toast.error('Failed to test voice')
      console.error('Voice test error:', error)
    }
  }
  
  if (!isOpen) return null
  
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-dark-bg/80 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: -20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: -20 }}
          className="bg-dark-card rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden relative"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-dark-border">
            <h2 className="text-2xl font-bold flex items-center gap-3">
              <FiMonitor className="w-6 h-6 text-ios-blue" />
              Settings
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-dark-border transition-colors"
            >
              <FiX className="w-5 h-5" />
            </button>
          </div>
          
          {/* Content */}
          <div className="p-6 space-y-8 overflow-y-auto max-h-[60vh]">
            {/* TTS Settings */}
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <FiVolume2 className="w-5 h-5 text-ios-blue" />
                <h3 className="text-xl font-semibold">Text-to-Speech</h3>
              </div>
              
              {/* Voice Selection */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Voice
                </label>
                <select
                  value={localSettings.tts.voice}
                  onChange={(e) => updateSetting('tts.voice', e.target.value)}
                  className="w-full p-3 bg-dark-border rounded-lg border border-dark-border focus:border-ios-blue focus:outline-none transition-colors"
                >
                  <option value="default">Default</option>
                  {availableVoices.length === 0 && (
                    <option disabled>Loading voices...</option>
                  )}
                  {availableVoices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} {voice.gender && voice.gender !== 'unknown' && `(${voice.gender})`}
                    </option>
                  ))}
                </select>
                
                {availableVoices.length === 0 && (
                  <p className="text-sm text-yellow-600 mt-1">
                    ⚠️ No TTS voices found. Check backend TTS configuration.
                  </p>
                )}
                
                {/* Test Voice Button */}
                <button
                  onClick={() => testVoice(localSettings.tts.voice)}
                  className="flex items-center gap-2 px-4 py-2 bg-ios-blue/10 text-ios-blue rounded-lg hover:bg-ios-blue/20 transition-colors"
                >
                  <FiPlay className="w-4 h-4" />
                  Test Voice
                </button>
              </div>
              
              {/* Speed Control */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Speech Speed: {localSettings.tts.speed}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={localSettings.tts.speed}
                  onChange={(e) => updateSetting('tts.speed', parseFloat(e.target.value))}
                  className="w-full h-2 bg-dark-border rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs text-dark-text-secondary">
                  <span>0.5x (Slow)</span>
                  <span>1.0x (Normal)</span>
                  <span>2.0x (Fast)</span>
                </div>
              </div>
              
              {/* Volume Control */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Volume: {Math.round(localSettings.tts.volume * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={localSettings.tts.volume}
                  onChange={(e) => updateSetting('tts.volume', parseFloat(e.target.value))}
                  className="w-full h-2 bg-dark-border rounded-lg appearance-none cursor-pointer slider"
                />
              </div>
            </div>
            
            {/* Presentation Settings */}
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <FiEye className="w-5 h-5 text-ios-blue" />
                <h3 className="text-xl font-semibold">Presentation</h3>
              </div>
              
              {/* Theme */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Theme
                </label>
                <select
                  value={localSettings.presentation.theme}
                  onChange={(e) => updateSetting('presentation.theme', e.target.value)}
                  className="w-full p-3 bg-dark-border rounded-lg border border-dark-border focus:border-ios-blue focus:outline-none transition-colors"
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                  <option value="auto">Auto</option>
                </select>
              </div>
              
              {/* Auto Advance */}
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-dark-text-secondary">
                    Auto-advance slides
                  </label>
                  <p className="text-xs text-dark-text-secondary">
                    Automatically move to next slide when audio ends
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.presentation.auto_advance}
                  onChange={(e) => updateSetting('presentation.auto_advance', e.target.checked)}
                  className="w-5 h-5 text-ios-blue bg-dark-border border-dark-border rounded focus:ring-ios-blue"
                />
              </div>
              
              {/* Animations */}
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-dark-text-secondary">
                    Enable animations
                  </label>
                  <p className="text-xs text-dark-text-secondary">
                    Show smooth transitions between slides
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.presentation.animations}
                  onChange={(e) => updateSetting('presentation.animations', e.target.checked)}
                  className="w-5 h-5 text-ios-blue bg-dark-border border-dark-border rounded focus:ring-ios-blue"
                />
              </div>
            </div>
            
            {/* Course Defaults */}
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <FiSpeaker className="w-5 h-5 text-ios-blue" />
                <h3 className="text-xl font-semibold">Course Defaults</h3>
              </div>
              
              {/* Complexity */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Default Complexity
                </label>
                <select
                  value={localSettings.course_defaults.complexity}
                  onChange={(e) => updateSetting('course_defaults.complexity', e.target.value)}
                  className="w-full p-3 bg-dark-border rounded-lg border border-dark-border focus:border-ios-blue focus:outline-none transition-colors"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              
              {/* Duration */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-dark-text-secondary">
                  Default Duration
                </label>
                <select
                  value={localSettings.course_defaults.duration}
                  onChange={(e) => updateSetting('course_defaults.duration', e.target.value)}
                  className="w-full p-3 bg-dark-border rounded-lg border border-dark-border focus:border-ios-blue focus:outline-none transition-colors"
                >
                  <option value="15-30 minutes">15-30 minutes</option>
                  <option value="30-45 minutes">30-45 minutes</option>
                  <option value="45-60 minutes">45-60 minutes</option>
                  <option value="60+ minutes">60+ minutes</option>
                </select>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="flex justify-end gap-3 p-6 border-t border-dark-border">
            <button
              onClick={onClose}
              className="px-6 py-2 text-dark-text-secondary hover:text-dark-text transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-6 py-2 bg-ios-blue hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <FiSave className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default SettingsModal