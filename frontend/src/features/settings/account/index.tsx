import { UserPen } from 'lucide-react'
import { useUIStore } from '@/stores/ui-store'
import { ContentSection } from '../components/content-section'
import { AccountForm } from './account-form'

export function SettingsAccount() {
  const routeNamingMode = useUIStore((s) => s.routeNamingMode)
  const isSimple = routeNamingMode === 'simple'

  return (
    <ContentSection
      title={isSimple ? '账号信息' : '身份簿'}
      desc={
        isSimple
          ? '查看和修改当前用户的账号信息。'
          : '记录当前修士的身份凭证与本命信息。'
      }
      icon={<UserPen className='h-5 w-5 text-primary' />}
    >
      <AccountForm />
    </ContentSection>
  )
}
