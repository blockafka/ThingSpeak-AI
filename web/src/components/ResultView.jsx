import { useState } from 'react'

const DNA_ROLE_LABELS = {
  primary: '主风格',
  supporting: '辅助风格',
}

function InfoCard({ title, value, accent = 'amber' }) {
  const accentClasses = accent === 'rose'
    ? 'border-rose-400/20 bg-rose-400/10 text-rose-100'
    : 'border-amber-400/20 bg-amber-400/10 text-amber-100'

  return (
    <div className={`rounded-2xl border p-4 ${accentClasses}`}>
      <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">{title}</div>
      <div className="text-sm md:text-base font-medium leading-relaxed">{value || '—'}</div>
    </div>
  )
}

function XhsPostCard({ post }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const fullText = `${post.title}\n\n${post.content}\n\n${(post.hashtags || []).map(t => `#${t}`).join(' ')}`
    try {
      await navigator.clipboard.writeText(fullText)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <span>📕</span>
          小红书笔记
        </h3>
        <button
          onClick={handleCopy}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            copied
              ? 'bg-green-500/20 text-green-300'
              : 'bg-amber-400/15 text-amber-200 hover:bg-amber-400/25'
          }`}
        >
          {copied ? '✓ 已复制全文' : '📋 复制全文'}
        </button>
      </div>

      {/* 标题 */}
      <div className="text-lg md:text-xl font-bold text-white mb-4 leading-snug">
        {post.title}
      </div>

      {/* 正文 */}
      <div className="text-sm leading-7 text-slate-200 whitespace-pre-line mb-4">
        {post.content}
      </div>

      {/* 标签 */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
        {(post.hashtags || []).map(tag => (
          <span
            key={tag}
            className="text-xs text-amber-300/90"
          >
            #{tag}
          </span>
        ))}
      </div>
    </div>
  )
}

function ImageSuggestions({ suggestions }) {
  if (!suggestions || suggestions.length === 0) return null

  return (
    <div className="glass-card rounded-2xl p-6">
      <h3 className="text-sm font-medium text-amber-300 mb-4">📸 笔记配图建议（{suggestions.length} 张）</h3>
      <div className="space-y-2">
        {suggestions.map((item, index) => (
          <div
            key={index}
            className="flex items-start gap-3 rounded-xl bg-white/5 border border-white/8 px-4 py-3"
          >
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-400/20 text-amber-300 text-xs font-bold shrink-0">
              {index + 1}
            </span>
            <p className="text-sm text-slate-200 leading-6">
              {item.content || item.description || item.content_type || item.text || item}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function DnaMatchPanel({ dnaMatches }) {
  if (!dnaMatches || dnaMatches.length === 0) return null

  return (
    <div className="glass-card rounded-2xl p-6">
      <h3 className="text-sm font-medium text-amber-300 mb-4">🧬 爆款 DNA 匹配</h3>
      <div className="space-y-2">
        {dnaMatches.map((dna, i) => {
          const isPrimary = dna.role === 'primary'
          const weight = Math.round((dna.weight || 0) * 100)
          return (
            <div
              key={dna.dna_id || i}
              className={`rounded-xl px-4 py-3 border ${
                isPrimary
                  ? 'bg-amber-400/10 border-amber-400/30'
                  : 'bg-white/5 border-white/10'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    isPrimary
                      ? 'bg-amber-400/20 text-amber-200'
                      : 'bg-white/10 text-slate-300'
                  }`}>
                    {DNA_ROLE_LABELS[dna.role] || dna.role}
                  </span>
                  <span className="text-sm font-medium text-white">
                    {dna.dna_name || dna.name || dna.dna_id}
                  </span>
                </div>
                <span className="text-xs text-slate-400 tabular-nums">{weight}% 权重</span>
              </div>
              {dna.reason && (
                <p className="text-xs text-slate-400 leading-5 mt-1">{dna.reason}</p>
              )}
              {/* 权重进度条 */}
              <div className="mt-2 h-1 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${isPrimary ? 'bg-amber-400' : 'bg-slate-400'}`}
                  style={{ width: `${weight}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ResultView({ result, elapsed, onReset }) {
  if (!result) return null

  const post = result.post || {}
  const imageSuggestions = result.image_suggestions || result.visual_suggestions || []
  const dnaMatches = result.dna_matches || []
  const keySellingPoints = result.key_selling_points || []

  const wordCount = (post.content || '').length

  return (
    <div className="animate-fade-in-up">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2">
            <span className="animate-bounce-once inline-block">✅</span>
            小红书笔记已生成
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            用时 {elapsed} 秒 · 约 {wordCount} 字 · {(post.hashtags || []).length} 个标签
          </p>
        </div>
        <button
          onClick={onReset}
          className="px-4 py-2 border border-white/10 rounded-lg text-sm text-slate-300 hover:bg-white/5 hover:border-white/20 transition-all"
        >
          重新生成
        </button>
      </div>

      {/* 核心数据卡片 */}
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <InfoCard
          title="主爆款 DNA"
          value={dnaMatches[0]?.dna_name || dnaMatches[0]?.name || dnaMatches[0]?.dna_id || '—'}
          accent="rose"
        />
        <InfoCard
          title="核心卖点"
          value={keySellingPoints.length > 0 ? `${keySellingPoints.length} 个` : '—'}
        />
        <InfoCard
          title="笔记配图"
          value={imageSuggestions.length > 0 ? `${imageSuggestions.length} 张图` : '—'}
        />
      </div>

      {/* 主体内容 */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-6 mb-6">
        {/* 左侧：小红书笔记 */}
        <div className="space-y-6">
          <XhsPostCard post={post} />
          <ImageSuggestions suggestions={imageSuggestions} />
        </div>

        {/* 右侧：DNA匹配 + 卖点 */}
        <div className="space-y-6">
          <DnaMatchPanel dnaMatches={dnaMatches} />

          {keySellingPoints.length > 0 && (
            <div className="glass-card rounded-2xl p-6">
              <h3 className="text-sm font-medium text-amber-300 mb-4">💡 核心卖点</h3>
              <div className="flex flex-wrap gap-2">
                {keySellingPoints.map((point, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 rounded-full text-sm bg-amber-400/15 text-amber-100 border border-amber-400/20"
                  >
                    {point}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
