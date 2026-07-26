import { useState } from 'react'

export default function FilterBar({ onFilter, onRefresh, leagues }) {
  const [date, setDate] = useState('')
  const [league, setLeague] = useState('')
  const [includeCompleted, setIncludeCompleted] = useState(false)
  const [personalNotPredicted, setPersonalNotPredicted] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    onFilter({ date, league, includeCompleted, personalNotPredicted })
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-4 rounded-lg shadow mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label className="block text-xs text-gray-500 mb-1">日期</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">联赛</label>
        <select
          value={league}
          onChange={(e) => setLeague(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-w-[120px]"
        >
          <option value="">全部</option>
          {leagues.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>
      </div>
      <label className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={includeCompleted}
          onChange={(e) => setIncludeCompleted(e.target.checked)}
          className="rounded border-gray-300 text-primary focus:ring-primary"
        />
        显示已完赛
      </label>
      <label className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={personalNotPredicted}
          onChange={(e) => setPersonalNotPredicted(e.target.checked)}
          className="rounded border-gray-300 text-primary focus:ring-primary"
        />
        个人未预测
      </label>
      <button
        type="submit"
        className="bg-primary text-white px-4 py-1.5 rounded text-sm hover:bg-primary/90 transition"
      >
        筛选
      </button>
      <button
        type="button"
        onClick={onRefresh}
        className="ml-auto border border-gray-300 text-gray-700 px-4 py-1.5 rounded text-sm hover:bg-gray-50 transition"
      >
        刷新
      </button>
    </form>
  )
}
