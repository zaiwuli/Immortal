import { Bell } from 'lucide-react'
import { useUIStore } from '@/stores/ui-store'
import { ContentSection } from '../components/content-section'
import { NotificationsForm } from './notifications-form'

export function SettingsNotifications() {
  const routeNamingMode = useUIStore((s) => s.routeNamingMode)
  const isSimple = routeNamingMode === 'simple'

  return (
    <ContentSection
      title={isSimple ? '通知设置' : '传讯法阵'}
      desc={
        isSimple
          ? '配置 Telegram、Discord 等通知渠道。'
          : '打通跨界传讯之路，使洞府异动即时回响。'
      }
      icon={<Bell size={18} />}
    >
      <NotificationsForm />
    </ContentSection>
  )
}
