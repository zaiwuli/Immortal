import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from '@tanstack/react-router'
import { showSubmittedData } from '@/lib/show-submitted-data'
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
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
  InputOTPSeparator,
} from '@/components/ui/input-otp'
import { authFormClassName, authPrimaryButtonClassName } from '../../auth-ui'

const formSchema = z.object({
  otp: z
    .string()
    .min(6, '请输入 6 位验证码。')
    .max(6, '请输入 6 位验证码。'),
})

type OtpFormProps = React.HTMLAttributes<HTMLFormElement>

const otpSlotClassName =
  'h-12 w-11 rounded-xl border border-stone-300/80 bg-white text-base text-stone-900 shadow-none first:rounded-xl first:border-l last:rounded-xl data-[active=true]:border-emerald-900/35 data-[active=true]:ring-3 data-[active=true]:ring-emerald-900/10'

export function OtpForm({ className, ...props }: OtpFormProps) {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { otp: '' },
  })

  const otp = form.watch('otp')

  function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    showSubmittedData(data)

    setTimeout(() => {
      setIsLoading(false)
      navigate({ to: '/' })
    }, 1000)
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
          name='otp'
          render={({ field }) => (
            <FormItem className='gap-3'>
              <FormLabel className='text-[13px] font-semibold tracking-[0.08em] text-stone-700'>验证码</FormLabel>
              <FormControl>
                <InputOTP
                  maxLength={6}
                  {...field}
                  containerClassName='justify-center gap-3 md:[&>[data-slot="input-otp-group"]>div]:w-11'
                >
                  <InputOTPGroup>
                    <InputOTPSlot className={otpSlotClassName} index={0} />
                    <InputOTPSlot className={otpSlotClassName} index={1} />
                  </InputOTPGroup>
                  <InputOTPSeparator className='text-stone-400' />
                  <InputOTPGroup>
                    <InputOTPSlot className={otpSlotClassName} index={2} />
                    <InputOTPSlot className={otpSlotClassName} index={3} />
                  </InputOTPGroup>
                  <InputOTPSeparator className='text-stone-400' />
                  <InputOTPGroup>
                    <InputOTPSlot className={otpSlotClassName} index={4} />
                    <InputOTPSlot className={otpSlotClassName} index={5} />
                  </InputOTPGroup>
                </InputOTP>
              </FormControl>
              <FormMessage className='text-center text-xs' />
            </FormItem>
          )}
        />
        <Button className={authPrimaryButtonClassName} disabled={otp.length < 6 || isLoading}>
          验证并进入
        </Button>
      </form>
    </Form>
  )
}
