const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

/** 拼接 API 路径。未设置 VITE_API_BASE_URL 时使用同域相对路径（配合 Vercel/Netlify 反代）。 */
export function apiUrl(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return API_BASE ? `${API_BASE}${normalized}` : normalized
}

/** 解析后端静态资源或相对 URL，供 img src / fetch 使用。 */
export function resolveAssetUrl(url) {
  if (!url || /^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
    return url
  }
  return apiUrl(url.startsWith('/') ? url : `/${url}`)
}
