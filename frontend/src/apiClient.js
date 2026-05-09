// 知枢前端：双 baseURL 接入层（P1）。
//
// 两种运行模式：
//   1) 单体（默认）：VITE_CLOUD_API 为空 → 所有请求 same-origin，行为与改造前一致
//   2) 云本机分离：VITE_CLOUD_API 设置后启用
//      - /api/auth/*、/api/admin/invites → 改写到云端 /api/cloud/*
//      - 其它 /api/*  → 走本机 agent（VITE_LOCAL_API；不设则也是 same-origin）
//      - JWT access token 通过 Authorization: Bearer 头携带，自动 refresh
//
// 设计原则（参《工程控制论》原则 9 反馈、原则 12 稳定优先）：
//   - 单体模式不引入任何额外行为，保证回滚路径
//   - 401 时一次自动 refresh，失败再上抛，避免静默死循环
//   - token 存 localStorage（P1 阶段）；P2 移到 httpOnly cookie 由云端下发

const CLOUD_BASE = (import.meta.env.VITE_CLOUD_API || '').replace(/\/+$/, '')
const LOCAL_BASE = (import.meta.env.VITE_LOCAL_API || '').replace(/\/+$/, '')
export const SPLIT_MODE_ENABLED = !!CLOUD_BASE

const ACCESS_KEY = 'mjq.access_token'
const REFRESH_KEY = 'mjq.refresh_token'

export function getAccessToken() {
  try { return localStorage.getItem(ACCESS_KEY) || '' } catch { return '' }
}
export function getRefreshToken() {
  try { return localStorage.getItem(REFRESH_KEY) || '' } catch { return '' }
}
export function setAccessToken(t) {
  try { if (t) localStorage.setItem(ACCESS_KEY, t) } catch {}
}
export function setRefreshToken(t) {
  try { if (t) localStorage.setItem(REFRESH_KEY, t) } catch {}
}
export function persistTokensFromResponse(data) {
  if (!data) return
  if (data.access_token) setAccessToken(data.access_token)
  if (data.refresh_token) setRefreshToken(data.refresh_token)
}
export function clearTokens() {
  try {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  } catch {}
}

function rewriteCloudPath(path) {
  // 旧接口路径 → 新云端路径的对照表（P1 仅认证相关迁云）
  if (path.startsWith('/api/auth/')) {
    return path.replace('/api/auth/', '/api/cloud/auth/')
  }
  if (path.startsWith('/api/admin/invites')) {
    return path.replace('/api/admin/invites', '/api/cloud/admin/invites')
  }
  return path
}

function isCloudPath(path) {
  return (
    path.startsWith('/api/auth/') ||
    path.startsWith('/api/admin/invites') ||
    path.startsWith('/api/cloud/')
  )
}

function resolveUrl(path) {
  if (!SPLIT_MODE_ENABLED) return path
  if (isCloudPath(path)) {
    const rewritten = path.startsWith('/api/cloud/') ? path : rewriteCloudPath(path)
    return CLOUD_BASE + rewritten
  }
  return (LOCAL_BASE || '') + path
}

let _refreshing = null
async function tryRefresh() {
  if (!SPLIT_MODE_ENABLED) return false
  const refresh = getRefreshToken()
  if (!refresh) return false
  if (_refreshing) return _refreshing  // 同一时刻只允许一个 refresh 请求
  _refreshing = (async () => {
    try {
      const res = await fetch(CLOUD_BASE + '/api/cloud/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (!res.ok) return false
      const data = await res.json()
      if (data.access_token) {
        setAccessToken(data.access_token)
        return true
      }
      return false
    } catch {
      return false
    } finally {
      // 留 50ms 让并发请求拿到结果
      setTimeout(() => { _refreshing = null }, 50)
    }
  })()
  return _refreshing
}

export async function apiFetch(path, options = {}) {
  const url = resolveUrl(path)
  const headers = { ...(options.headers || {}) }

  if (SPLIT_MODE_ENABLED) {
    const token = getAccessToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const fetchOpts = {
    ...options,
    headers,
    // 单体模式继续用 cookie session；分离模式跨域用 JWT，不带 cookie
    credentials: SPLIT_MODE_ENABLED ? 'omit' : 'same-origin',
  }

  let response = await fetch(url, fetchOpts)

  // 401 自动 refresh 一次
  if (response.status === 401 && SPLIT_MODE_ENABLED && getRefreshToken() && !path.startsWith('/api/cloud/auth/')) {
    const ok = await tryRefresh()
    if (ok) {
      const newToken = getAccessToken()
      if (newToken) headers['Authorization'] = `Bearer ${newToken}`
      response = await fetch(url, { ...fetchOpts, headers })
    }
  }

  return response
}
