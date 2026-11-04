import { Link } from '@tanstack/react-router'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  authCardClassName,
  authCardContentClassName,
  authCardDescriptionClassName,
  authCardFooterClassName,
  authCardHeaderClassName,
  authCardTitleClassName,
  authFooterTextClassName,
  authLinkClassName,
} from '../auth-ui'
import { AuthLayout } from '../auth-layout'
import { OtpForm } from './components/otp-form'

export function Otp() {
  return (
    <AuthLayout>
      <Card className={authCardClassName}>
        <CardHeader className={authCardHeaderClassName}>
          <CardTitle className={authCardTitleClassName}>二次验证</CardTitle>
          <CardDescription className={authCardDescriptionClassName}>
            请输入 6 位验证码。验证码已发送至你的邮箱，请在时效内完成验证。
          </CardDescription>
        </CardHeader>
        <CardContent className={authCardContentClassName}>
          <OtpForm />
        </CardContent>
        <CardFooter className={authCardFooterClassName}>
          <p className={authFooterTextClassName}>
            没有收到验证码?{' '}
            <Link to='/sign-in' className={authLinkClassName}>
              返回登录重新获取
            </Link>
          </p>
        </CardFooter>
      </Card>
    </AuthLayout>
  )
}
