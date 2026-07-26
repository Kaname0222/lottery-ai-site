export default function Leaderboard({ scores }) {
  if (!scores || scores.length === 0) {
    return <div className="text-sm text-gray-500">暂无评分数据</div>
  }

  const formatPoints = (value) => {
    const num = Number(value)
    return Number.isFinite(num) ? num.toFixed(2) : value
  }

  // 排名规则：有预测记录的排在前面；同记录数先看其他玩法积分，再看方向玩法积分
  const sortedScores = [...scores].sort((a, b) => {
    const aHas = (a.total_predictions || 0) > 0
    const bHas = (b.total_predictions || 0) > 0
    if (aHas !== bHas) return aHas ? -1 : 1
    const otherDiff = Number(b.other_points || 0) - Number(a.other_points || 0)
    if (otherDiff !== 0) return otherDiff
    return Number(b.direction_points || 0) - Number(a.direction_points || 0)
  })

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-4 py-3 border-b font-semibold text-gray-800">AI 排行榜</div>
      <div className="text-xs text-gray-500 px-4 py-1 bg-gray-50 border-b">
        排名：其他积分优先，同分看方向积分
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs whitespace-nowrap">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-2 py-2 text-left">排名</th>
              <th className="px-2 py-2 text-left">模型</th>
              <th className="px-2 py-2 text-right text-blue-700">其他积分</th>
              <th className="px-2 py-2 text-right text-green-700">方向积分</th>
              <th className="px-2 py-2 text-right">总积分</th>
              <th className="px-2 py-2 text-right">预测场数</th>
              <th className="px-2 py-2 text-right">命中其他</th>
              <th className="px-2 py-2 text-right">命中方向</th>
              <th className="px-2 py-2 text-right">准确率</th>
            </tr>
          </thead>
          <tbody>
            {sortedScores.map((s, idx) => (
              <tr key={s.provider_id} className="border-t">
                <td className="px-2 py-2 font-medium">{idx + 1}</td>
                <td className="px-2 py-2">{s.provider_display_name}</td>
                <td className="px-2 py-2 text-right font-bold text-blue-600">
                  {formatPoints(s.other_points)}
                </td>
                <td className="px-2 py-2 text-right font-bold text-green-600">
                  {formatPoints(s.direction_points)}
                </td>
                <td className="px-2 py-2 text-right">{formatPoints(s.total_points)}</td>
                <td className="px-2 py-2 text-right">{s.total_predictions}</td>
                <td className="px-2 py-2 text-right">{s.correct_predictions}</td>
                <td className="px-2 py-2 text-right">{s.direction_correct_predictions}</td>
                <td className="px-2 py-2 text-right">{(s.accuracy_rate * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
