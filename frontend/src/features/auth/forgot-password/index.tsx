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
import { ForgotPasswordForm } from './components/forgot-password-form'

export function ForgotPassword() {
  return (
    <AuthLayout>
      <Card className={authCardClassName}>
        <CardHeader className={authCardHeaderClassName}>
          <CardTitle className={authCardTitleClassName}>重置口令</CardTitle>
          <CardDescription className={authCardDescriptionClassName}>
            输入服务端生成的口令来重置用户。注意：此操作会删除数据库用户信息，需要重新注册。
          </CardDescription>
        </CardHeader>
        <CardContent className={authCardContentClassName}>
          <ForgotPasswordForm />
        </CardContent>
        <CardFooter className={authCardFooterClassName}>
          <p className={authFooterTextClassName}>
            没有账号?{' '}
            <Link to='/sign-up' className={authLinkClassName}>
              注册
            </Link>
          </p>
        </CardFooter>
      </Card>
    </AuthLayout>
  )
}
