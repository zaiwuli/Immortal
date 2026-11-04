import { request } from './request'

export interface Token {
  id: number
  token_key: string
  permissions: string[]
  enabled: boolean
  expires_at: string | null
  last_used_at: string | null
}
export interface Catalog {
  resources: Record<string, string>
  actions: Record<string, string>
}
export const listToken = () => request<Token[]>({ url: '/tokens/' })
export const permissionCatalog = () =>
  request<Catalog>({ url: '/tokens/permissions' })
export const deleteToken = (id: number) =>
  request({ url: `/tokens/${id}`, method: 'delete' })
export const patchToken = (id: number, enabled: boolean) =>
  request({ url: `/tokens/${id}`, method: 'patch', data: { enabled } })
export const addToken = (
  name: string,
  permissions: string[],
  expires_at: string | null
) =>
  request<Token & { token_value: string }>({
    url: '/tokens/',
    method: 'post',
    data: { name, permissions, expires_at },
  })
export const tokenAudit = (id: number) =>
  request<
    {
      id: number
      method: string
      path: string
      status_code: number
      create_time: string
    }[]
  >({ url: `/tokens/${id}/audit` })
