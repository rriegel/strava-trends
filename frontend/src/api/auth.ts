import apiClient from './client'
import type { User } from '../types'

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get('/users/me')
  return response.data
}

export async function updateUser(data: Partial<User>): Promise<User> {
  const response = await apiClient.put('/users/me', data)
  return response.data
}

export async function syncActivities(): Promise<{ status: string; message: string }> {
  const response = await apiClient.post('/users/me/sync')
  return response.data
}
