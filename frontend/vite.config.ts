import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3900,
    // Required when nginx proxies with Host: peace-keeper.app (Vite blocks unknown hosts by default)
    allowedHosts: [
      'peace-keeper.app',
      'www.peace-keeper.app',
      'localhost',
      '192.168.68.59',
    ],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
