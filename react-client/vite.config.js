import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { getServerConfig } from './src/utils/config'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  //const env = loadEnv(mode, '.', '')
  const config = getServerConfig()

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: config.API_URL || 'http://127.0.0.1:5001',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/serve-file': {
          target: config.API_URL || 'http://127.0.0.1:5001', // Ensure it points to Flask
          changeOrigin: true,
        }
      }
    }
  }
})
