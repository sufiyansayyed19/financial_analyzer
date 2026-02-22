import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    // Vite 7 uses Lightning CSS by default, which doesn't support
    // @tailwind directives. Force PostCSS for Tailwind v3 compatibility.
    transformer: 'postcss',
  },
})
