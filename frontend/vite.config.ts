import path from 'path'
import { build, defineConfig, type Plugin } from 'vite'
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
/** Dev only (TASK-0143): /c/widget.js from its source, and a chat page's frame-ancestors from the API, as nginx and the
 *  all-in-one image do in production. */
const chatEmbed = (): Plugin => ({
  name: 'chat-embed',
  configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const url = req.url || ''
      if (url.split('?')[0] === '/c/widget.js') {   // a classic script, as the production build makes it
        const out = await build({ configFile: path.resolve(__dirname, 'vite.widget.config.ts'), build: { write: false }, logLevel: 'silent' })
        const chunk = (Array.isArray(out) ? out[0] : out as { output: { code?: string }[] }).output[0]
        res.setHeader('Content-Type', 'text/javascript'); res.end(chunk.code ?? ''); return
      }
      if (/^\/c\/[a-z0-9-]+\/?(\?|$)/.test(url)) {
        try {
          const r = await fetch(`http://${API}/api/public/chat-frame`, { headers: { 'X-Original-URI': url } })
          res.setHeader('Content-Security-Policy', r.headers.get('content-security-policy') || "frame-ancestors 'none'")
        } catch { res.setHeader('Content-Security-Policy', "frame-ancestors 'none'") }
      }
      next()
    })
  },
})
export default defineConfig({
  plugins: [react(), tailwindcss(), chatEmbed()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: { rolldownOptions: { output: { advancedChunks: { groups: VENDOR } } } },
  server: { host: '0.0.0.0', port: Number(process.env.STUDIO_UI_PORT || 5173), proxy: {
    '/api': `http://${API}`,
    '/mcp': `http://${API}`,
    '/ws': { target: `ws://${API}`, ws: true },
  } },
})
