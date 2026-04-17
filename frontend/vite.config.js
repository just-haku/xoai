import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        port: 3080,
        host: true,
        allowedHosts: ['xoai.haku.io.vn'],
        proxy: {
            '/api': {
                target: 'http://xoai-backend:8080',
                changeOrigin: true
            },
            '/ws': {
                target: 'http://xoai-backend:8080',
                ws: true
            }
        },
        hmr: {
            host: 'xoai.haku.io.vn',
            clientPort: 443
        }
    }
})
