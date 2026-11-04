import * as z from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { update_user } from '@/api/user.ts'
import { Button } from '@/components/ui/button.tsx'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form.tsx'
import { Input } from '@/components/ui/input'
import { Save } from 'lucide-react'


const accountScheme = z.object({
  username: z.string().min(2, '用户名至少2位'),
  password: z.string().min(8, '至少8位密码'),
})

type accountValues = z.infer<typeof accountScheme>

export function AccountForm() {
  const account = useForm<accountValues>({
    resolver: zodResolver(accountScheme),
    defaultValues: {
      username: '',
      password: '',
    },
  })

  const handleSubmit = async (data: accountValues) => {
    const res = await update_user(data)
    toast.success(res.message)
  }

  return (
      <Form {...account}>
        <form
          onSubmit={account.handleSubmit(handleSubmit)}
          className='space-y-4  max-w-md'
        >
          <FormField
            control={account.control}
            name='username'
            render={({ field }) => (
              <FormItem>
                <FormLabel>用户名</FormLabel>
                <FormControl>
                  <Input placeholder='输入用户名' {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={account.control}
            name='password'
            render={({ field }) => (
              <FormItem>
                <FormLabel>密码</FormLabel>
                <FormControl>
                  <Input
                    type='password'
                    placeholder='输入登录密码'
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type='submit'>
            <Save/>
            保存配置
          </Button>
        </form>
      </Form>
  )
}
