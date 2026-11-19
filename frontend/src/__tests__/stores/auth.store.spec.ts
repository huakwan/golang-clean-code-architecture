import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'
import * as authApi from '@/api/auth.api'
import type { UserEntity, UserLoginResponse } from '@/types/auth.types'

vi.mock('@/api/auth.api')

const sampleUser: UserEntity = {
  id: 1,
  email: 'dev@example.com',
  first_name: 'Dev',
  last_name: 'User',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const sampleLoginResponse: UserLoginResponse = {
  user: sampleUser,
  token: {
    access: 'access-123',
    refresh: 'refresh-456',
  },
}

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('persists user and tokens on login', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(sampleLoginResponse)

    const store = useAuthStore()
    await store.login({ email: 'dev@example.com', password: 'secret' })

    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual(sampleUser)
    expect(store.accessToken).toBe('access-123')
    expect(store.refreshToken).toBe('refresh-456')
    expect(localStorage.getItem('auth_access_token')).toBe('access-123')
    expect(localStorage.getItem('auth_refresh_token')).toBe('refresh-456')
  })

  it('updates access token on refresh', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(sampleLoginResponse)
    vi.mocked(authApi.refreshToken).mockResolvedValueOnce({
      user: sampleUser,
      token: { access: 'access-new', refresh: 'refresh-456' },
    })

    const store = useAuthStore()
    await store.login({ email: 'dev@example.com', password: 'secret' })
    await store.refresh()

    expect(store.accessToken).toBe('access-new')
    expect(localStorage.getItem('auth_access_token')).toBe('access-new')
  })

  it('clears state and storage on logout even if API fails', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(sampleLoginResponse)
    vi.mocked(authApi.logout).mockRejectedValueOnce(new Error('network error'))

    const store = useAuthStore()
    await store.login({ email: 'dev@example.com', password: 'secret' })
    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.refreshToken).toBeNull()
    expect(localStorage.getItem('auth_access_token')).toBeNull()
  })
})
