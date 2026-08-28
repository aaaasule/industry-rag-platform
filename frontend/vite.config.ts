import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  optimizeDeps: {
    include: ['react-pdf', 'pdfjs-dist'],
  },
  server: {
    port: 5173,
    // 走代理而非 CORS：开发与生产（同源部署在 Nginx 后）的请求路径保持一致，
    // 避免出现"本地好用、上线 404"的路径差异
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE / 长连接：避免代理缓冲，问答流式才能边到边渲染
        timeout: 0,
        proxyTimeout: 0,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const ct = proxyRes.headers['content-type'] ?? '';
            if (String(ct).includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache';
              proxyRes.headers['x-accel-buffering'] = 'no';
              // Node http 默认可能缓冲；禁用 content-length 以便分块转发
              delete proxyRes.headers['content-length'];
            }
          });
        },
      },
    },
  },
});
