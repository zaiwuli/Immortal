import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from '@tanstack/react-router'
import { register } from '@/api/user.ts'
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
  authPasswordFieldClassName,
  authPrimaryButtonClassName,
} from '../../auth-ui'

const formSchema = z
  .object({
    username: z.string(),
    password: z.string().min(8, '至少 8 位密码'),
    confirmPassword: z.string().min(1, '再次输入密码'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: '两个密码不一致',
    path: ['confirmPassword'],
  })

export function SignUpForm({
  className,
  ...props
}: React.HTMLAttributes<HTMLFormElement>) {
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: '',
      password: '',
      confirmPassword: '',
    },
  })

  async function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    const res = await register(data)
    setIsLoading(false)
    if (res.code === 0) {
      await navigate({ to: '/sign-in', replace: true })
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
            <FormItem className='gap-2.5'>
              <FormLabel className={authLabelClassName}>用户名</FormLabel>
              <FormControl>
                <Input className={authFieldClassName} placeholder='请输入用户名' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name='password'
          render={({ field }) => (
            <FormItem className='gap-2.5'>
              <FormLabel className={authLabelClassName}>密码</FormLabel>
              <FormControl>
                <PasswordInput className={authPasswordFieldClassName} placeholder='********' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name='confirmPassword'
          render={({ field }) => (
            <FormItem className='gap-2.5'>
              <FormLabel className={authLabelClassName}>确认密码</FormLabel>
              <FormControl>
                <PasswordInput className={authPasswordFieldClassName} placeholder='********' {...field} />
              </FormControl>
              <FormMessage className='text-xs' />
            </FormItem>
          )}
        />
        <Button className={authPrimaryButtonClassName} disabled={isLoading}>
          创建账号
        </Button>
      </form>
    </Form>
  )
}
