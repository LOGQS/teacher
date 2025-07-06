import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { motion } from 'framer-motion'
import HomePage from './pages/HomePage'
import PresentationPage from './pages/PresentationPage'
import LibraryPage from './pages/LibraryPage'
import Navigation from './components/Navigation'
import SettingsModal from './components/SettingsModal'
import { useAppStore } from './store/appStore'

function App() {
  const { isGenerating } = useAppStore()
  const [showSettings, setShowSettings] = useState(false)

  return (
    <Router>
      <div className="min-h-screen bg-dark-bg text-dark-text">
        {/* Background gradient */}
        <div className="fixed inset-0 bg-gradient-to-br from-dark-bg via-dark-bg to-dark-card opacity-50 -z-10" />
        
        {/* Navigation */}
        <Navigation onOpenSettings={() => setShowSettings(true)} />
        
        {/* Main content */}
        <main className="relative z-10">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/presentation/:sessionId" element={<PresentationPage />} />
            <Route path="/library" element={<LibraryPage />} />
          </Routes>
        </main>
        
        {/* Settings Modal - rendered at App level for proper positioning */}
        <SettingsModal 
          isOpen={showSettings} 
          onClose={() => setShowSettings(false)} 
        />
        
      </div>
    </Router>
  )
}

export default App