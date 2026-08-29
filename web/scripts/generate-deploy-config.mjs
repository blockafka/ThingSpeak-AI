#!/usr/bin/env node
/**
 * 根据 BACKEND_URL 生成 Vercel / Netlify 的 API 反向代理配置。
 * 构建前自动执行（package.json prebuild）。
 *
 * 用法：
 *   BACKEND_URL=https://your-api.example.com npm run build
 *
 * 若不设置 BACKEND_URL，则仅输出 SPA 配置；此时可改用 VITE_API_BASE_URL 直连后端。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const webRoot = path.resolve(__dirname, '..')
const repoRoot = path.resolve(webRoot, '..')

const backend = (
  process.env.BACKEND_URL ||
  process.env.VITE_API_BASE_URL ||
  'https://wuyan-ai.vercel.app'
).replace(/\/$/, '')

const vercelConfig = {
  $schema: 'https://openapi.vercel.sh/vercel.json',
  rewrites: [],
}

if (backend) {
  vercelConfig.rewrites.push(
    { source: '/api/:path*', destination: `${backend}/api/:path*` },
    { source: '/static/:path*', destination: `${backend}/static/:path*` },
  )
  console.log(`[deploy-config] Vercel API proxy -> ${backend}`)
} else {
  console.log('[deploy-config] 未配置后端地址，跳过 API 反代')
}

fs.writeFileSync(
  path.join(webRoot, 'vercel.json'),
  `${JSON.stringify(vercelConfig, null, 2)}\n`,
)

const netlifyLines = [
  '[build]',
  '  base = "web"',
  '  command = "npm run build"',
  '  publish = "dist"',
  '',
]

if (backend) {
  netlifyLines.push(
    '[[redirects]]',
    '  from = "/api/*"',
    `  to = "${backend}/api/:splat"`,
    '  status = 200',
    '  force = true',
    '',
    '[[redirects]]',
    '  from = "/static/*"',
    `  to = "${backend}/static/:splat"`,
    '  status = 200',
    '  force = true',
    '',
  )
  console.log(`[deploy-config] Netlify API proxy -> ${backend}`)
}

fs.writeFileSync(path.join(repoRoot, 'netlify.toml'), `${netlifyLines.join('\n')}\n`)
