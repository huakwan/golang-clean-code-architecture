import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios, { type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { createHttpClient, configureHttpAuth } from '@/api/http'
import type { UserLoginResponse } from '@/types/auth.types'

describe('http client & 401 refresh interceptor', () => {
  const mockLoginResponse: UserLoginResponse = {
    user: {
      id: 1,
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Smith',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    token: {
      access: 'new-access-token',
      refresh: 'same-refresh-token',
    },
  }

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('attaches Authorization Bearer header when access token exists', async () => {
    let capturedAuthHeader: unknown = null
    const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
      capturedAuthHeader = config.headers?.Authorization
      return {
        data: { ok: true },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }

    const client = createHttpClient('http://localhost:8000', adapter)
    configureHttpAuth(client, {
      getAccessToken: () => 'my-access-token',
      getRefreshToken: () => 'my-refresh-token',
      onTokensRefreshed: vi.fn(),
      onAuthFailure: vi.fn(),
    })

    const res = await client.get('/api/v1/users/profile')
    expect(res.data).toEqual({ ok: true })
    expect(capturedAuthHeader).toBe('Bearer my-access-token')
  })

  it('refreshes token on 401 and retries the original request once', async () => {
    let currentAccess = 'expired-access-token'
    const onTokensRefreshed = vi.fn((payload: UserLoginResponse) => {
      currentAccess = payload.token.access
    })
    const onAuthFailure = vi.fn()

    const postSpy = vi.spyOn(axios, 'post').mockResolvedValueOnce({
      data: mockLoginResponse,
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as InternalAxiosRequestConfig,
    })

    let callCount = 0
    const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
      callCount += 1
      if (callCount === 1) {
        const err = new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
          data: { trace_id: 'middleware-002', message: 'token expired' },
          status: 401,
          statusText: 'Unauthorized',
          headers: {},
          config,
        })
        throw err
      }
      return {
        data: { id: 1, email: 'alice@example.com' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }

    const client = createHttpClient('http://localhost:8000', adapter)
    configureHttpAuth(client, {
      getAccessToken: () => currentAccess,
      getRefreshToken: () => 'valid-refresh-token',
      onTokensRefreshed,
      onAuthFailure,
    })

    const res = await client.post('/api/v1/users/profile')

    expect(postSpy).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/users/refresh-token',
      { refresh_token: 'valid-refresh-token' },
      { headers: { 'Content-Type': 'application/json' } },
    )
    expect(onTokensRefreshed).toHaveBeenCalledWith(mockLoginResponse)
    expect(onAuthFailure).not.toHaveBeenCalled()
    expect(callCount).toBe(2)
    expect(res.data).toEqual({ id: 1, email: 'alice@example.com' })
  })

  it('calls onAuthFailure and rejects when refresh token request fails', async () => {
    const onTokensRefreshed = vi.fn()
    const onAuthFailure = vi.fn()

    vi.spyOn(axios, 'post').mockRejectedValueOnce(new Error('Refresh invalid'))

    const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
      throw new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
        data: { trace_id: 'middleware-002', message: 'invalid token' },
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config,
      })
    }

    const client = createHttpClient('http://localhost:8000', adapter)
    configureHttpAuth(client, {
      getAccessToken: () => 'expired-token',
      getRefreshToken: () => 'revoked-refresh-token',
      onTokensRefreshed,
      onAuthFailure,
    })

    await expect(client.post('/api/v1/users/profile')).rejects.toThrow()
    expect(onTokensRefreshed).not.toHaveBeenCalled()
    expect(onAuthFailure).toHaveBeenCalledTimes(1)
  })
})
