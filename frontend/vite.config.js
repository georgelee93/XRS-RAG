import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, 'public/index.html'),
        admin: resolve(__dirname, 'public/admin.html'),
        chat: resolve(__dirname, 'public/chat.html'),
        login: resolve(__dirname, 'public/login.html'),
        signup: resolve(__dirname, 'public/signup.html'),
      },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  resolve: {
    alias: {
      '/src': resolve(__dirname, './src'),
    },
  },
})