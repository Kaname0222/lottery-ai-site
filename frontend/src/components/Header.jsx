import { FaFutbol } from 'react-icons/fa'

export default function Header() {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FaFutbol className="text-primary text-2xl" />
          <h1 className="text-xl font-bold text-gray-900">体彩竞彩 AI 比分预测</h1>
        </div>
        <div className="text-sm text-gray-500">每日自动抓取 · 五家大模型 · 积分排行</div>
      </div>
      <div className="bg-warning/10 border-b border-warning/20">
        <div className="max-w-7xl mx-auto px-4 py-2 text-xs text-warning">
          <strong>免责声明：</strong>本站所有 AI 预测仅供娱乐与研究，不构成任何投注建议。竞彩足球存在风险，请理性对待。
        </div>
      </div>
    </header>
  )
}
