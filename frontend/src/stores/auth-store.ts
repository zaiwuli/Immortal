import { create } from 'zustand'
import { getCookie, setCookie, removeCookie } from '@/lib/cookies'

export const ACCESS_TOKEN = 'jwt_token'
export const USERNAME = 'user'

interface AuthState {
  auth: {
    username: string
    setUsername: (username: string) => void
    accessToken: string
    setAccessToken: (accessToken: string) => void
    resetAccessToken: () => void
    reset: () => void
  }
}

export const useAuthStore = create<AuthState>()((set) => {
  return {
    auth: {
      username: getCookie(USERNAME) || '',
      setUsername: (username) => {
        set((state) => {
          setCookie(USERNAME, username)
          return { ...state, auth: { ...state.auth, username } }
        })
      },
      accessToken: getCookie(ACCESS_TOKEN) || '',
      setAccessToken: (accessToken) =>
        set((state) => {
          setCookie(ACCESS_TOKEN, accessToken)
          return { ...state, auth: { ...state.auth, accessToken } }
        }),
      resetAccessToken: () =>
        set((state) => {
          removeCookie(ACCESS_TOKEN)
          return { ...state, auth: { ...state.auth, accessToken: '' } }
        }),
      reset: () =>
        set((state) => {
          removeCookie(ACCESS_TOKEN)
          return {
            ...state,
            auth: { ...state.auth, user: null, accessToken: '' },
          }
        }),
    },
  }
})
