import { httpClient } from '@/api/http'
import type {
  UserEntity,
  UserLoginRequest,
  UserLoginResponse,
  UserRefreshTokenRequest,
  UserRegisterRequest,
} from '@/types/auth.types'

export async function register(payload: UserRegisterRequest): Promise<UserEntity> {
  const { data } = await httpClient.post<UserEntity>('/api/v1/users/register', payload)
  return data
}

export async function login(payload: UserLoginRequest): Promise<UserLoginResponse> {
  const { data } = await httpClient.post<UserLoginResponse>('/api/v1/users/login', payload)
  return data
}

export async function refreshToken(payload: UserRefreshTokenRequest): Promise<UserLoginResponse> {
  const { data } = await httpClient.post<UserLoginResponse>('/api/v1/users/refresh-token', payload)
  return data
}

export async function logout(payload: UserRefreshTokenRequest): Promise<void> {
  await httpClient.post('/api/v1/users/logout', payload)
}

export async function getProfile(): Promise<UserEntity> {
  const { data } = await httpClient.get<UserEntity>('/api/v1/users/profile')
  return data
}
