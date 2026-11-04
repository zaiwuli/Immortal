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
import { SignUpForm } from './components/sign-up-form'

export function SignUp() {
  return (
    <AuthLayout>
      <Card className={authCardClassName}>
        <CardHeader className={authCardHeaderClassName}>
          <CardTitle className={authCardTitleClassName}>创建账号</CardTitle>
          <CardDescription className={authCardDescriptionClassName}>
            设立新的宗门身份，完成后可回到登入页进入控制台。
          </CardDescription>
        </CardHeader>
        <CardContent className={authCardContentClassName}>
          <SignUpForm />
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
