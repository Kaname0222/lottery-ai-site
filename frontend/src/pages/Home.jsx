import { useEffect, useState } from 'react'
import Header from '../components/Header'
import FilterBar from '../components/FilterBar'
import MatchCard from '../components/MatchCard'
import Leaderboard from '../components/Leaderboard'
import MarketLeaderboard from '../components/MarketLeaderboard'
import ManualPredictionModal from '../components/ManualPredictionModal'
import {
  fetchDashboard,
  fetchMatches,
  runScrape,
  runPredictions,
  runScoring,
  finishMatches,
  fetchScoreLeaderboard,
  fetchTotalGoalsLeaderboard,
  fetchHalfFullLeaderboard,
} from '../api/client'
import { batchImportManualPredictions, AI_PROVIDER_OPTIONS } from '../utils/prediction'

export default function Home() {
  const [dashboard, setDashboard] = useState(null)
  const [matches, setMatches] = useState([])
  const [leagues, setLeagues] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ includeCompleted: false, personalNotPredicted: false })
  const [showImport, setShowImport] = useState(false)
  const [importText, setImportText] = useState('')
  const [importProvider, setImportProvider] = useState('gemini')
  const [importResult, setImportResult] = useState(null)
  const [showManualModal, setShowManualModal] = useState(false)
  const [scoreLeaderboard, setScoreLeaderboard] = useState(null)
  const [totalGoalsLeaderboard, setTotalGoalsLeaderboard] = useState(null)
  const [halfFullLeaderboard, setHalfFullLeaderboard] = useState(null)

  const loadDashboard = async () => {
    try {
      const { data } = await fetchDashboard()
      setDashboard(data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadMarketLeaderboards = async () => {
    try {
      const [score, totalGoals, halfFull] = await Promise.all([
        fetchScoreLeaderboard(),
        fetchTotalGoalsLeaderboard(),
        fetchHalfFullLeaderboard(),
      ])
      setScoreLeaderboard(score.data)
      setTotalGoalsLeaderboard(totalGoals.data)
      setHalfFullLeaderboard(halfFull.data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadMatches = async (params = {}) => {
    setLoading(true)
    try {
      const { data } = await fetchMatches(params)
      setMatches(data)
      const uniqueLeagues = Array.from(new Set(data.map((m) => m.league)))
      setLeagues(uniqueLeagues)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
    loadMatches()
    loadMarketLeaderboards()
  }, [])

  const buildParams = (f) => {
    const params = { include_completed: f.includeCompleted || false }
    if (f.date) params.match_date = f.date
    if (f.league) params.league = f.league
    if (f.personalNotPredicted) params.personal_not_predicted = true
    return params
  }

  const handleFilter = (f) => {
    setFilters(f)
    loadMatches(buildParams(f))
  }

  const handleRefresh = () => {
    loadDashboard()
    loadMatches(buildParams(filters))
    loadMarketLeaderboards()
  }

  const handleRunScrape = async () => {
    try {
      await runScrape()
      alert('抓取完成')
      handleRefresh()
    } catch (err) {
      alert('抓取失败')
    }
  }

  const handleRunPredictions = async () => {
    try {
      await runPredictions()
      alert('预测任务已触发')
      handleRefresh()
    } catch (err) {
      alert('预测失败')
    }
  }

  const handleRunScoring = async () => {
    try {
      await runScoring()
      alert('评分完成')
      handleRefresh()
    } catch (err) {
      alert('评分失败')
    }
  }

  const handleFinishMatches = async () => {
    try {
      const { data } = await finishMatches()
      alert(`一键完赛完成，更新 ${data.scored_count || 0} 场`)
      handleRefresh()
    } catch (err) {
      alert('一键完赛失败')
    }
  }

  const handleBatchImport = () => {
    const result = batchImportManualPredictions(importProvider, importText)
    setImportResult(result)
    if (result.failed.length === 0) {
      handleRefresh()
    }
  }

  return (
    <div className="min-h-screen pb-10">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500">今日比赛</div>
              <div className="text-2xl font-bold">{dashboard.total_matches}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500">已预测</div>
              <div className="text-2xl font-bold text-success">{dashboard.predicted_matches}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500">待预测</div>
              <div className="text-2xl font-bold text-warning">{dashboard.pending_matches}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow flex items-center gap-2">
              <button
                onClick={handleRunScrape}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-xs py-2 rounded"
              >
                手动抓取
              </button>
              <button
                onClick={handleRunPredictions}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-xs py-2 rounded"
              >
                手动预测
              </button>
              <button
                onClick={handleRunScoring}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-xs py-2 rounded"
              >
                手动评分
              </button>
              <button
                onClick={handleFinishMatches}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white text-xs py-2 rounded font-medium"
              >
                一键完赛
              </button>
              <button
                onClick={() => setShowImport(true)}
                className="flex-1 bg-green-100 hover:bg-green-200 text-green-800 text-xs py-2 rounded"
              >
                批量导入
              </button>
            </div>
          </div>
        )}

        {showImport && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="p-4 border-b flex items-center justify-between">
                <div className="font-bold text-gray-800">批量导入手动 AI 预测</div>
                <button onClick={() => setShowImport(false)} className="text-gray-500 hover:text-gray-700">✕</button>
              </div>
              <div className="p-4 space-y-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-600">AI 类型</span>
                  <select
                    value={importProvider}
                    onChange={(e) => setImportProvider(e.target.value)}
                    className="border rounded px-2 py-1"
                  >
                    {AI_PROVIDER_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder={`每行一条，格式：\n周六201韩职金泉尚武 VS 大田市民平胜、胜胜1-0、2-1\n周六202韩职浦项制铁 VS 全北现代平平、平负1-1、1-2`}
                  className="w-full h-64 border rounded p-3 text-xs font-mono"
                />
                {importResult && (
                  <div className={`text-sm ${importResult.failed.length > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    成功导入 {importResult.imported} 条
                    {importResult.failed.length > 0 && (
                      <div className="mt-1">
                        失败 {importResult.failed.length} 条：
                        <ul className="list-disc list-inside mt-1 text-xs">
                          {importResult.failed.slice(0, 5).map((line, i) => (
                            <li key={i}>{line}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="p-4 border-t flex justify-end gap-2">
                <button
                  onClick={() => setShowImport(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded"
                >
                  关闭
                </button>
                <button
                  onClick={handleBatchImport}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                >
                  导入
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <div className="flex items-end justify-between mb-4">
              <FilterBar onFilter={handleFilter} onRefresh={handleRefresh} leagues={leagues} />
              <button
                type="button"
                onClick={() => setShowManualModal(true)}
                className="ml-4 bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 whitespace-nowrap"
              >
                手动 AI 预测
              </button>
            </div>
            {loading ? (
              <div className="text-center py-10 text-gray-500">加载中...</div>
            ) : matches.length === 0 ? (
              <div className="text-center py-10 text-gray-500">暂无比赛数据，请点击“手动抓取”</div>
            ) : (
              matches.map((match) => (
                <MatchCard key={match.id} match={match} onUpdate={handleRefresh} />
              ))
            )}
          </div>
          <div className="lg:col-span-1 space-y-6">
            {dashboard && <Leaderboard scores={dashboard.provider_scores} />}
            {scoreLeaderboard && <MarketLeaderboard title="比分排行榜" scores={scoreLeaderboard} />}
            {totalGoalsLeaderboard && <MarketLeaderboard title="总进球数排行榜" scores={totalGoalsLeaderboard} />}
            {halfFullLeaderboard && <MarketLeaderboard title="半全场排行榜" scores={halfFullLeaderboard} />}
          </div>
        </div>

        {showManualModal && (
          <ManualPredictionModal
            matches={matches}
            onClose={() => setShowManualModal(false)}
            onSuccess={handleRefresh}
          />
        )}
      </main>
    </div>
  )
}
