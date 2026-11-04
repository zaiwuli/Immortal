import { Download } from 'lucide-react'
import { useUIStore } from '@/stores/ui-store'
import { ContentSection } from '@/features/settings/components/content-section.tsx'
import { DownloaderForm } from '@/features/settings/downloader/downloader-form.tsx'

export function SettingsDownloader() {
  const routeNamingMode = useUIStore((s) => s.routeNamingMode)
  const isSimple = routeNamingMode === 'simple'

  return (
    <ContentSection
      title={isSimple ? '下载器与其他工具' : '下载法器'}
      desc={
        isSimple
          ? '配置下载器、保存路径及外部工具连接。'
          : '布设下载器与归藏路径，使资源各归其位。'
      }
      icon={<Download className='h-5 w-5 text-primary' />}
    >
      <DownloaderForm />
    </ContentSection>
  )
}
