import { createRequire } from 'node:module'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
const require = createRequire(import.meta.url)
const compat = process.env.REACT_COMPAT_ROOT
const alias = compat ? ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'react-dom/client'].map(name => ({ find: new RegExp(`^${name.replaceAll('/', '\\/')}$`), replacement: require.resolve(name, { paths: [compat] }) })) : []
export default defineConfig({ root: import.meta.dirname, plugins: [react()], resolve: { alias, dedupe: ['react', 'react-dom', 'i18next', 'react-i18next'] }, build: { outDir: 'dist', emptyOutDir: true } })
