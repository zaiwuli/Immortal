import { Cog } from 'lucide-react'
import { ContentSection } from '../components/content-section'
import { RouteNamingForm } from './route-naming-form'
import { SystemConfigForm } from './system-config-form'

export function SettingsSystem() {
  return (
    <div className='space-y-4'>
      <ContentSection
        title='系统配置'
        desc='配置网络代理、数据源接口等运行设置。'
        icon={<Cog className='h-5 w-5' />}
      >
        <SystemConfigForm />
      </ContentSection>
      <RouteNamingForm />
    </div>
  )
}
