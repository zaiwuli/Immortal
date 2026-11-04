import { useUIStore } from '@/stores/ui-store'

type AuthLayoutProps = {
  children: React.ReactNode
}

const brandLogo = `${import.meta.env.BASE_URL}hulu_vector_180.png?v=20260321`

export function AuthLayout({ children }: AuthLayoutProps) {
  const routeNamingMode = useUIStore((s) => s.routeNamingMode)
  const isSimple = routeNamingMode === 'simple'

  return (
    <div className='container grid min-h-svh max-none items-center justify-center bg-[radial-gradient(circle_at_top,#efe2b2_0%,transparent_32%),linear-gradient(180deg,#f7f2e4_0%,#f1ead7_28%,#e6e0ce_100%)] px-4'>
      <div className='mx-auto flex w-full max-w-130 flex-col justify-center space-y-4 py-8 md:p-8'>
        <div className='rounded-[28px] border border-stone-300/70 bg-white/78 p-6 text-center shadow-[0_28px_80px_rgba(36,41,28,0.14)] backdrop-blur'>
          <div className='mx-auto flex size-18 items-center justify-center rounded-3xl bg-white shadow-[0_20px_48px_rgba(15,15,15,0.18)] ring-1 ring-black/8'>
            <img
              src={brandLogo}
              alt={isSimple ? 'Logo' : '青灯不灭'}
              data-image-mode-exempt='true'
              className='size-12 object-contain'
            />
          </div>
          <p className='mt-4 text-xs font-medium tracking-[0.45em] text-amber-700/80 uppercase'>
            {isSimple ? 'Media Console' : 'Immortal Console'}
          </p>
          <h1 className='mt-2 text-3xl font-semibold tracking-[0.2em] text-stone-900'>
            {isSimple ? '登录' : '修真入口'}
          </h1>
          <p className='mt-2 text-sm leading-6 text-stone-600'>
            {isSimple
              ? '登录后可管理订阅、任务和下载。'
              : '青灯不灭，灵气如潮。登录后可继续调度阵法、运转任务与巡览洞府。'}
          </p>
        </div>
        {children}
      </div>
    </div>
  )
}
