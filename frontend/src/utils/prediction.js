/**
 * 根据比分返回 1X2 结果
 * @returns {'主胜' | '平局' | '客胜'}
 */
export function getMatchResult(home, away) {
  if (home > away) return '主胜'
  if (home === away) return '平局'
  return '客胜'
}

/**
 * 根据让球盘口计算让球胜平负结果
 * @param {number} home
 * @param {number} away
 * @param {string} handicap 如 '+1', '-1', '0'
 * @returns {'让球主胜' | '让球平局' | '让球客胜' | null}
 */
export function getHandicapResult(home, away, handicap) {
  if (handicap === null || handicap === undefined || handicap === '') return null
  const val = parseFloat(handicap)
  if (Number.isNaN(val)) return null
  const adjustedHome = home + val
  if (adjustedHome > away) return '让球主胜'
  if (adjustedHome === away) return '让球平局'
  return '让球客胜'
}

/**
 * 根据比分返回总进球数字符串（与赔率 key 对齐）
 * @returns {string}
 */
export function getTotalGoals(home, away) {
  const total = home + away
  return `${total}球`
}

/**
 * 返回比分字符串，如 '2:1'
 */
export function getScoreStr(home, away) {
  return `${home}:${away}`
}

/**
 * 返回半全场字符串，如 '主胜/平局'
 */
export function getHalfFull(htHome, htAway, ftHome, ftAway) {
  const ht = getMatchResult(htHome, htAway)
  const ft = getMatchResult(ftHome, ftAway)
  return `${ht}/${ft}`
}

/**
 * 根据单个全场比分和半全场结果生成一组玩法预测
 */
function buildUserPrediction(home, away, halfFull, handicap) {
  return {
    胜平负: getMatchResult(home, away),
    让球胜平负: getHandicapResult(home, away, handicap),
    比分: getScoreStr(home, away),
    总进球数: getTotalGoals(home, away),
    半全场: halfFull || getHalfFull(home, away, home, away),
  }
}

/**
 * 获取用户在五种玩法上的预测结果（支持两个全场比分 + 两个半全场）
 * @returns {Array|null} 返回一个或两个预测场景数组
 */
export function getUserPredictions(halfFull1, halfFull2, ft1Home, ft1Away, ft2Home, ft2Away, handicap) {
  const s1h = parseInt(ft1Home, 10)
  const s1a = parseInt(ft1Away, 10)
  const s2h = parseInt(ft2Home, 10)
  const s2a = parseInt(ft2Away, 10)

  const scenarios = []
  if (!Number.isNaN(s1h) && !Number.isNaN(s1a)) {
    scenarios.push(buildUserPrediction(s1h, s1a, halfFull1, handicap))
  }
  if (!Number.isNaN(s2h) && !Number.isNaN(s2a)) {
    scenarios.push(buildUserPrediction(s2h, s2a, halfFull2, handicap))
  }

  return scenarios.length > 0 ? scenarios : null
}

/**
 * 查找某条推荐对应的赔率
 */
export function getOddsForBet(bet, match) {
  switch (bet.market) {
    case '胜平负': {
      const r = getMatchResultLabel(bet.selection)
      if (r === '主胜') return match.odds_home_win
      if (r === '平局') return match.odds_draw
      if (r === '客胜') return match.odds_away_win
      return null
    }
    case '让球胜平负': {
      const r = getHandicapLabel(bet.selection)
      if (r === '让球主胜') return match.odds_hhad_home_win
      if (r === '让球平局') return match.odds_hhad_draw
      if (r === '让球客胜') return match.odds_hhad_away_win
      return null
    }
    case '比分':
      return match.score_odds ? match.score_odds[bet.selection] : null
    case '总进球数': {
      const totalKey = String(bet.selection).replace(/球$/, '')
      return match.total_goals_odds ? match.total_goals_odds[totalKey] : null
    }
    case '半全场': {
      const hfKey = String(bet.selection)
        .replace(/主胜/g, '胜')
        .replace(/平局/g, '平')
        .replace(/客胜/g, '负')
      return match.half_full_odds ? match.half_full_odds[hfKey] : null
    }
    default:
      return null
  }
}

function getMatchResultLabel(selection) {
  if (selection.includes('主胜')) return '主胜'
  if (selection.includes('平局')) return '平局'
  if (selection.includes('客胜')) return '客胜'
  return selection
}

function getHandicapLabel(selection) {
  if (selection.includes('让球主胜')) return '让球主胜'
  if (selection.includes('让球平局')) return '让球平局'
  if (selection.includes('让球客胜')) return '让球客胜'
  return selection
}

/**
 * 判断 AI 推荐是否命中用户预测结果
 * userPredictions 可以是单个对象或对象数组（两个预测场景）
 */
export function betHitsUserPrediction(bet, userPredictions) {
  if (!userPredictions || !bet.market || !bet.selection) return false
  const scenarios = Array.isArray(userPredictions) ? userPredictions : [userPredictions]
  return scenarios.some((scenario) => {
    const userSel = scenario[bet.market]
    if (!userSel) return false
    // 允许让球 selection 里带额外描述，如 "让球主胜（-1）"
    if (bet.market === '让球胜平负') {
      const normalized = getHandicapLabel(bet.selection)
      return normalized === userSel
    }
    return String(bet.selection).trim() === String(userSel).trim()
  })
}

/**
 * 计算单条推荐的模拟投注积分（净盈亏，2 元本金）
 * @returns {number} 命中返回 odds * 2 - 2，未命中返回 -2
 */
export function evaluateBetPoints(bet, userPredictions, match) {
  const hits = betHitsUserPrediction(bet, userPredictions)
  if (!hits) return -2
  const odds = getOddsForBet(bet, match)
  if (!odds || odds <= 0) return -2
  return Number((odds * 2 - 2).toFixed(2))
}

/**
 * 根据用户预测计算一组 AI 预测的总积分
 */
export function evaluatePredictions(predictions, userPredictions, match) {
  if (!userPredictions || !predictions || predictions.length === 0) return null
  let total = 0
  const details = []
  predictions.forEach((pred) => {
    if (!pred.bets || pred.bets.length === 0) return
    pred.bets.forEach((bet) => {
      const points = evaluateBetPoints(bet, userPredictions, match)
      total += points
      details.push({
        predictionIndex: pred.prediction_index,
        market: bet.market,
        selection: bet.selection,
        hits: points > -2,
        points,
      })
    })
  })
  return { total: Number(total.toFixed(2)), details }
}

const STORAGE_KEY = 'personal_predictions_v1'

export function loadPersonalPrediction(matchId) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const all = JSON.parse(raw)
    return all[matchId] || null
  } catch {
    return null
  }
}

export function savePersonalPrediction(matchId, data) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const all = raw ? JSON.parse(raw) : {}
    all[matchId] = data
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // ignore
  }
}

/**
 * 把本地个人预测格式转换为后端接口需要的 payload
 */
export function buildPersonalPredictionPayload(halfFull1, halfFull2, ft1Home, ft1Away, ft2Home, ft2Away) {
  const predictions = []
  const s1h = parseInt(ft1Home, 10)
  const s1a = parseInt(ft1Away, 10)
  const s2h = parseInt(ft2Home, 10)
  const s2a = parseInt(ft2Away, 10)

  if (!Number.isNaN(s1h) && !Number.isNaN(s1a)) {
    predictions.push({ prediction_index: 1, home_score: s1h, away_score: s1a })
  }
  if (!Number.isNaN(s2h) && !Number.isNaN(s2a)) {
    predictions.push({ prediction_index: 2, home_score: s2h, away_score: s2a })
  }

  return predictions.length > 0
    ? {
        half_full: halfFull1 || null,
        half_full2: halfFull2 || halfFull1 || null,
        predictions,
      }
    : null
}

const MANUAL_STORAGE_KEY = 'manual_predictions_v1'

export const AI_PROVIDER_OPTIONS = [
  { value: 'gpt', label: 'GPT' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'kimi', label: 'Kimi' },
  { value: 'doubao', label: '豆包' },
  { value: 'qianwen', label: '千问' },
  { value: 'manual', label: '手动' },
]

export const HALF_FULL_OPTIONS = [
  { value: '', label: '请选择半全场' },
  { value: '胜/胜', label: '主胜/主胜' },
  { value: '胜/平', label: '主胜/平局' },
  { value: '胜/负', label: '主胜/客胜' },
  { value: '平/胜', label: '平局/主胜' },
  { value: '平/平', label: '平局/平局' },
  { value: '平/负', label: '平局/客胜' },
  { value: '负/胜', label: '客胜/主胜' },
  { value: '负/平', label: '客胜/平局' },
  { value: '负/负', label: '客胜/客胜' },
]

function buildPredictionItem(index, homeScore, awayScore, halfFull, handicap) {
  const h = parseInt(homeScore, 10)
  const a = parseInt(awayScore, 10)
  if (Number.isNaN(h) || Number.isNaN(a)) return null

  const bets = [
    { market: '胜平负', selection: getMatchResult(h, a), reason: '手动填写' },
    { market: '让球胜平负', selection: getHandicapResult(h, a, handicap), reason: '手动填写' },
    { market: '比分', selection: getScoreStr(h, a), reason: '手动填写' },
    { market: '总进球数', selection: getTotalGoals(h, a), reason: '手动填写' },
  ].filter((b) => b.selection !== null)

  if (halfFull && String(halfFull).trim()) {
    bets.push({ market: '半全场', selection: String(halfFull).trim(), reason: '手动填写' })
  }

  return {
    prediction_index: index,
    home_score: h,
    away_score: a,
    confidence: null,
    reasoning_summary: '手动预测',
    market_reasoning: null,
    bets,
    is_correct: null,
    points_awarded: null,
  }
}

/**
 * 根据用户输入构建一条手动预测记录（用于展示在卡片上）
 * halfFull2 可选，未提供时两个预测共用 halfFull
 */
export function buildManualPredictionRecord(providerValue, halfFull, score1Home, score1Away, score2Home, score2Away, handicap, halfFull2) {
  const option = AI_PROVIDER_OPTIONS.find((o) => o.value === providerValue)
  const providerName = option ? option.value : 'manual'
  const displayName = option ? `${option.label}（手动）` : '手动'

  const hf2 = halfFull2 !== undefined && halfFull2 !== null ? halfFull2 : halfFull

  const pred1 = buildPredictionItem(1, score1Home, score1Away, halfFull, handicap)
  const pred2 = buildPredictionItem(2, score2Home, score2Away, hf2, handicap)
  const predictions = [pred1, pred2].filter(Boolean)

  if (predictions.length === 0) return null

  return {
    provider_id: `manual-${providerName}`,
    provider_name: providerName,
    provider_display_name: displayName,
    predictions,
  }
}

export function loadManualPredictions(matchId) {
  try {
    const raw = localStorage.getItem(MANUAL_STORAGE_KEY)
    if (!raw) return []
    const all = JSON.parse(raw)
    return Array.isArray(all[matchId]) ? all[matchId] : []
  } catch {
    return []
  }
}

export function saveManualPrediction(matchId, record) {
  try {
    const raw = localStorage.getItem(MANUAL_STORAGE_KEY)
    const all = raw ? JSON.parse(raw) : {}
    const list = Array.isArray(all[matchId]) ? all[matchId] : []
    const existingIndex = list.findIndex((r) => r.provider_id === record.provider_id)
    if (existingIndex >= 0) {
      list[existingIndex] = record
    } else {
      list.push(record)
    }
    all[matchId] = list
    localStorage.setItem(MANUAL_STORAGE_KEY, JSON.stringify(all))
  } catch {
    // ignore
  }
}

export function deleteManualPrediction(matchId, providerId) {
  try {
    const raw = localStorage.getItem(MANUAL_STORAGE_KEY)
    if (!raw) return
    const all = JSON.parse(raw)
    if (!Array.isArray(all[matchId])) return
    all[matchId] = all[matchId].filter((r) => r.provider_id !== providerId)
    localStorage.setItem(MANUAL_STORAGE_KEY, JSON.stringify(all))
  } catch {
    // ignore
  }
}

/**
 * 将手动预测合并到后端返回的 predictions_by_provider 数组中
 * 如果后端已经存在同名 provider，则跳过该手动记录，避免重复显示
 */
export function mergeManualPredictions(matchId, backendPredictions) {
  const manual = loadManualPredictions(matchId)
  if (manual.length === 0) return backendPredictions || []
  const merged = [...(backendPredictions || [])]
  manual.forEach((record) => {
    // 若后端已有同名 provider（如 Gemini），不再显示 manual-gemini
    const backendHasSameProvider = merged.some(
      (p) => p.provider_name && record.provider_name && p.provider_name.toLowerCase() === record.provider_name.toLowerCase()
    )
    if (backendHasSameProvider) {
      return
    }
    const existingIndex = merged.findIndex((p) => p.provider_id === record.provider_id)
    if (existingIndex >= 0) {
      merged[existingIndex] = record
    } else {
      merged.push(record)
    }
  })
  return merged
}

/**
 * 批量导入手动预测
 * 文本格式：周六201韩职金泉尚武 VS 大田市民平胜、胜胜1-0、2-1
 */
export function batchImportManualPredictions(providerValue, text) {
  const lines = String(text).split(/\r?\n/).filter((line) => line.trim())
  const pattern = /^(周[一二六日]\d{3}).*?([胜平负]{2})、([胜平负]{2})(\d+-\d+)[、\s]+(\d+-\d+)\s*$/
  let imported = 0
  const failed = []

  lines.forEach((line) => {
    const match = line.trim().match(pattern)
    if (!match) {
      failed.push(line.trim())
      return
    }
    const [, matchId, hf1, hf2, score1Str, score2Str] = match
    const [s1Home, s1Away] = score1Str.split('-').map((s) => parseInt(s, 10))
    const [s2Home, s2Away] = score2Str.split('-').map((s) => parseInt(s, 10))

    const record = buildManualPredictionRecord(providerValue, hf1, s1Home, s1Away, s2Home, s2Away, null, hf2)
    if (!record) {
      failed.push(line.trim())
      return
    }
    saveManualPrediction(matchId, record)
    imported++
  })

  return { imported, failed }
}
