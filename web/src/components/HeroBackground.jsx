import { useEffect, useState } from 'react'

const FOOD_IMAGES = [
  'https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?w=1200&q=60',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200&q=60',
  'https://images.unsplash.com/photo-1547592180-85f173990554?w=1200&q=60',
  'https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?w=1200&q=60',
  'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=1200&q=60',
  'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1200&q=60',
]

const PARAMS = {
  imageOpacity: 0.34,
  imageFilter: 'blur(2px) saturate(1.05) contrast(1.02)',
  gridOpacity: 0.12,
}

export default function HeroBackground({ static: isStatic = false }) {
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (isStatic) return
    const timeout = setTimeout(() => {
      setCurrentIndex(prev => (prev + 1) % FOOD_IMAGES.length)
    }, 1200)
    const interval = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % FOOD_IMAGES.length)
    }, 4500)
    return () => {
      clearTimeout(timeout)
      clearInterval(interval)
    }
  }, [isStatic])

  return (
    <div className="fixed inset-0 z-0 overflow-hidden bg-[#0a0810]">
      {FOOD_IMAGES.map((url, i) => (
        <div
          key={i}
          className="absolute inset-0 bg-cover bg-center transition-opacity duration-[1200ms] ease-in-out"
          style={{
            backgroundImage: `url(${url})`,
            opacity: i === currentIndex ? PARAMS.imageOpacity : 0,
            filter: PARAMS.imageFilter,
            transform: 'scale(1.05)',
          }}
        />
      ))}

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(250,204,21,0.12),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(249,115,22,0.14),transparent_34%),linear-gradient(180deg,rgba(5,5,10,0.55),rgba(5,5,10,0.82))]" />

      <div
        className="absolute inset-0"
        style={{
          opacity: PARAMS.gridOpacity,
          backgroundImage:
            'linear-gradient(rgba(251, 191, 36, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(251, 191, 36, 0.08) 1px, transparent 1px)',
          backgroundSize: '88px 88px',
        }}
      />
    </div>
  )
}
