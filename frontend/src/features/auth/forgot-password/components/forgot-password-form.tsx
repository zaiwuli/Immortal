import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from '@tanstack/react-router'
import { ArrowRight, Loader2, RefreshCcw } from 'lucide-react'
import { toast } from 'sonner'
import { clearUser, getResetToken } from '@/api/user.ts'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
  authFieldClassName,
  authFormClassName,
  authLabelClassName,
  authPrimaryButtonClassName,
  authSecondaryButtonClassName,
} from '../../auth-ui'

const formSchema = z.object({
  token: z.string().min(1, '输入口令'),
})

export function ForgotPasswordForm({
  className,
  ...props
}: React.HTMLAttributes<HTMLFormElement>) {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { token: '' },
  })

  async function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    const res = await clearUser(data.token)
    setIsLoading(false)
    if (res.code === 0) {
      toast.success('前往注册账号')
      navigate({ to: '/sign-up', replace: true })
    }
  }

  async function handleGenerateToken() {
    const res = await getResetToken()
    if (res.code === 0) {
      toast.success(res.message)
    }
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn(authFormClassName, className)}
        {...props}
      >
        <FormField
          control={form.control}
          name='token'
          render={({ field }) => (
            <FormItem className='gap-2.5'>
              <div className='flex items-center justify-between gap-3'>
                <FormLabel className={authLabelClassName}>口令</FormLabel>
                <Button
                  type='button'
                  variant='ghost'
                  size='sm'
                  className={authSecondaryButtonClassName}
                  onClick={handleGenerateToken}
                >
                  <RefreshCcw className='h-3.5 w-3.5' />
                  随机生成
                </Button>
              </div>

              <FormControl>
                <Input className={authFieldClassName} placeholder='输入或生成口令' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
            </FormItem>
          )}
        />
        <Button className={authPrimaryButtonClassName} disabled={isLoading}>
          继续
          {isLoading ? <Loader2 className='animate-spin' /> : <ArrowRight />}
        </Button>
      </form>
    </Form>
  )
}
