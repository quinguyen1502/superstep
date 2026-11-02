import { createRoot } from 'react-dom/client'
import { App } from './app'

// The headless store owns disposal; toolkit hooks and their StrictMode lifecycle are a later task.
createRoot(document.getElementById('root')!).render(<App />)
