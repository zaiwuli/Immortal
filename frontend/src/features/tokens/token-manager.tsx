import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  addToken,
  deleteToken,
  listToken,
  patchToken,
  permissionCatalog,
  tokenAudit,
} from '@/api/token'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ConfirmButton } from '@/components/confirm-button'

export default function TokenManager() {
  const cache = useQueryClient()
  const { data: tokens = [] } = useQuery({
    queryKey: ['tokens'],
    queryFn: async () => (await listToken()).data,
  })
  const { data: catalog } = useQuery({
    queryKey: ['permission-catalog'],
    queryFn: async () => (await permissionCatalog()).data,
  })
  const [open, setOpen] = useState(false),
    [name, setName] = useState(''),
    [permissions, setPermissions] = useState<string[]>([]),
    [expires, setExpires] = useState(''),
    [secret, setSecret] = useState(''),
    [busy, setBusy] = useState(false),
    [auditId, setAuditId] = useState<number | null>(null)
  const { data: audit = [] } = useQuery({
    queryKey: ['token-audit', auditId],
    enabled: auditId !== null,
    queryFn: async () => (await tokenAudit(auditId!)).data,
  })
  const refresh = () => cache.invalidateQueries({ queryKey: ['tokens'] })
  const choose = (kind: string) => {
    const resources = Object.keys(catalog?.resources ?? {})
    setPermissions(
      kind === 'full'
        ? ['*']
        : kind === 'read'
          ? resources.map((r) => `${r}:read`)
          : kind === 'download'
            ? [
                'content:read',
                'subscriptions:read',
                'subscriptions:write',
                'subscriptions:execute',
                'subscriptions:delete',
                'downloads:read',
                'downloads:execute',
              ]
            : resources
                .filter((r) => !['account', 'tokens'].includes(r))
                .flatMap((r) =>
                  Object.keys(catalog?.actions ?? {}).map((a) => `${r}:${a}`)
                )
    )
  }
  const create = async () => {
    setBusy(true)
    try {
      const res = await addToken(
        name.trim(),
        permissions,
        expires ? new Date(expires).toISOString() : null
      )
      if (res.code === 0) {
        setSecret(res.data.token_value)
        setOpen(false)
        setName('')
        setPermissions([])
        await refresh()
      }
    } catch {
      toast.error('创建失败，请检查名称和有效期')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className='space-y-5 overflow-auto p-1'>
      <div className='flex flex-wrap items-center justify-between gap-3'>
        <div>
          <h2 className='text-xl font-semibold'>API 令牌</h2>
          <p className='text-sm text-muted-foreground'>
            供外部 AI 和工具按授权操作后台。完整令牌仅在创建时显示一次。
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>创建令牌</Button>
      </div>
      <div className='space-y-2 rounded-lg border p-4 text-sm'>
        <p>
          服务地址：<code>{window.location.origin}</code>
        </p>
        <p>
          接口定义：
          <a
            className='text-primary underline'
            href='/openapi.json'
            target='_blank'
            rel='noreferrer'
          >
            OpenAPI
          </a>{' '}
          ·{' '}
          <a
            className='text-primary underline'
            href='/docs'
            target='_blank'
            rel='noreferrer'
          >
            接口文档
          </a>
        </p>
        <p>
          请求头：<code>X-API-Key: YOUR_API_TOKEN</code>，也支持 Bearer 令牌。
        </p>
        <p>
          连接后调用 <code>GET /api/v1/tokens/me</code> 查询当前权限。
        </p>
      </div>
      {tokens.length === 0 && (
        <p className='p-8 text-center text-muted-foreground'>
          暂无令牌，创建后即可连接外部工具。
        </p>
      )}
      {tokens.map((t) => (
        <div key={t.id} className='space-y-3 rounded-lg border p-4'>
          <div className='flex flex-wrap justify-between gap-2'>
            <strong>{t.token_key}</strong>
            <span>{t.enabled ? '已启用' : '已停用'}</span>
          </div>
          <p className='text-sm break-all text-muted-foreground'>
            {t.permissions.includes('*')
              ? '完全控制'
              : t.permissions.join('、')}
          </p>
          <p className='text-xs text-muted-foreground'>
            有效期：
            {t.expires_at ? new Date(t.expires_at).toLocaleString() : '长期'} ·
            最近使用：
            {t.last_used_at
              ? new Date(t.last_used_at).toLocaleString()
              : '尚未使用'}
          </p>
          <div className='flex gap-2'>
            <Button
              variant='outline'
              onClick={async () => {
                await patchToken(t.id, !t.enabled)
                await refresh()
              }}
            >
              {t.enabled ? '停用' : '启用'}
            </Button>
            <Button variant='outline' onClick={() => setAuditId(t.id)}>
              操作记录
            </Button>
            <ConfirmButton
              variant='outline'
              title='吊销令牌'
              description='吊销后该令牌立即失效。'
              triggerText='吊销'
              onConfirm={async () => {
                await deleteToken(t.id)
                await refresh()
              }}
            />
          </div>
        </div>
      ))}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className='max-h-[85vh] overflow-auto sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>创建 API 令牌</DialogTitle>
          </DialogHeader>
          <label className='space-y-1 text-sm'>
            名称
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={64}
              placeholder='例如：外部 AI 助手'
            />
          </label>
          <label className='space-y-1 text-sm'>
            到期时间（留空为长期）
            <Input
              type='datetime-local'
              value={expires}
              onChange={(e) => setExpires(e.target.value)}
            />
          </label>
          <div className='flex flex-wrap gap-2'>
            {[
              ['read', '只读'],
              ['download', '订阅与下载'],
              ['ops', '自动化运维'],
              ['full', '完全控制'],
            ].map(([key, label]) => (
              <Button key={key} variant='outline' onClick={() => choose(key)}>
                {label}
              </Button>
            ))}
          </div>
          <label className='flex gap-2 text-sm'>
            <input
              type='checkbox'
              checked={permissions.includes('*')}
              onChange={(e) => setPermissions(e.target.checked ? ['*'] : [])}
            />
            完全控制（包含账号及令牌管理）
          </label>
          <div className='space-y-3'>
            {Object.entries(catalog?.resources ?? {}).map(([key, label]) => (
              <fieldset key={key} className='rounded border p-3'>
                <legend className='px-1 text-sm'>{label}</legend>
                <div className='flex flex-wrap gap-4'>
                  {Object.entries(catalog?.actions ?? {}).map(
                    ([action, text]) => {
                      const value = `${key}:${action}`
                      return (
                        <label key={value} className='flex gap-1 text-sm'>
                          <input
                            type='checkbox'
                            disabled={permissions.includes('*')}
                            checked={
                              permissions.includes('*') ||
                              permissions.includes(value)
                            }
                            onChange={(e) =>
                              setPermissions(
                                e.target.checked
                                  ? [...permissions, value]
                                  : permissions.filter((p) => p !== value)
                              )
                            }
                          />
                          {text}
                        </label>
                      )
                    }
                  )}
                </div>
              </fieldset>
            ))}
          </div>
          <Button
            disabled={busy || !name.trim() || permissions.length === 0}
            onClick={create}
          >
            {busy ? '创建中…' : '创建令牌'}
          </Button>
        </DialogContent>
      </Dialog>
      <Dialog
        open={!!secret}
        onOpenChange={(v) => {
          if (!v) setSecret('')
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>请保存令牌</DialogTitle>
          </DialogHeader>
          <p className='text-sm'>
            关闭后无法再次查看。丢失时请吊销并创建新令牌。
          </p>
          <Input readOnly value={secret} />
          <Button
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(secret)
                toast.success('令牌已复制')
              } catch {
                toast.error('请手动选择并复制令牌')
              }
            }}
          >
            复制令牌
          </Button>
        </DialogContent>
      </Dialog>
      <Dialog
        open={auditId !== null}
        onOpenChange={(v) => {
          if (!v) setAuditId(null)
        }}
      >
        <DialogContent className='max-h-[80vh] overflow-auto sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>最近 50 条操作记录</DialogTitle>
          </DialogHeader>
          {audit.length === 0 ? (
            <p>暂无操作记录</p>
          ) : (
            audit.map((row) => (
              <div key={row.id} className='border-b py-2 text-xs break-all'>
                {new Date(row.create_time).toLocaleString()} · {row.method}{' '}
                {row.path} · HTTP {row.status_code}
              </div>
            ))
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
