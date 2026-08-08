import request from './index'

export const login = (data: { username: string; password: string }) =>
  request.post('/api/v1/auth/login', data)

export const register = (data: { username: string; password: string; email: string }) =>
  request.post('/api/v1/auth/register', data)

export const getProfile = () => request.get('/api/v1/auth/profile')
