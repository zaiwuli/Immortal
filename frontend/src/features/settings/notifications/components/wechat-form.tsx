import { useEffect, useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import { getConfig, postConfig } from '@/api/config.ts'
import { Button } from '@/components/ui/button.tsx'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from '@/components/ui/form.tsx'
import { Input } from '@/components/ui/input.tsx'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover.tsx'
import { Separator } from '@/components/ui/separator.tsx'
import { Switch } from '@/components/ui/switch.tsx'
import { Textarea } from '@/components/ui/textarea.tsx'
import {
  NotificationTemplateDocsPanel,
  NotificationTemplateDocsPopoverContent,
  type NotificationTemplateEventName,
  castSubscribeTemplate,
  downloadTemplate,
  movieSubscribeTemplate,
  subscribeCompletedTemplate,
} from '@/features/settings/notifications/components/template-docs.tsx'

const schema = z.object({
  enable: z.boolean(),
  download_enable: z.boolean(),
  push_image: z.boolean(),
  corp_id: z.string(),
  corp_secret: z.string(),
  agent_id: z.string(),
  token: z.string(),
  encoding_aes_key: z.string(),
  to_user: z.string(),
  proxy: z.string().optional(),
  template: z.string(),
  movie_subscribe_enable: z.boolean(),
  movie_subscribe_template: z.string(),
  subscribe_completed_enable: z.boolean(),
  subscribe_completed_template: z.string(),
  cast_subscribe_enable: z.boolean(),
  cast_subscribe_template: z.string(),
})

type FormValues = z.infer<typeof schema>

const CONFIG_KEY = 'Notification.wechat'

const DEFAULT_VALUES: FormValues = {
  enable: false,
  download_enable: false,
  push_image: false,
  corp_id: '',
  corp_secret: '',
  agent_id: '',
  token: '',
  encoding_aes_key: '',
  to_user: '@all',
  proxy: '',
  template: downloadTemplate,
  movie_subscribe_enable: false,
  movie_subscribe_template: movieSubscribeTemplate,
  subscribe_completed_enable: false,
  subscribe_completed_template: subscribeCompletedTemplate,
  cast_subscribe_enable: false,
  cast_subscribe_template: castSubscribeTemplate,
}

const DEFAULT_TEMPLATES = {
  template: downloadTemplate,
  movie_subscribe_template: movieSubscribeTemplate,
  subscribe_completed_template: subscribeCompletedTemplate,
  cast_subscribe_template: castSubscribeTemplate,
} satisfies Pick<
  FormValues,
  | 'template'
  | 'movie_subscribe_template'
  | 'subscribe_completed_template'
  | 'cast_subscribe_template'
>

function TemplateHeader({
  title,
  eventName,
  active,
  onSelect,
}: {
  title: string
  eventName: NotificationTemplateEventName
  active: boolean
  onSelect: (eventName: NotificationTemplateEventName) => void
}) {
  return (
    <div className='flex items-center justify-between gap-3'>
      <div className='text-sm font-medium'>{title}</div>
      <div className='hidden lg:block'>
        <Button
          type='button'
          variant={active ? 'default' : 'outline'}
          size='sm'
          onClick={() => onSelect(eventName)}
        >
          模板说明
        </Button>
      </div>
      <div className='lg:hidden'>
        <Popover>
          <PopoverTrigger asChild>
            <Button type='button' variant='outline' size='sm'>
              模板说明
            </Button>
          </PopoverTrigger>
          <PopoverContent align='end' className='w-[min(92vw,28rem)] p-3'>
            <NotificationTemplateDocsPopoverContent eventName={eventName} />
          </PopoverContent>
        </Popover>
      </div>
    </div>
  )
}

export function WechatNotificationForm() {
  const queryClient = useQueryClient()
  const [activeTemplateDoc, setActiveTemplateDoc] = useState<NotificationTemplateEventName | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  })

  const { data } = useQuery({
    queryKey: [CONFIG_KEY],
    queryFn: async () => {
      const res = await getConfig<FormValues>(CONFIG_KEY)
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (data) {
      form.reset({ ...DEFAULT_VALUES, ...data })
    }
  }, [data, form])

  const onSubmit = async (values: FormValues) => {
    const res = await postConfig(CONFIG_KEY, values as never)
    if (res.code === 0) {
      toast.success(res.message)
      queryClient.invalidateQueries({ queryKey: [CONFIG_KEY] })
    }
  }

  const handleResetTemplate = (
    fieldName: keyof typeof DEFAULT_TEMPLATES,
    label: string,
  ) => {
    form.setValue(fieldName, DEFAULT_TEMPLATES[fieldName], {
      shouldDirty: true,
      shouldTouch: true,
    })
    toast.success(`${label}已重置为默认模板`)
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className='space-y-4 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start lg:gap-6 lg:space-y-0'
      >
        <div className='max-w-4xl space-y-4'>
          <FormField
            control={form.control}
            name='enable'
            render={({ field }) => (
              <FormItem className='flex items-center justify-between'>
                <FormLabel>启用企业微信通知</FormLabel>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name='push_image'
            render={({ field }) => (
              <FormItem className='flex items-center justify-between'>
                <FormLabel>推送图片</FormLabel>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />

          <Separator />


          <FormField
            name='corp_id'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>企业 ID</FormLabel>
                <FormControl>
                  <Input placeholder='WECHAT_CORP_ID' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='corp_secret'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>企业密钥</FormLabel>
                <FormControl>
                  <Input placeholder='WECHAT_CORP_SECRET' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='agent_id'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>应用 ID</FormLabel>
                <FormControl>
                  <Input placeholder='WECHAT_AGENT_ID' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='token'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>回调 Token</FormLabel>
                <FormControl>
                  <Input placeholder='WECHAT_TOKEN' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='encoding_aes_key'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>回调 EncodingAESKey</FormLabel>
                <FormControl>
                  <Input placeholder='WECHAT_ENCODING_AES_KEY' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='proxy'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>企业微信代理</FormLabel>
                <FormControl>
                  <Input placeholder='https://qyapi.weixin.qq.com' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <FormField
            name='to_user'
            control={form.control}
            render={({ field }) => (
              <FormItem>
                <FormLabel>推送用户</FormLabel>
                <FormControl>
                  <Input placeholder='@all' {...field} />
                </FormControl>
              </FormItem>
            )}
          />

          <div className='space-y-2'>
            <TemplateHeader
              title='下载开始模板'
              eventName='download'
              active={activeTemplateDoc === 'download'}
              onSelect={setActiveTemplateDoc}
            />
            <FormField
              control={form.control}
              name='download_enable'
              render={({ field }) => (
                <FormItem className='flex items-center justify-between'>
                  <FormLabel>启用下载推送</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              name='template'
              control={form.control}
              render={({ field }) => (
                <FormItem>
                  <div className='mb-2 flex items-center justify-between gap-3'>
                    <FormLabel>消息模板</FormLabel>
                    <Button
                      type='button'
                      variant='outline'
                      size='sm'
                      onClick={() => handleResetTemplate('template', '下载开始模板')}
                    >
                      <RotateCcw className='h-4 w-4' />
                      重置默认模板
                    </Button>
                  </div>
                  <FormControl>
                    <Textarea rows={8} {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>

          <Separator />

          <div className='space-y-2'>
            <TemplateHeader
              title='影片订阅推送'
              eventName='movie_subscribe'
              active={activeTemplateDoc === 'movie_subscribe'}
              onSelect={setActiveTemplateDoc}
            />
            <FormField
              control={form.control}
              name='movie_subscribe_enable'
              render={({ field }) => (
                <FormItem className='flex items-center justify-between'>
                  <FormLabel>启用影片订阅推送</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              name='movie_subscribe_template'
              control={form.control}
              render={({ field }) => (
                <FormItem>
                  <div className='mb-2 flex items-center justify-between gap-3'>
                    <FormLabel>影片订阅模板</FormLabel>
                    <Button
                      type='button'
                      variant='outline'
                      size='sm'
                      onClick={() =>
                        handleResetTemplate('movie_subscribe_template', '影片订阅模板')
                      }
                    >
                      <RotateCcw className='h-4 w-4' />
                      重置默认模板
                    </Button>
                  </div>
                  <FormControl>
                    <Textarea rows={8} {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>

          <Separator />

          <div className='space-y-2'>
            <TemplateHeader
              title='订阅完成推送'
              eventName='subscribe_completed'
              active={activeTemplateDoc === 'subscribe_completed'}
              onSelect={setActiveTemplateDoc}
            />
            <FormField
              control={form.control}
              name='subscribe_completed_enable'
              render={({ field }) => (
                <FormItem className='flex items-center justify-between'>
                  <FormLabel>启用订阅完成推送</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              name='subscribe_completed_template'
              control={form.control}
              render={({ field }) => (
                <FormItem>
                  <div className='mb-2 flex items-center justify-between gap-3'>
                    <FormLabel>订阅完成模板</FormLabel>
                    <Button
                      type='button'
                      variant='outline'
                      size='sm'
                      onClick={() =>
                        handleResetTemplate(
                          'subscribe_completed_template',
                          '订阅完成模板',
                        )
                      }
                    >
                      <RotateCcw className='h-4 w-4' />
                      重置默认模板
                    </Button>
                  </div>
                  <FormControl>
                    <Textarea rows={8} {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>

          <Separator />

          <div className='space-y-2'>
            <TemplateHeader
              title='演员订阅推送'
              eventName='cast_subscribe'
              active={activeTemplateDoc === 'cast_subscribe'}
              onSelect={setActiveTemplateDoc}
            />
            <FormField
              control={form.control}
              name='cast_subscribe_enable'
              render={({ field }) => (
                <FormItem className='flex items-center justify-between'>
                  <FormLabel>启用演员订阅推送</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              name='cast_subscribe_template'
              control={form.control}
              render={({ field }) => (
                <FormItem>
                  <div className='mb-2 flex items-center justify-between gap-3'>
                    <FormLabel>演员订阅模板</FormLabel>
                    <Button
                      type='button'
                      variant='outline'
                      size='sm'
                      onClick={() =>
                        handleResetTemplate('cast_subscribe_template', '演员订阅模板')
                      }
                    >
                      <RotateCcw className='h-4 w-4' />
                      重置默认模板
                    </Button>
                  </div>
                  <FormControl>
                    <Textarea rows={8} {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>

          <Button type='submit'>
            <Save className='h-4 w-4' />
            保存配置
          </Button>
        </div>

        <div className='hidden lg:block lg:sticky lg:top-4 lg:h-[calc(100vh-5rem)] lg:overflow-hidden'>
          <NotificationTemplateDocsPanel eventName={activeTemplateDoc} />
        </div>
      </form>
    </Form>
  )
}
