import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiHome, FiBookOpen, FiSettings } from 'react-icons/fi'

const Navigation = ({ onOpenSettings }) => {
  const location = useLocation()
  
  const navItems = [
    { path: '/', icon: FiHome, label: 'Home' },
    { path: '/library', icon: FiBookOpen, label: 'Library' },
  ]
  
  return (
    <motion.nav 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="fixed top-0 left-0 right-0 z-50 bg-dark-bg/80 backdrop-blur-lg border-b border-dark-border"
    >
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-ios-blue to-ios-accent rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <span className="font-bold text-xl text-dark-text">Teacher</span>
          </Link>
          
          {/* Navigation Items */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                    isActive 
                      ? 'bg-ios-blue text-white' 
                      : 'text-dark-text-secondary hover:text-dark-text hover:bg-dark-card'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="font-medium">{item.label}</span>
                  
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute inset-0 bg-ios-blue rounded-lg -z-10"
                      transition={{ type: "spring", duration: 0.5 }}
                    />
                  )}
                </Link>
              )
            })}
          </div>
          
          {/* Settings Button */}
          <button 
            onClick={onOpenSettings}
            className="p-2 rounded-lg text-dark-text-secondary hover:text-dark-text hover:bg-dark-card transition-colors"
          >
            <FiSettings className="w-5 h-5" />
          </button>
        </div>
      </div>
    </motion.nav>
  )
}

export default Navigation