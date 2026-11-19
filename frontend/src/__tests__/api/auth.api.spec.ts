import { describe, it, expect, vi, beforeEach } from 'vitest'
import { httpClient } from '@/api/http'
import { getProfile, login, logout, refreshToken, register } from '@/api/auth.api'

vi.mock('@/api/http', () => ({
  httpClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls GET /api/v1/users/profile for getProfile', async () => {
    const user = {
      id: 1,
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Smith',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    }
    vi.mocked(httpClient.get).mockResolvedValueOnce({ data: user })

    const result = await getProfile()

    expect(httpClient.get).toHaveBeenCalledWith('/api/v1/users/profile')
    expect(httpClient.post).not.toHaveBeenCalled()
    expect(result).toEqual(user)
  })

  it('calls POST endpoints for register, login, refreshToken, and logout', async () => {
    vi.mocked(httpClient.post).mockResolvedValue({ data: {} })

    await register({
      email: 'a@b.com',
      password: 'secret',
      first_name: 'A',
      last_name: 'B',
    })
    await login({ email: 'a@b.com', password: 'secret' })
    await refreshToken({ refresh_token: 'ref' })
    await logout({ refresh_token: 'ref' })

    expect(httpClient.post).toHaveBeenNthCalledWith(1, '/api/v1/users/register', {
      email: 'a@b.com',
      password: 'secret',
      first_name: 'A',
      last_name: 'B',
    })
    expect(httpClient.post).toHaveBeenNthCalledWith(2, '/api/v1/users/login', {
      email: 'a@b.com',
      password: 'secret',
    })
    expect(httpClient.post).toHaveBeenNthCalledWith(3, '/api/v1/users/refresh-token', {
      refresh_token: 'ref',
    })
    expect(httpClient.post).toHaveBeenNthCalledWith(4, '/api/v1/users/logout', {
      refresh_token: 'ref',
    })
  })
})
