import { Info } from 'lucide-react'
import { Badge } from '@/components/ui/badge.tsx'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card.tsx'

export type NotificationTemplateEventName =
  | 'download'
  | 'movie_subscribe'
  | 'subscribe_completed'
  | 'cast_subscribe'

export const downloadTemplate = `🚀 下载开始

📌 标题: {{ article_title }}
🗂️ 分类: {{ article_section }} / {{ article_category }}
📦 大小: {{ article_size }}
🗓️ 发布日期: {{ article_publish_date }}
🆔 站点 ID: {{ article_tid }}
🌐 站点: {{ article_website }}
⬇️ 下载器: {{ download_client }}
📁 保存路径: {{ download_save_path }}
🔗 详情页: {{ article_detail_url }}
🎞️ 番号: {{ article_match_number }}
📚 在库: {{ article_in_library }}
🧲 磁链: {{ article_magnet }}`

export const movieSubscribeTemplate = `🎬 影片订阅

🎞️ 番号: {{ movie_number }}
📌 标题: {{ movie_cn_title or movie_title or movie_number }}
🗓️ 发布日期: {{ movie_release_date }}
👥 演员: {{ movie_cast_names | join(' / ') }}
🏷️ 标签: {{ movie_genres | join(' / ') }}
📡 订阅状态: {{ subscribe_status }}
⚡ 预下载: {{ subscribe_pre_download_enabled }}
🧰 过滤器: {{ filter_name }}
📊 排序器: {{ priority_name }}`

export const subscribeCompletedTemplate = `✅ 订阅完成

🎞️ 番号: {{ movie_number }}
📌 标题: {{ movie_cn_title or movie_title or movie_number }}
🏁 完成方式: {{ completion_source }}
📦 资源标题: {{ article_title }}
📏 资源大小: {{ article_size }}
🗓️ 资源发布时间: {{ article_publish_date }}
🔗 详情页: {{ article_detail_url }}
🧰 过滤器: {{ filter_name }}
📊 排序器: {{ priority_name }}`

export const castSubscribeTemplate = `🌸 演员订阅

👤 演员: {{ cast_cn_name or cast_name }}
🪪 曾用名: {{ cast_former_name | join(' / ') }}
🗓️ 最早发行日期: {{ cast_subscribe_earliest_release_date }}
👥 最多共演人数: {{ cast_subscribe_max_coactors }}
🚫 排除 VR: {{ cast_subscribe_exclude_vr }}
🧰 过滤器: {{ filter_name }}
📊 排序器: {{ priority_name }}`

// ============ 共用字段定义 ============

const FILTER_PRIORITY_COMMON_FIELDS: TemplateDocField[] = [
  {
    key: 'filter_name / priority_name',
    label: '过滤器与排序器名称',
    description: '过滤器名称和排序器名称。',
  },
]

const FILTER_RULE_FIELDS: TemplateDocField[] = [
  {
    key: 'filter_keyword / filter_resolutions / filter_subtitles / filter_mosaic',
    label: '过滤器规则',
    description:
      '过滤器关键词、分辨率、字幕和马赛克规则；其中数组已被拍平成字符串。',
  },
  {
    key: 'filter_min_size / filter_max_size',
    label: '过滤器大小范围',
    description: '过滤器限制的最小和最大体积。',
  },
  {
    key: 'filter_skip_in_library_check / filter_enable_pre_download / filter_is_default',
    label: '过滤器布尔项',
    description: '值为 是/否。',
  },
  {
    key: 'filter_create_time / filter_update_time',
    label: '过滤器时间',
    description: '过滤器创建和更新时间。',
  },
]

const FILTER_ID_FIELDS: TemplateDocField[] = [
  {
    key: 'filter_id / priority_id',
    label: '生效对象 ID',
    description: '最终生效的过滤器和排序器 ID。',
  },
  {
    key: 'filter_create_time / filter_update_time',
    label: '过滤器时间',
    description: '过滤器创建和更新时间。',
  },
]

const PRIORITY_RULE_FIELDS: TemplateDocField[] = [
  {
    key: 'priority_resolutions / priority_subtitles / priority_mosaic / priority_sort',
    label: '排序器规则',
    description:
      '排序器的分辨率、字幕、马赛克和优先级规则；数组已被拍平成字符串。',
  },
  {
    key: 'priority_is_default',
    label: '默认排序器',
    description: '排序器是否为默认值，值为 是/否。',
  },
  {
    key: 'priority_create_time / priority_update_time',
    label: '排序器时间',
    description: '排序器创建和更新时间。',
  },
]

const MOVIE_BASE_FIELDS: TemplateDocField[] = [
  { key: 'movie_id', label: '影片主键', description: '本地 movie 表主键。' },
  {
    key: 'movie_description / movie_cn_description',
    label: '影片简介',
    description: '原始简介和中文简介。',
  },
  { key: 'movie_duration', label: '片长', description: '影片片长。' },
  {
    key: 'movie_poster / movie_banner',
    label: '影片图片',
    description: '海报与横幅图地址。',
  },
  {
    key: 'movie_still_photos',
    label: '影片预览图数组',
    description: '影片预览图列表。',
  },
  {
    key: 'movie_genres',
    label: '影片标签数组',
    description: '影片标签原始数组。',
  },
  {
    key: 'movie_cast_ids',
    label: '演员 ID 数组',
    description: '影片关联演员 ID 原始数组。',
  },
  {
    key: 'movie_create_time / movie_update_time',
    label: '影片时间',
    description: '影片创建和更新时间。',
  },
]

const MOVIE_CAST_FIELDS: TemplateDocField[] = [
  {
    key: 'movie_cast_ids / movie_cast_names',
    label: '影片数组字段',
    description: '影片标签、演员 ID、演员名称数组。',
  },
]

const SUBSCRIBE_ID_FIELDS: TemplateDocField[] = [
  {
    key: 'subscribe_id / subscribe_movie_id',
    label: '订阅关联 ID',
    description: '订阅主键和关联影片主键。',
  },
  {
    key: 'subscribe_filter_id / subscribe_priority_id',
    label: '订阅绑定对象 ID',
    description: '订阅绑定的过滤器和排序器 ID。',
  },
  {
    key: 'subscribe_create_time / subscribe_update_time',
    label: '订阅时间',
    description: '订阅创建和更新时间。',
  },
]

const CAST_BASE_FIELDS: TemplateDocField[] = [
  {
    key: 'cast_id / cast_avatar / cast_photo',
    label: '演员基础信息',
    description: '演员主键、头像和照片地址。',
  },
  {
    key: 'cast_create_time / cast_update_time',
    label: '演员时间',
    description: '演员创建和更新时间。',
  },
]

const CAST_SUBSCRIBE_ID_FIELDS: TemplateDocField[] = [
  {
    key: 'cast_subscribe_id / cast_subscribe_cast_id',
    label: '演员订阅关联 ID',
    description: '演员订阅主键和关联演员主键。',
  },
  {
    key: 'cast_subscribe_filter_id / cast_subscribe_priority_id',
    label: '演员订阅绑定对象 ID',
    description: '演员订阅绑定的过滤器和排序器 ID。',
  },
  {
    key: 'cast_subscribe_create_time / cast_subscribe_update_time',
    label: '演员订阅时间',
    description: '演员订阅创建和更新时间。',
  },
]

// ============ 类型定义 ============

type TemplateDocField = {
  key: string
  label: string
  description: string
}

type TemplateDocGroup = {
  title: string
  fields: TemplateDocField[]
}

type TemplateDocConfig = {
  title: string
  description: string
  groups: TemplateDocGroup[]
}

const DOCS: Record<NotificationTemplateEventName, TemplateDocConfig> = {
  download: {
    title: '下载开始节点',
    description:
      '当文章成功创建下载任务时触发。下载节点已统一使用 article_* 和 download_* 命名。',
    groups: [
      {
        title: '常用字段',
        fields: [
          {
            key: 'article_title',
            label: '资源标题',
            description: '文章标题。',
          },
          {
            key: 'article_section / article_category',
            label: '分类信息',
            description: '文章所属板块和分类。',
          },
          { key: 'article_size', label: '资源大小', description: '文章大小。' },
          {
            key: 'article_publish_date',
            label: '发布时间',
            description: '文章发布时间，格式为 YYYY-MM-DD。',
          },
          {
            key: 'article_tid',
            label: '站点 ID',
            description: '文章在来源站点上的 tid。',
          },
          {
            key: 'article_website',
            label: '来源站点',
            description: '文章来源站点标识。',
          },
          {
            key: 'download_client',
            label: '下载器',
            description: '实际执行下载的客户端名称。',
          },
          {
            key: 'download_save_path',
            label: '保存路径',
            description: '本次下载使用的目标保存路径。',
          },
          {
            key: 'article_detail_url',
            label: '详情页',
            description: '文章详情链接。',
          },
        ],
      },
      {
        title: '补充字段',
        fields: [
          {
            key: 'article_magnet',
            label: '磁链数组',
            description: '文章原始磁链数组。',
          },
          { key: 'article_edk', label: 'ED2K', description: 'ED2K 链接数组。' },
          {
            key: 'article_match_number',
            label: '提取番号',
            description: '从标题中提取出的番号。',
          },
          {
            key: 'article_preview_images',
            label: '预览图数组',
            description: '文章预览图数组。',
          },
          {
            key: 'article_in_library',
            label: '是否在库',
            description: '布尔类型，表示文章是否已在媒体库中。',
          },
          {
            key: 'article_id',
            label: '文章主键',
            description: '本地 article 表主键。',
          },
          {
            key: 'article_create_time / article_update_time',
            label: '时间字段',
            description: '文章创建和更新时间。',
          },
        ],
      },
    ],
  },
  movie_subscribe: {
    title: '影片订阅节点',
    description:
      '新建影片订阅，或恢复已取消、已完成的影片订阅时触发。字段以 subscribe_service.py 中的推送 payload 为准。',
    groups: [
      {
        title: '常用字段',
        fields: [
          { key: 'movie_number', label: '影片番号', description: '影片番号。' },
          {
            key: 'movie_cn_title / movie_title',
            label: '影片标题',
            description:
              '中文标题与原始标题；如需展示标题请在模板里自行兜底，例如 movie_cn_title or movie_title or movie_number。',
          },
          {
            key: 'movie_release_date',
            label: '发布日期',
            description: '影片发行日期，格式为 YYYY-MM-DD。',
          },
          {
            key: 'movie_cast_names',
            label: '演员数组',
            description:
              '影片演员名称数组；需要文本时可使用 join，例如 movie_cast_names | join(" / ")。',
          },
          {
            key: 'subscribe_status',
            label: '订阅状态',
            description: '当前影片订阅状态。',
          },
          {
            key: 'subscribe_pre_download_enabled',
            label: '预下载状态',
            description: '是否允许预下载，值为 是/否。',
          },
          ...FILTER_PRIORITY_COMMON_FIELDS,
        ],
      },
      {
        title: '补充字段',
        fields: [
          ...MOVIE_BASE_FIELDS,
          ...SUBSCRIBE_ID_FIELDS,
          ...FILTER_ID_FIELDS,
          ...FILTER_RULE_FIELDS,
          ...PRIORITY_RULE_FIELDS,
        ],
      },
    ],
  },
  subscribe_completed: {
    title: '订阅完成节点',
    description:
      '影片因媒体库已存在，或成功命中资源并创建下载任务时触发。字段以 subscribe_service.py 中的推送 payload 为准。',
    groups: [
      {
        title: '常用字段',
        fields: [
          {
            key: 'completion_source',
            label: '完成来源',
            description: '当前可能为 library 或 download。',
          },
          { key: 'movie_number', label: '影片番号', description: '影片番号。' },
          {
            key: 'movie_cn_title / movie_title',
            label: '影片标题',
            description: '中文标题与原始标题；如需展示标题请在模板里自行兜底。',
          },
          {
            key: 'article_title / article_size / article_publish_date',
            label: '资源标题信息',
            description: '命中资源的标题、大小和发布时间。',
          },
          {
            key: 'article_detail_url',
            label: '详情链接',
            description: '资源文章详情页地址。',
          },
          {
            key: 'subscribe_status / subscribe_pre_download_enabled',
            label: '订阅状态',
            description: '推送时订阅状态和预下载状态；预下载值为 是/否。',
          },
          ...FILTER_PRIORITY_COMMON_FIELDS,
        ],
      },
      {
        title: '补充字段',
        fields: [
          {
            key: 'movie_id / movie_release_date / movie_duration',
            label: '影片基础信息',
            description: '影片主键、发布日期和片长。',
          },
          ...MOVIE_BASE_FIELDS,
          ...MOVIE_CAST_FIELDS,
          {
            key: 'article_id / article_tid / article_match_number',
            label: '资源标识',
            description: '本地文章主键、来源站点 tid 和匹配番号。',
          },
          {
            key: 'article_magnet / article_edk / article_preview_images',
            label: '资源数组字段',
            description: '磁链、ED2K 和预览图数组。',
          },
          {
            key: 'article_section / article_category / article_website',
            label: '资源分类',
            description: '文章板块、分类和来源站点。',
          },
          {
            key: 'article_in_library',
            label: '是否在库',
            description: '布尔类型，表示文章是否已在媒体库中。',
          },
          {
            key: 'article_create_time / article_update_time',
            label: '资源时间',
            description: '文章创建和更新时间。',
          },
          {
            key: 'subscribe_id / subscribe_movie_id / subscribe_filter_id / subscribe_priority_id',
            label: '订阅关联 ID',
            description: '订阅及其关联对象 ID。',
          },
          ...SUBSCRIBE_ID_FIELDS,
          {
            key: 'filter_id / filter_keyword / filter_resolutions / filter_subtitles / filter_mosaic',
            label: '过滤器规则',
            description: '过滤器 ID、关键词与各类规则；数组已拍平成字符串。',
          },
          {
            key: 'filter_min_size / filter_max_size / filter_skip_in_library_check / filter_enable_pre_download / filter_is_default',
            label: '过滤器补充项',
            description: '大小范围和布尔项；布尔值为 是/否。',
          },
          ...FILTER_RULE_FIELDS,
          {
            key: 'priority_id / priority_resolutions / priority_subtitles / priority_mosaic / priority_sort / priority_is_default',
            label: '排序器规则',
            description:
              '排序器 ID、规则与默认状态；数组已拍平成字符串，布尔值为 是/否。',
          },
          ...PRIORITY_RULE_FIELDS,
        ],
      },
    ],
  },
  cast_subscribe: {
    title: '演员订阅节点',
    description:
      '新建演员订阅，或恢复已取消的演员订阅时触发。字段以 subscribe_service.py 中的推送 payload 为准。',
    groups: [
      {
        title: '常用字段',
        fields: [
          {
            key: 'cast_cn_name / cast_name',
            label: '演员名称',
            description:
              '中文名与原名；如需展示名请在模板里自行兜底，例如 cast_cn_name or cast_name。',
          },
          {
            key: 'cast_former_name',
            label: '曾用名数组',
            description: '演员曾用名原始数组；需要文本时可使用 join。',
          },
          {
            key: 'cast_subscribe_earliest_release_date',
            label: '最早发行日期',
            description: '演员订阅设置的最早发行日期。',
          },
          {
            key: 'cast_subscribe_max_coactors / cast_subscribe_max_page / cast_subscribe_replace_max_page',
            label: '订阅约束',
            description: '共演人数、抓取页数和替换页数限制。',
          },
          {
            key: 'cast_subscribe_is_single / cast_subscribe_exclude_vr',
            label: '布尔项',
            description: '仅单体和排除 VR，值为 是/否。',
          },
          {
            key: 'cast_subscribe_status',
            label: '演员订阅状态',
            description: '当前演员订阅状态。',
          },
          ...FILTER_PRIORITY_COMMON_FIELDS,
        ],
      },
      {
        title: '补充字段',
        fields: [
          ...CAST_BASE_FIELDS,
          ...CAST_SUBSCRIBE_ID_FIELDS,
          ...FILTER_ID_FIELDS,
          ...FILTER_RULE_FIELDS,
          ...PRIORITY_RULE_FIELDS,
        ],
      },
    ],
  },
}

function NotificationTemplateDocsContent({
  eventName,
}: {
  eventName: NotificationTemplateEventName | null
}) {
  if (!eventName) {
    return (
      <Card className='border-dashed bg-muted/20'>
        <CardHeader>
          <CardTitle className='flex items-center gap-2 text-sm'>
            <Info className='h-4 w-4 text-primary' />
            模板说明
          </CardTitle>
          <CardDescription>
            点击左侧任意模板区域里的“模板说明”按钮，在这里查看对应节点可用的变量。
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const doc = DOCS[eventName]

  return (
    <div className='space-y-3'>
      <Card>
        <CardHeader>
          <CardTitle className='flex items-center gap-2 text-sm'>
            <Info className='h-4 w-4 text-primary' />
            {doc.title}变量说明
          </CardTitle>
          <CardDescription>{doc.description}</CardDescription>
        </CardHeader>
      </Card>
      {doc.groups.map((group) => (
        <Card key={group.title} className='gap-3 py-4'>
          <CardHeader className='px-4'>
            <CardTitle className='text-sm'>{group.title}</CardTitle>
            <CardDescription>模板中可直接使用下面这些字段。</CardDescription>
          </CardHeader>
          <CardContent className='space-y-2 px-4'>
            {group.fields.map((field) => (
              <div
                key={field.key}
                className='rounded-md border border-border/60 bg-background/70 px-3 py-2'
              >
                <div className='flex flex-wrap items-center gap-2'>
                  <code className='rounded bg-muted px-1.5 py-0.5 text-xs'>
                    {field.key}
                  </code>
                  <Badge variant='outline'>{field.label}</Badge>
                </div>
                <p className='mt-1 text-xs leading-5 text-muted-foreground'>
                  {field.description}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function NotificationTemplateDocsPanel({
  eventName,
}: {
  eventName: NotificationTemplateEventName | null
}) {
  return (
    <div className='max-h-full overflow-y-auto pr-1'>
      <NotificationTemplateDocsContent eventName={eventName} />
    </div>
  )
}

export function NotificationTemplateDocsPopoverContent({
  eventName,
}: {
  eventName: NotificationTemplateEventName
}) {
  return (
    <div className='max-h-[70vh] overflow-y-auto pr-1'>
      <NotificationTemplateDocsContent eventName={eventName} />
    </div>
  )
}
