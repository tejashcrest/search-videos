import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'
import runtimeConfig from './config/runtimeConfig.js'

// Preload configuration before rendering React app
console.log('🚀 Initializing application...');

runtimeConfig.load()
  .then(() => {
    console.log('✓ Configuration loaded successfully');
    console.log('🎯 Starting React application...');
    
    // Render React app after configuration is loaded
    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </React.StrictMode>,
    );
  })
  .catch((error) => {
    console.error('❌ Failed to load configuration:', error.message);
    console.log('⚠️ Starting app anyway - API calls will handle configuration loading');
    
    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </React.StrictMode>,
    );
  });
