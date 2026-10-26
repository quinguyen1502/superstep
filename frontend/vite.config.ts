import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
const API = `127.0.0.1:${process.env.STUDIO_API_PORT || 8000}`
// Large libraries get their own chunks, so the app code can change without busting them and no chunk passes 500 kB (TASK-0043).
const VENDOR = [
  { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|scheduler|react-router|react-router-dom)[\\/]/ },
  { name: 'vendor-codemirror', test: /node_modules[\\/](@codemirror|@lezer|@uiw|style-mod|w3c-keyname|crelt)[\\/]/ },
  { name: 'vendor-flow', test: /node_modules[\\/](@xyflow|d3-[a-z-]+|zustand|classcat)[\\/]/ },
  { name: 'vendor-ui', test: /node_modules[\\/](radix-ui|@radix-ui|@floating-ui|cmdk|react-resizable-panels)[\\/]/ },
  { name: 'vendor-i18n', test: /node_modules[\\/](i18next|react-i18next|i18next-browser-languagedetector)[\\/]/ },
]
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: { rolldownOptions: { output: { advancedChunks: { groups: VENDOR } } } },
  server: { host: '0.0.0.0', port: Number(process.env.STUDIO_UI_PORT || 5173), proxy: {
    '/api': `http://${API}`,
    '/mcp': `http://${API}`,
    '/ws': { target: `ws://${API}`, ws: true },
  } },
})
