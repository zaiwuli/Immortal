import { useEffect, useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from '@tanstack/react-router'
import { Loader2, LogIn } from 'lucide-react'
import { toast } from 'sonner'
import { login } from '@/api/user.ts'
import { useAuthStore } from '@/stores/auth-store'
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
import { PasswordInput } from '@/components/password-input'
import {
  authFieldClassName,
  authFormClassName,
  authLabelClassName,
  authLinkClassName,
  authPasswordFieldClassName,
  authPrimaryButtonClassName,
} from '../../auth-ui'

const formSchema = z.object({
  username: z.string(),
  password: z.string().min(8, '密码至少 8 位'),
})

interface UserAuthFormProps extends React.HTMLAttributes<HTMLFormElement> {
  redirectTo?: string
}

export function UserAuthForm({
  className,
  redirectTo,
  ...props
}: UserAuthFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const { auth } = useAuthStore()

  useEffect(() => {
    if (auth.accessToken) {
      const targetPath = redirectTo || '/'
      navigate({ to: targetPath, replace: true })
    }
  }, [auth, navigate, redirectTo])

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  })

  async function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    const res = await login(data)
    setIsLoading(false)
    if (res.code === 0) {
      auth.setAccessToken(res.data.access_token)
      auth.setUsername(res.data.username)
      const targetPath = redirectTo || '/'
      toast.success(`欢迎回来, ${data.username}!`)
      await navigate({ to: targetPath, replace: true })
    } else {
      toast.error(res.message)
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
          name='username'
          render={({ field }) => (
            <FormItem className='relative gap-2.5'>
              <FormLabel className={authLabelClassName}>用户名</FormLabel>
              <FormControl>
                <Input className={authFieldClassName} placeholder='请输入用户名' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
              <Link to='/sign-up' className={cn(authLinkClassName, 'absolute end-0 top-0')}>
                首次登录?
              </Link>
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name='password'
          render={({ field }) => (
            <FormItem className='relative gap-2.5'>
              <FormLabel className={authLabelClassName}>密码</FormLabel>
              <FormControl>
                <PasswordInput className={authPasswordFieldClassName} placeholder='********' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
              <Link to='/forgot-password' className={cn(authLinkClassName, 'absolute end-0 top-0')}>
                忘记密码?
              </Link>
            </FormItem>
          )}
        />

        <Button className={authPrimaryButtonClassName} disabled={isLoading}>
          {isLoading ? <Loader2 className='animate-spin' /> : <LogIn />}
          登录
        </Button>
      </form>
    </Form>
  )
}
