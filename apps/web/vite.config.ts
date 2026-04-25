import { defineConfig, loadEnv } from 'vite'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Plugin } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** Прокси GET /{localpart}/deeplink на API (тот же хост, что и /api). */
function iterDeeplinkProxyPlugin(apiBase: string): Plugin {
  return {
    name: 'iter-deeplink-proxy',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const raw = req.url?.split('?')[0] ?? ''
        if (req.method && req.method !== 'GET' && req.method !== 'HEAD') return next()
        if (!/^\/[^/]+\/deeplink$/.test(raw)) return next()
        const target = new URL(apiBase)
        const opts: http.RequestOptions = {
          hostname: target.hostname,
          port: target.port || (target.protocol === 'https:' ? 443 : 80),
          path: req.url,
          method: req.method,
          headers: { ...req.headers, host: target.host },
        }
        const pReq = http.request(opts, (pRes) => {
          res.writeHead(
            pRes.statusCode ?? 502,
            pRes.headers as Record<string, number | string | string[] | undefined>,
          )
          pRes.pipe(res)
        })
        pReq.on('error', () => {
          res.statusCode = 502
          res.end()
        })
        pReq.end()
      })
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const apiProxy =
    env.VITE_API_PROXY ||
    process.env.VITE_API_PROXY ||
    'http://127.0.0.1:8010'

  return {
    server: {
      fs: {
        allow: [path.resolve(__dirname, '../..')],
      },
      proxy: {
        '/api': {
          // 8010: на Windows :8000 иногда даёт WinError 10013 (занят / excluded port range)
          target: apiProxy,
          changeOrigin: true,
          // Без таймаута при выключенном API браузер может висеть на «Отправка…» очень долго
          timeout: 20_000,
          proxyTimeout: 20_000,
        },
        '/config': {
          target: apiProxy,
          changeOrigin: true,
          timeout: 60_000,
          proxyTimeout: 60_000,
        },
        '/health': {
          target: apiProxy,
          changeOrigin: true,
          timeout: 20_000,
          proxyTimeout: 20_000,
        },
      },
    },
    plugins: [react(), tailwindcss(), iterDeeplinkProxyPlugin(apiProxy)],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@brand': path.resolve(__dirname, '../../assets/brand'),
      },
    },

    // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
    assetsInclude: ['**/*.svg', '**/*.csv'],
  }
})
