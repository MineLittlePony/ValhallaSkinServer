import VuePlugin from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    VuePlugin(),
    UnoCSS(),
  ],
  appType: 'mpa',
  build: {
    reportCompressedSize: true,
    sourcemap: true,
  },
  server: {
    proxy: Object.fromEntries(['/api', '/__debug__', '/textures'].map(key => [
      key,
      { target: 'http://localhost:8000', xfwd: true },
    ])),
  },
})
