import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/api/auth.api'
import type {
  UserEntity,
  UserLoginRequest,
  UserLoginResponse,
  UserRegisterRequest,
} from '@/types/auth.types'

const STORAGE_KEYS = {
  access: 'auth_access_token',
  refresh: 'auth_refresh_token',
  user: 'auth_user',
} as const

function loadStoredUser(): UserEntity | null {
  const raw = localStorage.getItem(STORAGE_KEYS.user)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserEntity
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(STORAGE_KEYS.access))
  const refreshToken = ref<string | null>(localStorage.getItem(STORAGE_KEYS.refresh))
  const user = ref<UserEntity | null>(loadStoredUser())
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  function applySession(response: UserLoginResponse): void {
    accessToken.value = response.token.access
    refreshToken.value = response.token.refresh
    user.value = response.user

    localStorage.setItem(STORAGE_KEYS.access, response.token.access)
    localStorage.setItem(STORAGE_KEYS.refresh, response.token.refresh)
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(response.user))
  }

  function clearSession(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    localStorage.removeItem(STORAGE_KEYS.access)
    localStorage.removeItem(STORAGE_KEYS.refresh)
    localStorage.removeItem(STORAGE_KEYS.user)
  }

  async function register(payload: UserRegisterRequest): Promise<UserEntity> {
    loading.value = true
    try {
      return await authApi.register(payload)
    } finally {
      loading.value = false
    }
  }

  async function login(payload: UserLoginRequest): Promise<UserLoginResponse> {
    loading.value = true
    try {
      const response = await authApi.login(payload)
      applySession(response)
      return response
    } finally {
      loading.value = false
    }
  }

  async function refresh(): Promise<UserLoginResponse> {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }
    loading.value = true
    try {
      const response = await authApi.refreshToken({ refresh_token: refreshToken.value })
      applySession(response)
      return response
    } finally {
      loading.value = false
    }
  }

  async function fetchProfile(): Promise<UserEntity> {
    loading.value = true
    try {
      const profile = await authApi.getProfile()
      user.value = profile
      localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(profile))
      return profile
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    const tokenToRevoke = refreshToken.value
    try {
      if (tokenToRevoke) {
        await authApi.logout({ refresh_token: tokenToRevoke })
      }
    } catch {
      // Clear local session regardless of server revocation errors
    } finally {
      clearSession()
    }
  }

  return {
    accessToken,
    refreshToken,
    user,
    loading,
    isAuthenticated,
    applySession,
    clearSession,
    register,
    login,
    refresh,
    fetchProfile,
    logout,
  }
})
