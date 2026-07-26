import { useEffect, useState } from 'react'
import PredictionList from './PredictionList'
import { submitResult, submitPersonalPrediction } from '../api/client'
import {
  getUserPredictions,
  loadPersonalPrediction,
  savePersonalPrediction,
  buildPersonalPredictionPayload,
  HALF_FULL_OPTIONS,
} from '../utils/prediction'

function OddsTable({ title, headers, rows, highlightFn }) {
  return (
    <div className="bg-gray-50 rounded p-3">
      <div className="text-xs font-bold text-gray-700 mb-2">{title}</div>
      <table className="w-full text-xs text-center">
        <thead>
          <tr className="text-gray-500">
            {headers.map((h, i) => (
              <th key={i} className="py-1 font-normal">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => {
                const isHighlighted = highlightFn ? highlightFn(cell, ci) : false
                return (
                  <td
                    key={ci}
                    className={`py-1 px-1 rounded ${isHighlighted ? 'bg-primary/10 text-primary font-semibold' : ''}`}
                  >
                    {cell}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OddsTags({ title, oddsMap, maxItems = 999 }) {
  if (!oddsMap || Object.keys(oddsMap).length === 0) return null
  const entries = Object.entries(oddsMap).slice(0, maxItems)
  return (
    <div className="bg-gray-50 rounded p-3">
      <div className="text-xs font-bold text-gray-700 mb-2">{title}</div>
      <div className="flex flex-wrap gap-2">
        {entries.map(([k, v]) => (
          <span key={k} className="text-xs bg-white border rounded px-2 py-1">
            {k} <span className="text-primary font-semibold">{v}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function NumberInput({ value, onChange, placeholder }) {
  return (
    <input
      type="number"
      min="0"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border rounded w-14 px-2 py-1 text-center"
      placeholder={placeholder}
    />
  )
}

export default function MatchCard({ match, onUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const [homeScore, setHomeScore] = useState('')
  const [awayScore, setAwayScore] = useState('')
  const [actualHalfFull, setActualHalfFull] = useState('')
  const [loading, setLoading] = useState(false)

  const [personalHalfFull, setPersonalHalfFull] = useState('')
  const [personalHalfFull2, setPersonalHalfFull2] = useState('')
  const [ft1Home, setFt1Home] = useState('')
  const [ft1Away, setFt1Away] = useState('')
  const [ft2Home, setFt2Home] = useState('')
  const [ft2Away, setFt2Away] = useState('')

  const predictionsByProvider = match.predictions_by_provider || []
  const providerOrder = ['GPT', 'Gemini', 'DeepSeek', 'Kimi', '豆包', '千问', '个人预测']
  const sorted = providerOrder
    .map((name) => predictionsByProvider.find((p) => p.provider_display_name === name || p.provider_display_name === `${name}（手动）`))
    .filter(Boolean)

  // 其余 provider（含手动导入）按原顺序追加
  const displayList = [...sorted]
  predictionsByProvider.forEach((p) => {
    if (!displayList.find((item) => item.provider_id === p.provider_id)) {
      displayList.push(p)
    }
  })

  useEffect(() => {
    const saved = loadPersonalPrediction(match.match_id)
    if (saved) {
      setPersonalHalfFull(saved.halfFull ?? '')
      setPersonalHalfFull2(saved.halfFull2 ?? '')
      setFt1Home(saved.ft1Home ?? '')
      setFt1Away(saved.ft1Away ?? '')
      setFt2Home(saved.ft2Home ?? '')
      setFt2Away(saved.ft2Away ?? '')
    }
  }, [match.match_id])

  const handleSavePersonal = async () => {
    savePersonalPrediction(match.match_id, {
      halfFull: personalHalfFull,
      halfFull2: personalHalfFull2,
      ft1Home,
      ft1Away,
      ft2Home,
      ft2Away,
    })
    // 同步到后端，参与排行榜评分
    const payload = buildPersonalPredictionPayload(
      personalHalfFull,
      personalHalfFull2,
      ft1Home,
      ft1Away,
      ft2Home,
      ft2Away
    )
    if (payload) {
      try {
        await submitPersonalPrediction(match.match_id, payload)
        if (onUpdate) onUpdate()
      } catch (err) {
        console.error('同步个人预测失败', err)
      }
    }
  }

  const userPredictions = getUserPredictions(
    personalHalfFull,
    personalHalfFull2,
    ft1Home,
    ft1Away,
    ft2Home,
    ft2Away,
    match.handicap
  )

  const handleSubmitResult = async (e) => {
    e.preventDefault()
    if (homeScore === '' || awayScore === '') return
    setLoading(true)
    try {
      await submitResult(match.match_id, parseInt(homeScore), parseInt(awayScore), actualHalfFull || null)
      setHomeScore('')
      setAwayScore('')
      setActualHalfFull('')
      onUpdate()
    } catch (err) {
      alert('提交比分失败')
    } finally {
      setLoading(false)
    }
  }

  // 后端存储的是北京时间（naive datetime），这里强制按 Asia/Shanghai 解析和展示，
  // 避免浏览器时区非北京时间时显示错位。
  const formatBeijingTime = (isoString) => {
    if (!isoString) return '未知'
    const beijingIso = isoString.replace(' ', 'T').replace(/Z$/, '') + '+08:00'
    return new Date(beijingIso).toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const matchTime = match.match_time ? formatBeijingTime(match.match_time) : '未知'

  // 比分赔率分组
  const scoreOdds = match.score_odds || {}
  const homeWinScores = Object.entries(scoreOdds).filter(([k]) => k.startsWith('胜') || (k.includes(':') && parseInt(k.split(':')[0]) > parseInt(k.split(':')[1])))
  const drawScores = Object.entries(scoreOdds).filter(([k]) => k.startsWith('平') || (k.includes(':') && parseInt(k.split(':')[0]) === parseInt(k.split(':')[1])))
  const awayWinScores = Object.entries(scoreOdds).filter(([k]) => k.startsWith('负') || (k.includes(':') && parseInt(k.split(':')[0]) < parseInt(k.split(':')[1])))

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-4">
      <div
        className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <div className="text-xs text-gray-500 mb-1">
            {match.league} · {matchTime} · 编号 {match.match_id}
          </div>
          <div className="text-lg font-bold text-gray-900">
            {match.home_team} <span className="text-primary">VS</span> {match.away_team}
          </div>
        </div>
        <div className="text-sm text-gray-600 space-y-1">
          {match.odds_home_win && (
            <div>
              胜平负：主胜 {match.odds_home_win} / 平 {match.odds_draw} / 客胜 {match.odds_away_win}
            </div>
          )}
          {match.odds_hhad_home_win && (
            <div>
              让球{match.handicap}：主胜 {match.odds_hhad_home_win} / 平 {match.odds_hhad_draw} / 客胜 {match.odds_hhad_away_win}
            </div>
          )}
          {match.support_home !== null && match.support_home !== undefined && (
            <div>
              支持率：主 {match.support_home}% / 平 {match.support_draw}% / 客 {match.support_away}%
            </div>
          )}
          {match.actual_home_score !== null && match.actual_home_score !== undefined && (
            <div className="font-bold text-success">
              实际比分：{match.actual_home_score} : {match.actual_away_score}
              {match.actual_half_full && <span className="ml-2">半全场：{match.actual_half_full}</span>}
            </div>
          )}
          <div className="text-xs text-primary">
            {expanded ? '▲ 收起赔率' : '▼ 展开全部赔率'}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <OddsTable
            title="胜平负"
            headers={['主胜', '平', '客胜']}
            rows={[[match.odds_home_win, match.odds_draw, match.odds_away_win]]}
          />
          <OddsTable
            title={`让球胜平负 (${match.handicap || '-'})`}
            headers={['主胜', '平', '客胜']}
            rows={[[match.odds_hhad_home_win, match.odds_hhad_draw, match.odds_hhad_away_win]]}
          />
          <OddsTags title="总进球数" oddsMap={match.total_goals_odds} />
          <OddsTags title="半全场" oddsMap={match.half_full_odds} />
          {Object.keys(scoreOdds).length > 0 && (
            <div className="md:col-span-2 bg-gray-50 rounded p-3">
              <div className="text-xs font-bold text-gray-700 mb-2">比分赔率</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <div className="text-xs text-gray-500 mb-1">主胜</div>
                  <div className="flex flex-wrap gap-1">
                    {homeWinScores.map(([k, v]) => (
                      <span key={k} className="bg-white border rounded px-1.5 py-0.5">{k} <span className="text-primary font-semibold">{v}</span></span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">平局</div>
                  <div className="flex flex-wrap gap-1">
                    {drawScores.map(([k, v]) => (
                      <span key={k} className="bg-white border rounded px-1.5 py-0.5">{k} <span className="text-primary font-semibold">{v}</span></span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">客胜</div>
                  <div className="flex flex-wrap gap-1">
                    {awayWinScores.map(([k, v]) => (
                      <span key={k} className="bg-white border rounded px-1.5 py-0.5">{k} <span className="text-primary font-semibold">{v}</span></span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-4 pt-4 border-t">
        <div className="bg-blue-50 border border-blue-100 rounded p-3 mb-3">
          <div className="text-xs font-bold text-blue-800 mb-2">我的预测</div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-gray-600">半全场1</span>
            <select
              value={personalHalfFull}
              onChange={(e) => setPersonalHalfFull(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              {HALF_FULL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <span className="text-gray-600 ml-2">全场比分1</span>
            <NumberInput value={ft1Home} onChange={setFt1Home} placeholder="主" />
            <span>:</span>
            <NumberInput value={ft1Away} onChange={setFt1Away} placeholder="客" />
            <span className="text-gray-600 ml-2">半全场2</span>
            <select
              value={personalHalfFull2}
              onChange={(e) => setPersonalHalfFull2(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              {HALF_FULL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <span className="text-gray-600 ml-2">全场比分2</span>
            <NumberInput value={ft2Home} onChange={setFt2Home} placeholder="主" />
            <span>:</span>
            <NumberInput value={ft2Away} onChange={setFt2Away} placeholder="客" />
            <button
              type="button"
              onClick={handleSavePersonal}
              className="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700"
            >
              保存
            </button>
          </div>
          {userPredictions && userPredictions.length > 0 && (
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              {userPredictions.map((scenario, idx) => (
                <div key={idx} className="bg-white rounded px-2 py-1">
                  <span className="text-gray-500">场景 {idx + 1}：</span>
                  <span className="font-semibold text-blue-700">{scenario['比分']}</span>
                  <span className="text-gray-400 mx-1">|</span>
                  <span className="font-semibold text-blue-700">{scenario['半全场']}</span>
                  <span className="text-gray-400 mx-1">|</span>
                  <span className="font-semibold text-blue-700">{scenario['胜平负']}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-2">
          {displayList.map((provider) => (
            <PredictionList
              key={provider.provider_id}
              providerName={provider.provider_display_name}
              predictions={provider.predictions}
              match={match}
              userPredictions={userPredictions}
            />
          ))}
        </div>
      </div>

      {match.actual_home_score === null || match.actual_home_score === undefined ? (
        <form onSubmit={handleSubmitResult} className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-gray-500">回填实际比分：</span>
          <input
            type="number"
            min="0"
            value={homeScore}
            onChange={(e) => setHomeScore(e.target.value)}
            className="border rounded w-16 px-2 py-1"
            placeholder="主"
          />
          <span>:</span>
          <input
            type="number"
            min="0"
            value={awayScore}
            onChange={(e) => setAwayScore(e.target.value)}
            className="border rounded w-16 px-2 py-1"
            placeholder="客"
          />
          <span className="text-gray-500 ml-2">半全场</span>
          <select
            value={actualHalfFull}
            onChange={(e) => setActualHalfFull(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            {HALF_FULL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={loading}
            className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-700 disabled:opacity-50"
          >
            提交并评分
          </button>
        </form>
      ) : null}
    </div>
  )
}
