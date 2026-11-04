import { request } from './request'

export interface User {
  username: string
  access_token: string
}


export function login(data: { username: string; password: string }) {
  return request<User>({
    url: '/users/login',
    method: 'post',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    data: data,
  })
}

export function register(params: { username: string; password: string }) {
  return request({
    url: '/users/',
    method: 'post',
    params,
  })
}

export function update_user(params: { username: string; password: string }) {
  return request({
    url: '/users/',
    method: 'put',
    params,
  })
}

export function getResetToken() {
  return request({
    url: '/users/reset-token',
    method: 'get',
  })
}

export function clearUser(token: string) {
  return request({
    url: `/users/reset?token=${token}`,
    method: 'delete',
  })
}

export function getVersion() {
  return request<string>({
    url: `/users/version`,
    method: 'get',
  })
}
