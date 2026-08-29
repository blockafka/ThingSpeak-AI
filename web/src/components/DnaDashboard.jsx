import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

// DNA 素材库仪表盘：演示数据来自 6 个维度、每维度 20 条 Mock 片段。
const MOCK_DIMENSIONS = [
  { id: 'scene', name: '场景', top: '下班后附近餐饮推荐', top10Scores: [0.94, 0.92, 0.90, 0.88, 0.87, 0.85, 0.83, 0.81, 0.80, 0.78], status: 'rising', trend: [0.73, 0.74, 0.75, 0.78, 0.80, 0.84, 0.87] },
  { id: 'valuePromise', name: '价值承诺', top: '32元也能吃得满足', top10Scores: [0.92, 0.90, 0.88, 0.86, 0.85, 0.83, 0.81, 0.80, 0.78, 0.76], status: 'rising', trend: [0.69, 0.73, 0.76, 0.77, 0.77, 0.79, 0.84] },
  { id: 'hook', name: '开头钩子', top: '价格对比 + 结果反差', top10Scores: [0.96, 0.94, 0.92, 0.90, 0.88, 0.87, 0.85, 0.83, 0.81, 0.80], status: 'rising', trend: [0.86, 0.84, 0.85, 0.86, 0.88, 0.89, 0.93] },
  { id: 'structure', name: '内容结构', top: '反差开场 → 3个证据 → 到店建议', top10Scores: [0.93, 0.91, 0.90, 0.88, 0.86, 0.84, 0.82, 0.81, 0.79, 0.77], status: 'rising', trend: [0.71, 0.73, 0.77, 0.82, 0.83, 0.84, 0.86] },
  { id: 'tone', name: '表达语气', top: '第一人称、口语化、朋友推荐', top10Scores: [0.89, 0.87, 0.85, 0.83, 0.81, 0.79, 0.77, 0.75, 0.74, 0.72], status: 'rising', trend: [0.72, 0.70, 0.71, 0.75, 0.76, 0.80, 0.83] },
  { id: 'visualStyle', name: '视觉风格', top: '菜品近景首图，暖色自然光', top10Scores: [0.91, 0.89, 0.87, 0.85, 0.83, 0.81, 0.79, 0.78, 0.76, 0.74], status: 'rising', trend: [0.61, 0.67, 0.70, 0.76, 0.80, 0.81, 0.88] },
]

const average = (values) => values.reduce((sum, value) => sum + value, 0) / values.length
const OVERALL_TOP10_AVERAGE = average(MOCK_DIMENSIONS.flatMap(dimension => dimension.top10Scores))

const STATUS_LABELS = {
  rising: { label: '上升', icon: '↑', className: 'text-emerald-300 bg-emerald-400/15 border-emerald-400/20', color: '#34d399' },
  stable: { label: '平稳', icon: '→', className: 'text-slate-300 bg-slate-400/10 border-slate-400/15', color: '#94a3b8' },
}

function MiniTrendChart({ data, color = '#fbbf24', height = 34, width = 100 }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const horizontalPadding = 5
  const points = data.map((value, index) => [
    horizontalPadding + (index / (data.length - 1)) * (width - horizontalPadding * 2),
    height - ((value - min) / range) * (height - 4) - 2,
  ])
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(' ')
  return (
    <svg width={width} height={height} className="block" aria-hidden="true">
      <path d={`${path} L ${width - horizontalPadding} ${height} L ${horizontalPadding} ${height} Z`} fill={color} fillOpacity="0.08" />
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx={points.at(-1)[0]} cy={points.at(-1)[1]} r="2.5" fill={color} />
    </svg>
  )
}

function useCountUp(target, duration = 1000) {
  const [value, setValue] = useState(0)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    const start = performance.now()
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration])

  return value
}

function MetricCard({ icon, label, value, suffix, accent = 'amber', decimals = 0 }) {
  const animated = useCountUp(typeof value === 'number' ? value : 0)
  const colors = {
    amber: 'from-amber-400/20 to-amber-400/0 text-amber-300',
    rose: 'from-rose-400/20 to-rose-400/0 text-rose-300',
    emerald: 'from-emerald-400/20 to-emerald-400/0 text-emerald-300',
    sky: 'from-sky-400/20 to-sky-400/0 text-sky-300',
  }
  const display = typeof value === 'number'
    ? (decimals ? animated.toFixed(decimals) : Math.round(animated).toLocaleString())
    : value
  return (
    <div className="glass-card rounded-xl p-4 relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${colors[accent]} opacity-30 pointer-events-none`} />
      <div className="relative">
        <div className="flex items-center gap-2 mb-2">
          <span aria-hidden="true">{icon}</span>
          <span className="text-xs text-slate-400">{label}</span>
        </div>
        <div className="text-xl md:text-2xl font-bold text-white tabular-nums">
          {display}<span className="text-sm font-normal text-slate-400 ml-1">{suffix}</span>
        </div>
      </div>
    </div>
  )
}

function DimensionCard({ dimension, index }) {
  const status = STATUS_LABELS[dimension.status] || STATUS_LABELS.stable
  const top10Average = average(dimension.top10Scores)
  const [tooltipPosition, setTooltipPosition] = useState(null)

  const showTooltip = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setTooltipPosition({ left: rect.left, top: rect.bottom + 8 })
  }

  return (
    <div
      className="glass-card rounded-xl p-4 relative overflow-hidden transition-all duration-300 hover:scale-[1.02] hover:border-amber-400/30"
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <div className="flex items-center mb-2">
        <span className={`inline-flex shrink-0 items-center whitespace-nowrap text-[10px] px-2 py-0.5 rounded-full border font-medium ${status.className}`}>
          {status.icon}&nbsp;{status.label}
        </span>
      </div>
      <div className="text-xs font-semibold text-white mb-2">{dimension.name}</div>
      <div className="w-full">
        <div
          title={dimension.top}
          className="w-full truncate text-xs text-slate-300 leading-5 cursor-help"
          onMouseEnter={showTooltip}
          onMouseLeave={() => setTooltipPosition(null)}
        >
          {dimension.top}
        </div>
      </div>
      {tooltipPosition && createPortal(
        <div
          className="pointer-events-none fixed z-[100] max-w-64 rounded-lg border border-amber-300/20 bg-slate-950 px-3 py-2 text-xs leading-5 text-slate-100 shadow-xl"
          style={{ left: tooltipPosition.left, top: tooltipPosition.top }}
        >
          {dimension.top}
        </div>,
        document.body,
      )}
      <div className="flex items-end justify-between mt-3 pt-2 border-t border-white/5">
        <div>
          <div className="text-lg font-bold text-white">{top10Average.toFixed(2)}</div>
          <div className="text-[10px] text-slate-500">Top 10 平均分</div>
        </div>
        <MiniTrendChart data={dimension.trend} color={status.color} />
      </div>
    </div>
  )
}

export default function DnaDashboard() {
  return (
    <div className="glass-card rounded-2xl p-6 animate-fade-in-up">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400/30 to-rose-400/30 flex items-center justify-center text-base border border-amber-400/20">🧬</div>
          <div>
            <h2 className="text-sm font-semibold text-white">DNA素材库</h2>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <MetricCard icon="🧬" label="DNA 素材总数" value={120} suffix="条" accent="rose" />
        <MetricCard icon="🧩" label="维度数量" value={6} suffix="个" accent="amber" />
        <MetricCard icon="🎯" label="每维度候选" value={10} suffix="条" accent="sky" />
        <MetricCard icon="🏅" label="平均 Top 10 分数" value={OVERALL_TOP10_AVERAGE} suffix="" accent="emerald" decimals={2} />
      </div>

      <div className="flex items-center mb-3">
        <span className="text-xs font-medium text-slate-300">🔥 六维 DNA 素材</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {MOCK_DIMENSIONS.map((dimension, index) => (
          <DimensionCard key={dimension.id} dimension={dimension} index={index} />
        ))}
      </div>
    </div>
  )
}
