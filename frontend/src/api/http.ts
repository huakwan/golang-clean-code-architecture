import axios, {
  type AxiosAdapter,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { UserLoginResponse } from '@/types/auth.types'

export interface HttpAuthBridge {
  getAccessToken: () => string | null
  getRefreshToken: () => string | null
  onTokensRefreshed: (response: UserLoginResponse) => void
  onAuthFailure: () => void
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const SKIP_REFRESH_PATHS = [
  '/api/v1/users/login',
  '/api/v1/users/register',
  '/api/v1/users/refresh-token',
]

export function createHttpClient(
  baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  adapter?: AxiosAdapter,
): AxiosInstance {
  return axios.create({
    baseURL,
    headers: { 'Content-Type': 'application/json' },
    ...(adapter ? { adapter } : {}),
  })
}

export function configureHttpAuth(client: AxiosInstance, bridge: HttpAuthBridge): void {
  let refreshPromise: Promise<string> | null = null

  client.interceptors.request.use((config) => {
    const token = bridge.getAccessToken()
    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error?.config as RetryableRequestConfig | undefined
      const status = error?.response?.status
      const requestUrl = originalRequest?.url ?? ''
      const shouldSkipRefresh = SKIP_REFRESH_PATHS.some((path) => requestUrl.includes(path))

      if (status !== 401 || !originalRequest || originalRequest._retry || shouldSkipRefresh) {
        return Promise.reject(error)
      }

      const refreshToken = bridge.getRefreshToken()
      if (!refreshToken) {
        bridge.onAuthFailure()
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        if (!refreshPromise) {
          const base = (client.defaults.baseURL ?? '').replace(/\/+$/, '')
          refreshPromise = axios
            .post<UserLoginResponse>(
              `${base}/api/v1/users/refresh-token`,
              { refresh_token: refreshToken },
              { headers: { 'Content-Type': 'application/json' } },
            )
            .then((res) => {
              bridge.onTokensRefreshed(res.data)
              return res.data.token.access
            })
            .finally(() => {
              refreshPromise = null
            })
        }

        const newAccessToken = await refreshPromise
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return client(originalRequest)
      } catch (refreshError) {
        bridge.onAuthFailure()
        return Promise.reject(refreshError)
      }
    },
  )
}

export const httpClient = createHttpClient()
