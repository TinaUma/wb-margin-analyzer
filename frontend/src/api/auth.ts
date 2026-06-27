import client from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/login', { email, password })
  return data
}

export async function register(email: string, password: string): Promise<void> {
  await client.post('/auth/register', { email, password })
}
