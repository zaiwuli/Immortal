import { KeyRound } from 'lucide-react'
import { ConfigDrawer } from '@/components/config-drawer'
import { ContentTitle } from '@/components/content-title.tsx'
import { ImageModeSwitch } from '@/components/image-mode-switch.tsx'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ServerLogDialog } from '@/components/server-log-dialog.tsx'
import { ThemeSwitch } from '@/components/theme-switch'
import { useUIStore } from '@/stores/ui-store'
import TokenManager from '@/features/tokens/token-manager.tsx'

export function Tokens() {
  const routeNamingMode = useUIStore((s) => s.routeNamingMode)
  const isSimple = routeNamingMode === 'simple'

  return (
    <>
      <Header fixed>
        <Search />
        <div className='ms-auto flex items-center space-x-4'>
          <ServerLogDialog />
          <ImageModeSwitch />
          <ThemeSwitch />
          <ConfigDrawer />
        </div>
      </Header>

      <Main fixed>
        <ContentTitle
          title={isSimple ? 'Token 管理' : '法印册'}
          description={
            isSimple
              ? '管理 API Token，用于第三方应用访问。'
              : '法印可授外界器物通行之权，以行宗门术法。'
          }
          icon={<KeyRound className='h-8 w-8 text-primary' />}
        />
        <TokenManager />
      </Main>
    </>
  )
}
