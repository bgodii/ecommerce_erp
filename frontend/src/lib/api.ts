import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const baseURL = (import.meta.env.VITE_API_URL as string) || '/api'

export const api = axios.create({ baseURL })

const ACCESS = 'erp_access'
const REFRESH = 'erp_refresh'

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS)
  },
  get refresh() {
    return localStorage.getItem(REFRESH)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS, access)
    localStorage.setItem(REFRESH, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS)
    localStorage.removeItem(REFRESH)
  },
}

api.interceptors.request.use((cfg) => {
  const t = tokens.access
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

let refreshing: Promise<string | null> | null = null

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    const config = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const status = err.response?.status
    const isAuthCall = config?.url?.includes('/auth/')
    if (status === 401 && config && !config._retry && tokens.refresh && !isAuthCall) {
      config._retry = true
      if (!refreshing) {
        refreshing = axios
          .post(`${baseURL}/auth/refresh`, { refresh_token: tokens.refresh })
          .then((res) => {
            tokens.set(res.data.access_token, res.data.refresh_token)
            return res.data.access_token as string
          })
          .catch(() => {
            tokens.clear()
            return null
          })
          .finally(() => {
            refreshing = null
          })
      }
      const newToken = await refreshing
      if (newToken) {
        config.headers.Authorization = `Bearer ${newToken}`
        return api(config)
      }
    }
    return Promise.reject(err)
  },
)

export function apiError(err: unknown, fallback = 'Ocorreu um erro'): string {
  const e = err as AxiosError<{ detail?: string | { msg: string }[] }>
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) return detail[0].msg
  return fallback
}
