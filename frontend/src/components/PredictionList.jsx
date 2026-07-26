import { useState } from 'react'
import { evaluatePredictions, getOddsForBet } from '../utils/prediction'

const MARKET_ORDER = ['胜平负', '让球胜平负', '比分', '总进球数', '半全场']

function combineByMarket(predictions) {
  const map = {}
  predictions.forEach((pred) => {
    if (!pred.bets) return
    pred.bets.forEach((bet) => {
      if (!map[bet.market]) {
        map[bet.market] = []
      }
      map[bet.market].push({
        selection: bet.selection,
        reason: bet.reason,
        predictionIndex: pred.prediction_index,
      })
    })
  })
  return MARKET_ORDER.filter((m) => map[m]).map((market) => ({
    market,
    items: map[market].sort((a, b) => a.predictionIndex - b.predictionIndex),
  }))
}

export default function PredictionList({ providerName, predictions, match, userPredictions }) {
  const [expanded, setExpanded] = useState(false)

  if (!predictions || predictions.length === 0) {
    return <div className="text-xs text-gray-400 py-2">未预测</div>
  }

  const sorted = [...predictions].sort((a, b) => a.prediction_index - b.prediction_index)
  const scoreText = sorted.map((p) => `${p.home_score}:${p.away_score}`).join(' / ')
  const confidenceText = sorted
    .filter((p) => p.confidence !== null && p.confidence !== undefined)
    .map((p) => `${Math.round(p.confidence * 100)}%`)
    .join(' / ')
  const combinedBets = combineByMarket(sorted)

  const evaluation = match && userPredictions
    ? evaluatePredictions(sorted, userPredictions, match)
    : null

  const getScoreClass = (preds) => {
    const allCorrect = preds.length > 0 && preds.every((p) => p.is_correct === true)
    const anyWrong = preds.some((p) => p.is_correct === false)
    if (allCorrect) return 'bg-success/10 text-success border-success/30'
    if (anyWrong) return 'bg-danger/10 text-danger border-danger/30'
    return 'bg-gray-50 border-gray-200'
  }

  return (
    <div className={`border rounded p-1.5 ${getScoreClass(sorted)}`}>
      <div className="text-[10px] font-semibold text-gray-500 mb-0.5 truncate">{providerName}</div>

      <div className="flex items-center justify-between">
        <span className="font-bold text-xs">{scoreText}</span>
        {confidenceText && <span className="text-[10px]">{confidenceText}</span>}
      </div>

      {combinedBets.length > 0 && (
        <div className="mt-1 space-y-0.5">
          {combinedBets.map(({ market, items }) => (
            <div key={market} className="text-[10px] flex flex-wrap gap-0.5 leading-tight">
              <span className="text-gray-600">{market}:</span>
              {items.map((item, idx) => (
                <span key={idx} className="font-bold text-primary">
                  {item.selection}
                  {idx < items.length - 1 && <span className="text-gray-400 font-normal mx-0.5">/</span>}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}

      <div className="mt-1">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-[10px] text-primary hover:text-primary/80 flex items-center gap-0.5"
        >
          {expanded ? '▲ 收起' : '▼ 推理'}
        </button>
        {expanded && (
          <div className="mt-1 space-y-1 text-[10px]">
            {sorted.map((pred) => (
              <div key={pred.prediction_index} className="bg-white border rounded p-1">
                <div className="font-semibold text-gray-700 mb-0.5">
                  预测{pred.prediction_index}（{pred.home_score}:{pred.away_score}）
                </div>
                {pred.reasoning_summary && (
                  <div className="text-gray-600 mb-0.5">
                    <span className="font-medium">基本面：</span>
                    {pred.reasoning_summary}
                  </div>
                )}
                {pred.market_reasoning && (
                  <div className="text-gray-600">
                    <span className="font-medium">市场：</span>
                    {pred.market_reasoning}
                  </div>
                )}
                {pred.bets && pred.bets.length > 0 && (
                  <div className="mt-1 space-y-0.5">
                    {pred.bets.map((bet, idx) => {
                      const hit = userPredictions
                        ? evaluation?.details.find(
                            (d) =>
                              d.predictionIndex === pred.prediction_index &&
                              d.market === bet.market &&
                              d.selection === bet.selection
                          )?.hits
                        : null
                      const odds = match ? getOddsForBet(bet, match) : null
                      return (
                        <div
                          key={idx}
                          className={`text-[10px] p-0.5 rounded ${hit === true ? 'bg-success/10' : hit === false ? 'bg-danger/10' : ''}`}
                        >
                          <span className="font-medium">{bet.market}:</span>
                          <span className="text-primary font-semibold">{bet.selection}</span>
                          {odds !== null && odds !== undefined && (
                            <span className="text-gray-500 ml-0.5">@{odds}</span>
                          )}
                          {hit === true && <span className="text-success ml-0.5">✓</span>}
                          {hit === false && <span className="text-danger ml-0.5">✗</span>}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {sorted.some((p) => p.points_awarded !== null && p.points_awarded !== undefined) && (
        <div className="mt-1 text-[10px]">
          {sorted.map((pred) =>
            pred.points_awarded !== null && pred.points_awarded !== undefined ? (
              <span key={pred.prediction_index} className="mr-0.5">
                {pred.points_awarded > 0 ? (
                  <span className="score-badge bg-success/20 text-success">+{pred.points_awarded}</span>
                ) : pred.points_awarded < 0 ? (
                  <span className="score-badge bg-danger/20 text-danger">{pred.points_awarded}</span>
                ) : (
                  <span className="score-badge bg-gray-100 text-gray-600">{pred.points_awarded}</span>
                )}
              </span>
            ) : null
          )}
        </div>
      )}
    </div>
  )
}
