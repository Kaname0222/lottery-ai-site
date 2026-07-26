import { useState } from 'react'
import { AI_PROVIDER_OPTIONS, HALF_FULL_OPTIONS } from '../utils/prediction'
import { submitManualPrediction } from '../api/client'

function NumberInput({ value, onChange, placeholder }) {
  return (
    <input
      type="number"
      min={0}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-14 border rounded px-2 py-1 text-sm text-center focus:outline-none focus:ring-2 focus:ring-primary"
    />
  )
}

export default function ManualPredictionModal({ matches, onClose, onSuccess }) {
  const [matchId, setMatchId] = useState('')
  const [provider, setProvider] = useState('deepseek')
  const [halfFull1, setHalfFull1] = useState('')
  const [halfFull2, setHalfFull2] = useState('')
  const [ft1Home, setFt1Home] = useState('')
  const [ft1Away, setFt1Away] = useState('')
  const [ft2Home, setFt2Home] = useState('')
  const [ft2Away, setFt2Away] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const s1h = parseInt(ft1Home, 10)
    const s1a = parseInt(ft1Away, 10)
    const s2h = parseInt(ft2Home, 10)
    const s2a = parseInt(ft2Away, 10)

    if (!matchId) {
      setError('请选择比赛')
      return
    }
    if (Number.isNaN(s1h) || Number.isNaN(s1a)) {
      setError('请填写完整的第一组比分')
      return
    }

    const predictions = [{ prediction_index: 1, home_score: s1h, away_score: s1a }]
    if (!Number.isNaN(s2h) && !Number.isNaN(s2a)) {
      predictions.push({ prediction_index: 2, home_score: s2h, away_score: s2a })
    }

    const payload = {
      provider_name: provider,
      half_full: halfFull1 || null,
      half_full2: halfFull2 || halfFull1 || null,
      predictions,
    }

    setLoading(true)
    try {
      await submitManualPrediction(matchId, payload)
      onSuccess()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || '提交失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b flex items-center justify-between">
          <div className="font-bold text-gray-800">手动 AI 预测</div>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">选择比赛</label>
            <select
              value={matchId}
              onChange={(e) => setMatchId(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">请选择比赛</option>
              {matches.map((m) => (
                <option key={m.match_id} value={m.match_id}>
                  {m.match_id} {m.league} {m.home_team} VS {m.away_team}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">AI 类型</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              {AI_PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-600">预测 1</div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">半全场</span>
                <select
                  value={halfFull1}
                  onChange={(e) => setHalfFull1(e.target.value)}
                  className="border rounded px-2 py-1 text-sm flex-1"
                >
                  {HALF_FULL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">比分</span>
                <NumberInput value={ft1Home} onChange={setFt1Home} placeholder="主" />
                <span>:</span>
                <NumberInput value={ft1Away} onChange={setFt1Away} placeholder="客" />
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-600">预测 2</div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">半全场</span>
                <select
                  value={halfFull2}
                  onChange={(e) => setHalfFull2(e.target.value)}
                  className="border rounded px-2 py-1 text-sm flex-1"
                >
                  {HALF_FULL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">比分</span>
                <NumberInput value={ft2Home} onChange={setFt2Home} placeholder="主" />
                <span>:</span>
                <NumberInput value={ft2Away} onChange={setFt2Away} placeholder="客" />
              </div>
            </div>
          </div>

          {error && <div className="text-sm text-danger">{error}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? '提交中...' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
