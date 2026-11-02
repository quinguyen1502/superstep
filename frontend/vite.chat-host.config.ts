import path from 'node:path'
import { createRequire } from 'node:module'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const require = createRequire(import.meta.url)
const root = path.resolve(import.meta.dirname, '../examples/chat-host')
export default defineConfig({
  root,
  plugins: [react(), tailwindcss()],
  resolve: { alias: [
    { find: '@', replacement: path.resolve(import.meta.dirname, 'src') },
    { find: '@superstep/sdk', replacement: path.resolve(import.meta.dirname, '../sdk/typescript/dist/esm/index.js') },
    { find: 'lucide-react', replacement: path.resolve(import.meta.dirname, '../node_modules/lucide-react/dist/esm/lucide-react.mjs') },
    ...['react/jsx-runtime', 'react-dom/client', 'react', 'react-i18next'].map(name => ({ find: new RegExp(`^${name.replace('/', '\\/')}$`), replacement: require.resolve(name) })),
  ], dedupe: ['react', 'react-dom', 'i18next'] },
  build: { outDir: path.join(root, 'dist'), emptyOutDir: true, rolldownOptions: { output: { codeSplitting: { groups: [
    { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
    { name: 'vendor-ui', test: /node_modules[\\/](radix-ui|@radix-ui|@floating-ui)[\\/]/ },
    { name: 'vendor-i18n', test: /node_modules[\\/](i18next|react-i18next|i18next-browser-languagedetector)[\\/]/ },
  ] } } } },
})
