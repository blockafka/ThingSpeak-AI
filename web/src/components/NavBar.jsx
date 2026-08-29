export default function NavBar() {
  return (
    <nav className="border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-amber-300 text-xl">✦</span>
          <span className="font-semibold text-white text-lg">物言测试版</span>
          <span className="text-xs text-slate-500 ml-2 hidden sm:inline">家乡特产小红书笔记一键生成</span>
        </div>
      </div>
    </nav>
  )
}
