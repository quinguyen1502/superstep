import { defineConfig } from 'vite'
// The chat widget: one self-contained script at /c/widget.js, built after the app into the same dist/.
export default defineConfig({
  build: {
    outDir: 'dist/c', emptyOutDir: false, copyPublicDir: false,
    lib: { entry: 'src/widget/widget.ts', formats: ['iife'], name: 'SuperstepChat', fileName: () => 'widget.js' },
    // A classic script inherits the host page's encoding when no charset is supplied.
    rolldownOptions: { output: { charset: 'ascii' } },
  },
})
