export default function MarketLeaderboard({ title, scores }) {
  if (!scores || scores.length === 0) {
    return <div className="text-sm text-gray-500">暂无评分数据</div>
  }

  const formatPoints = (value) => {
    const num = Number(value)
    return Number.isFinite(num) ? num.toFixed(2) : value
  }

  const sortedScores = [...scores].sort((a, b) => {
    const pointsDiff = Number(b.total_points || 0) - Number(a.total_points || 0)
    if (pointsDiff !== 0) return pointsDiff
    return Number(b.correct_predictions || 0) - Number(a.correct_predictions || 0)
  })

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-4 py-3 border-b font-semibold text-gray-800">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs whitespace-nowrap">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-2 py-2 text-left">排名</th>
              <th className="px-2 py-2 text-left">模型</th>
              <th className="px-2 py-2 text-right">积分</th>
              <th className="px-2 py-2 text-right">预测场数</th>
              <th className="px-2 py-2 text-right">命中</th>
              <th className="px-2 py-2 text-right">准确率</th>
            </tr>
          </thead>
          <tbody>
            {sortedScores.map((s, idx) => (
              <tr key={s.provider_id} className="border-t">
                <td className="px-2 py-2 font-medium">{idx + 1}</td>
                <td className="px-2 py-2">{s.provider_display_name}</td>
                <td className="px-2 py-2 text-right font-bold">{formatPoints(s.total_points)}</td>
                <td className="px-2 py-2 text-right">{s.total_predictions}</td>
                <td className="px-2 py-2 text-right">{s.correct_predictions}</td>
                <td className="px-2 py-2 text-right">{(s.accuracy_rate * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
