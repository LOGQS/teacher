import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { Toaster } from 'react-hot-toast'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster 
      position="top-center"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#1A1A1B',
          color: '#E8E8E8',
          border: '1px solid #2A2A2B',
        },
        success: {
          iconTheme: {
            primary: '#34C759',
            secondary: '#1A1A1B',
          },
        },
        error: {
          iconTheme: {
            primary: '#FF3B30',
            secondary: '#1A1A1B',
          },
        },
      }}
    />
  </React.StrictMode>,
)