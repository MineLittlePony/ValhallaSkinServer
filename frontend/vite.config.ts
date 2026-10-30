import preact from '@preact/preset-vite'
import UnoCSS from 'unocss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    preact(),
    UnoCSS(),
  ],
  appType: 'mpa',
  server: {
    proxy: Object.fromEntries(['/api', '/__debug__', '/textures'].map(key => [
      key,
      { target: 'http://localhost:8000', xfwd: true },
    ])),

  },
})
