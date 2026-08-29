import { useEffect, useRef, useState } from 'react'

// ============================================================
// Mock 数据：10 种 DNA，取 Top 5 展示
// ============================================================
const MOCK_DNAS = [
  {
    id: 'bestie_travel_share',
    name: '闺蜜旅游分享风',
    status: 'rising',
    avgLikes: 12800,
    growthRate: 0.38,
    sampleCount: 286,
    avgCollectRatio: 2.7,
    trend: [8200, 9100, 8800, 10500, 11800, 12400, 12800],
    topKeywords: ['伴手礼', '宝藏', '闺蜜安利', '旅游必带'],
  },
  {
    id: 'gift_guide',
    name: '送礼实用攻略风',
    status: 'rising',
    avgLikes: 9600,
    growthRate: 0.22,
    sampleCount: 214,
    avgCollectRatio: 3.1,
    trend: [7600, 8200, 7900, 8500, 9000, 9300, 9600],
    topKeywords: ['送长辈', '实用礼物', '不踩雷', '节日礼盒'],
  },
  {
    id: 'local_recommend',
    name: '本地人良心推荐风',
    status: 'stable',
    avgLikes: 8400,
    growthRate: 0.08,
    sampleCount: 253,
    avgCollectRatio: 2.2,
    trend: [7800, 8000, 8200, 8100, 8300, 8400, 8400],
    topKeywords: ['本地人推荐', '避坑', '正宗', '老牌子'],
  },
  {
    id: 'healthy_snack',
    name: '健康零食测评风',
    status: 'rising',
    avgLikes: 7200,
    growthRate: 0.31,
    sampleCount: 168,
    avgCollectRatio: 2.9,
    trend: [5200, 4800, 5500, 6000, 6500, 6900, 7200],
    topKeywords: ['低卡', '无添加', '配料表', '减脂期'],
  },
  {
    id: 'cultural_story',
    name: '文艺治愈故事风',
    status: 'stable',
    avgLikes: 15200,
    growthRate: 0.05,
    sampleCount: 97,
    avgCollectRatio: 3.4,
    trend: [14800, 15000, 14700, 15100, 15300, 15200, 15200],
    topKeywords: ['老手艺', '古法', '非遗', '故事感'],
  },
  {
    id: 'weird_snack_review',
    name: '猎奇搞笑测评风',
    status: 'watching',
    avgLikes: 6800,
    growthRate: -0.12,
    sampleCount: 73,
    avgCollectRatio: 1.5,
    trend: [7800, 7600, 7400, 7200, 7000, 6900, 6800],
    topKeywords: ['黑暗料理', '测评', '猎奇', '奇葩'],
  },
  {
    id: 'unboxing_review',
    name: '沉浸式开箱风',
    status: 'rising',
    avgLikes: 5400,
    growthRate: 0.45,
    sampleCount: 42,
    avgCollectRatio: 1.8,
    trend: [3600, 3800, 4100, 4500, 4800, 5200, 5400],
    topKeywords: ['开箱', '沉浸式', '第一视角', '真实分享'],
  },
  {
    id: 'price_comparison',
    name: '性价比攻略风',
    status: 'stable',
    avgLikes: 4800,
    growthRate: 0.1,
    sampleCount: 58,
    avgCollectRatio: 2.5,
    trend: [4200, 4300, 4400, 4500, 4600, 4700, 4800],
    topKeywords: ['平价', '学生党', '囤货', '性价比'],
  },
  {
    id: 'office_snack',
    name: '办公室摸鱼风',
    status: 'watching',
    avgLikes: 3200,
    growthRate: -0.05,
    sampleCount: 34,
    avgCollectRatio: 1.6,
    trend: [3400, 3400, 3300, 3300, 3200, 3200, 3200],
    topKeywords: ['摸鱼', '办公室', '工位', '解腻'],
  },
  {
    id: 'recipe_inspiration',
    name: '创意食谱灵感风',
    status: 'rising',
    avgLikes: 4200,
    growthRate: 0.28,
    sampleCount: 51,
    avgCollectRatio: 3.6,
    trend: [3100, 3300, 3500, 3700, 3900, 4100, 4200],
    topKeywords: ['创意吃法', '食谱', '百搭', 'DIY'],
  },
]

// 按 7 天增长率排序取 Top 5
const TOP_DNAS = [...MOCK_DNAS]
  .sort((a, b) => b.growthRate - a.growthRate)
  .slice(0, 5)

// 汇总指标
const MOCK_SUMMARY = {
  totalNotes: 1247,
  weeklyNew: 86,
  totalDnas: 12,
  activeDnas: 8,
  watchingDnas: 3,
  retiredDnas: 9,
  lastUpdate: '3天前',
  lastVersion: 'v2.3',
  lastUpdateNote: '新增"沉浸式开箱" DNA',
  collectRatio: 2.4,
  industryRatio: 1.8,
  ratioImprovement: 0.33,
}

// ============================================================
// 状态标签
// ============================================================
const STATUS_LABELS = {
  rising: { label: '上升', icon: '↑', className: 'text-emerald-300 bg-emerald-400/15 border-emerald-400/20' },
  stable: { label: '平稳', icon: '→', className: 'text-slate-300 bg-slate-400/10 border-slate-400/15' },
  watching: { label: '观察', icon: '!', className: 'text-amber-300 bg-amber-400/15 border-amber-400/20' },
}

// ============================================================
// 迷你折线图组件（纯 SVG）
// ============================================================
function MiniTrendChart({ data, color = '#fbbf24', height = 36, width = 120 }) {
  if (!data || data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((val - min) / range) * (height - 4) - 2
    return [x, y]
  })

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`)
    .join(' ')

  const areaD = `${pathD} L ${width} ${height} L 0 ${height} Z`

  return (
    <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
      <defs>
        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#trendGrad)" />
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r="2.5" fill={color} />
    </svg>
  )
}

// ============================================================
// 数字滚动动画
// ============================================================
function useCountUp(target, duration = 1200) {
  const [value, setValue] = useState(0)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    const startTime = performance.now()
    const startVal = 0

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1)
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(startVal + (target - startVal) * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }

    requestAnimationFrame(tick)
  }, [target, duration])

  return value
}

// ============================================================
// 指标卡
// ============================================================
function MetricCard({ icon, label, value, valueSuffix, accent = 'amber' }) {
  const animatedValue = useCountUp(typeof value === 'number' ? value : 0)

  const accentClasses = {
    amber: 'from-amber-400/20 to-amber-400/0 text-amber-300',
    rose: 'from-rose-400/20 to-rose-400/0 text-rose-300',
    emerald: 'from-emerald-400/20 to-emerald-400/0 text-emerald-300',
    sky: 'from-sky-400/20 to-sky-400/0 text-sky-300',
  }[accent]

  const displayValue = typeof value === 'number' ? animatedValue.toLocaleString() : value

  return (
    <div className="glass-card rounded-xl p-4 relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${accentClasses} opacity-30 pointer-events-none`} />
      <div className="relative">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base" aria-hidden="true">{icon}</span>
          <span className="text-xs text-slate-400">{label}</span>
        </div>
        <div className="text-xl md:text-2xl font-bold text-white tabular-nums">
          {displayValue}
          {valueSuffix && <span className="text-sm font-normal text-slate-400 ml-1">{valueSuffix}</span>}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// DNA 活力卡
// ============================================================
function DnaVitalityCard({ dna, rank, index }) {
  const statusInfo = STATUS_LABELS[dna.status] || STATUS_LABELS.stable
  const [hovered, setHovered] = useState(false)

  // 折线颜色按状态
  const trendColor = dna.status === 'rising' ? '#34d399'  // emerald
    : dna.status === 'watching' ? '#fbbf24'                 // amber
    : '#94a3b8'                                                // slate

  // 入场动画延迟
  const animDelay = `${index * 80}ms`

  return (
    <div
      className="glass-card rounded-xl p-4 relative overflow-hidden cursor-default transition-all duration-300 hover:scale-[1.02] hover:border-amber-400/30 group"
      style={{ animationDelay: animDelay }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* 排名徽章 */}
      <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-amber-400/20 text-amber-300 text-xs font-bold flex items-center justify-center border border-amber-400/20">
        #{rank}
      </div>

      {/* 顶部：名称 + 状态标签 */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${statusInfo.className}`}>
          {statusInfo.icon} {statusInfo.label}
        </span>
      </div>
      <div className="text-xs font-semibold text-white mb-3 pr-8 truncate" title={dna.name}>
        {dna.name}
      </div>

      {/* 中部：迷你趋势图 + 赞藏比 */}
      <div className="flex items-end justify-between mb-3">
        <div>
          <div className="text-lg font-bold text-white tabular-nums">
            {dna.avgCollectRatio.toFixed(1)}
          </div>
          <div className="text-[10px] text-slate-500">赞藏比</div>
        </div>
        <MiniTrendChart data={dna.trend} color={trendColor} height={32} width={90} />
      </div>

      {/* 底部：样本量 + 增长率 */}
      <div className="flex items-center justify-between text-xs pt-2 border-t border-white/5">
        <span className="text-slate-500">
          <span className="text-slate-300 font-medium tabular-nums">{dna.sampleCount}</span> 篇样本
        </span>
        <span className={dna.growthRate >= 0 ? 'text-emerald-300 tabular-nums' : 'text-rose-300 tabular-nums'}>
          {dna.growthRate >= 0 ? '+' : ''}{(dna.growthRate * 100).toFixed(0)}%
        </span>
      </div>

      {/* 悬停详情 */}
      {hovered && (
        <div className="absolute inset-x-0 bottom-0 p-3 bg-[#1e1a22]/95 backdrop-blur-md border-t border-white/10 animate-fade-in-up rounded-b-xl z-10">
          <div className="text-[11px] text-slate-400 mb-1.5">TOP 关键词</div>
          <div className="flex flex-wrap gap-1">
            {dna.topKeywords.map((kw, i) => (
              <span
                key={i}
                className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-slate-300 border border-white/10"
              >
                {kw}
              </span>
            ))}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            赞藏比 1 : <span className="text-amber-300 font-medium">{dna.avgCollectRatio}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================
// 主组件
// ============================================================
export default function DnaDashboard() {
  return (
    <div className="glass-card rounded-2xl p-6 animate-fade-in-up">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400/30 to-rose-400/30 flex items-center justify-center text-base border border-amber-400/20">
            🧬
          </div>
          <h2 className="text-sm font-semibold text-white">爆款 DNA 实时更新</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-300 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            实时采集中
          </span>
        </div>
      </div>

      {/* 指标卡网格 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <MetricCard
          icon="📊"
          label="已分析爆文"
          value={MOCK_SUMMARY.totalNotes}
          valueSuffix="篇"
          accent="amber"
        />
        <MetricCard
          icon="🧬"
          label="DNA 总数"
          value={MOCK_SUMMARY.totalDnas}
          valueSuffix="种"
          accent="rose"
        />
        <MetricCard
          icon="⏰"
          label="最近更新时间"
          value={3}
          valueSuffix="天前"
          accent="sky"
        />
        <MetricCard
          icon="🏅"
          label="平均赞藏比"
          value={2.4}
          accent="emerald"
        />
      </div>

      {/* Top 5 DNA 活力榜 */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-medium text-slate-300">🔥 增长最快 Top 5</span>
        <span className="text-[10px] text-slate-500">按 7 天增长率排序</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {TOP_DNAS.map((dna, i) => (
          <DnaVitalityCard key={dna.id} dna={dna} rank={i + 1} index={i} />
        ))}
      </div>
    </div>
  )
}
