import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getConfig, postConfig } from '@/api/config'
import { request } from '@/api/request'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface ToolConfig {
  url: string
  api_token: string
  auto_extract: boolean
  save_paths: { label: string; path: string }[]
}
export function OtherTools() {
  const { data, refetch } = useQuery({
    queryKey: ['tools115-config'],
    queryFn: async () =>
      (await getConfig<ToolConfig>('Downloader.tools115')).data,
  })
  const [url, setUrl] = useState(''),
    [token, setToken] = useState(''),
    [extract, setExtract] = useState(true),
    [busy, setBusy] = useState(false),
    [text, setText] = useState(''),
    [batch, setBatch] = useState(''),
    [result, setResult] = useState(''),
    [key, setKey] = useState('')
  useEffect(() => {
    if (data) {
      setUrl(data.url ?? '')
      setToken(data.api_token ?? '')
      setExtract(data.auto_extract ?? true)
    }
  }, [data])
  const save = async () => {
    setBusy(true)
    try {
      const res = await postConfig('Downloader.tools115', {
        url: url.trim(),
        api_token: token.trim(),
        auto_extract: extract,
        save_paths: [{ label: '115tools 默认云目录', path: 'default' }],
      })
      if (res.code === 0) {
        toast.success('已保存')
        await refetch()
      }
    } catch {
      toast.error('保存失败')
    } finally {
      setBusy(false)
    }
  }
  const test = async () => {
    try {
      const res = await request({ url: '/tools/115tools/test', method: 'post' })
      if (res.code === 0) toast.success('连接成功')
    } catch {
      toast.error('连接失败，请检查已保存的地址和令牌')
    }
  }
  const submit = async () => {
    const id = key || crypto.randomUUID()
    setKey(id)
    setBusy(true)
    try {
      const res = await request<{ batch_id: string }>({
        url: '/tools/115tools/import',
        method: 'post',
        data: { text, idempotency_key: id },
      })
      if (res.code === 0) {
        setBatch(res.data.batch_id)
        setResult(JSON.stringify(res.data, null, 2))
        setKey('')
        toast.success('已登记批次，请查询后续状态')
      }
    } catch {
      toast.error('提交结果未知。保持内容不变重试会复用相同幂等键。')
    } finally {
      setBusy(false)
    }
  }
  const query = async () => {
    try {
      const res = await request({
        url: `/tools/115tools/batches/${encodeURIComponent(batch)}`,
      })
      setResult(JSON.stringify(res.data, null, 2))
    } catch {
      toast.error('查询失败，请确认批次属于当前配置的远端令牌')
    }
  }
  return (
    <div className='space-y-4'>
      <h3 className='font-semibold'>115tools</h3>
      <p className='text-sm text-muted-foreground'>
        连接独立部署的
        115tools，支持订阅投递和手动导入。保存后可在分发规则中选择
        115tools。云目录由工具后台管理，此处的默认目标不会覆盖远端目录。
      </p>
      <label className='block space-y-1 text-sm'>
        服务地址
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder='http://主机:端口'
        />
      </label>
      <label className='block space-y-1 text-sm'>
        115tools API 令牌
        <Input
          type='password'
          autoComplete='off'
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
      </label>
      <label className='flex gap-2 text-sm'>
        <input
          type='checkbox'
          checked={extract}
          onChange={(e) => setExtract(e.target.checked)}
        />
        离线下载后自动解压
      </label>
      <div className='flex gap-2'>
        <Button disabled={busy || !url || !token} onClick={save}>
          保存连接
        </Button>
        <Button variant='outline' onClick={test}>
          测试已保存连接
        </Button>
      </div>
      <div className='space-y-3 border-t pt-4'>
        <p className='text-sm'>
          手动导入链接（每行一条）。登记排队不代表下载或解压完成。
        </p>
        <textarea
          className='min-h-24 w-full rounded border bg-background p-2 text-sm'
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setKey('')
          }}
        />
        <Button disabled={busy || !text.trim()} onClick={submit}>
          提交链接
        </Button>
        <div className='flex gap-2'>
          <Input
            placeholder='批次 ID'
            value={batch}
            onChange={(e) => setBatch(e.target.value)}
          />
          <Button variant='outline' disabled={!batch} onClick={query}>
            查询批次
          </Button>
        </div>
        {result && (
          <pre className='max-h-64 overflow-auto rounded border p-3 text-xs'>
            {result}
          </pre>
        )}
      </div>
    </div>
  )
}
