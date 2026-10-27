import { defineConfig } from 'vite'
// The chat widget (TASK-0143): one self-contained script at /c/widget.js, built after the app into the same dist/.
export default defineConfig({
  build: {
    outDir: 'dist/c', emptyOutDir: false, copyPublicDir: false,
    lib: { entry: 'src/widget/widget.ts', formats: ['iife'], name: 'SuperstepChat', fileName: () => 'widget.js' },
  },
})
