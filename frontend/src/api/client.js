import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

export default client

export const fetchDashboard = () => client.get('/dashboard/today')
export const fetchMatches = (params) => client.get('/matches', { params })
export const fetchProviders = () => client.get('/providers')
export const fetchLeaderboard = () => client.get('/providers/leaderboard')
export const submitResult = (matchId, homeScore, awayScore, halfFull = null) =>
  client.post(`/matches/${matchId}/result`, null, { params: { home_score: homeScore, away_score: awayScore, half_full: halfFull } })
export const submitPersonalPrediction = (matchId, data) =>
  client.post(`/matches/${matchId}/personal-prediction`, data)
export const submitManualPrediction = (matchId, data) =>
  client.post(`/matches/${matchId}/manual-prediction`, data)
export const runScrape = () => client.post('/admin/run-scrape')
export const runPredictions = () => client.post('/admin/run-predictions')
export const runScoring = () => client.post('/admin/run-scoring')
export const finishMatches = () => client.post('/admin/run-scoring')
