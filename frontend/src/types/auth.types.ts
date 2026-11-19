export interface UserEntity {
  id: number
  email: string
  first_name: string
  last_name: string
  created_at: string
  updated_at: string
}

export interface UserTokenEntity {
  access: string
  refresh: string
}

export interface UserLoginResponse {
  user: UserEntity
  token: UserTokenEntity
}

export interface UserRegisterRequest {
  email: string
  password: string
  first_name: string
  last_name: string
}

export interface UserLoginRequest {
  email: string
  password: string
}

export interface UserRefreshTokenRequest {
  refresh_token: string
}
