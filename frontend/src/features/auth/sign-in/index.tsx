import { useSearch } from '@tanstack/react-router'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  authCardClassName,
  authCardContentClassName,
  authCardDescriptionClassName,
  authCardHeaderClassName,
  authCardTitleClassName,
} from '../auth-ui'
import { AuthLayout } from '../auth-layout'
import { UserAuthForm } from './components/user-auth-form'

export function SignIn() {
  const { redirect } = useSearch({ from: '/(auth)/sign-in' })

  return (
    <AuthLayout>
      <Card className={authCardClassName}>
        <CardHeader className={authCardHeaderClassName}>
          <CardTitle className={authCardTitleClassName}>登入</CardTitle>
          <CardDescription className={authCardDescriptionClassName}>
            以宗门令鉴定身份后，进入控制台继续调度阵法与任务。
          </CardDescription>
        </CardHeader>
        <CardContent className={authCardContentClassName}>
          <UserAuthForm redirectTo={redirect} />
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
