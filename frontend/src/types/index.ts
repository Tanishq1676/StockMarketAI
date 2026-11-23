export interface Meta {
  symbol: string;
  bse_symbol?: string;
  isin?: string | null;
  name: string;
  exchange?: string;
  sector?: string;
  market_cap?: string;
  nse_indices?: string[];
  data_source?: string;
  status?: string;
  type?: string;
}

export interface DataStatus {
  latest_trade_date?: string | null;
  fetched_at?: string | null;
  sources?: string[];
  is_live?: boolean;
  delay_minutes?: number;
}

export interface Quote {
  symbol: string;
  name?: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change_pct: number;
  last_updated: string;
  data_source: string;
  is_live?: boolean;
  delay_minutes?: number;
  prev_close?: number | null;
  trade_date?: string | null;
  fetched_at?: string | null;
  source_url?: string | null;
}

export interface HistoryRow {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  source?: string;
}

export interface IndexMeta {
  symbol: string;
  name: string;
  type: string;
  exchange: string;
  price?: number;
  change_pct?: number;
  prev_close?: number | null;
  trade_date?: string | null;
  data_source?: string;
  last_updated?: string;
}

export interface StockTableRow {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  market_cap: string;
  nse_indices: string[];
  isin?: string | null;
  bse_symbol?: string | null;
  price?: number;
  change_pct?: number;
  prev_close?: number | null;
  trade_date?: string | null;
  last_updated?: string | null;
  data_source?: string;
  is_live?: boolean;
  delay_minutes?: number;
}

export interface LiveRow {
  symbol: string;
  name?: string;
  price: number;
  change_pct: number;
  volume: number;
  prev_close?: number | null;
  trade_date?: string | null;
  last_updated?: string;
  data_source: string;
  is_live?: boolean;
  delay_minutes?: number;
}

export interface Prediction {
  horizon: string;
  predicted_close: number;
  prediction_interval?: [number, number];
  direction: string;
  bullish_probability: number;
  bearish_probability: number;
  confidence: number;
  expected_move_pct?: number;
  generated_at?: string;
}

export interface Indicator {
  rsi14_last?: number;
  historical_volatility_annualized?: number;
  max_drawdown_pct?: number;
  price_change_pct?: number;
  recent_trend?: number;
  volume_ratio?: number;
  volume_last?: number;
  volume_avg_60d?: number;
  ma5?: number;
  ma20?: number;
  ma50?: number;
  ma100?: number;
  ma200?: number;
  upper_last?: number;
  middle_last?: number;
  lower_last?: number;
  atr14_last?: number;
  support_levels?: number[];
  trend?: string;
  ma?: Record<string, number[]>;
  macd?: { macd_last?: number; signal_last?: number; hist_last?: number };
  bollinger?: { upper_last?: number; middle_last?: number; lower_last?: number };
}

export interface Analysis extends Indicator {
  symbol: string;
  ai_summary: string;
  ai_risk_factors: string[];
  ai_source: string;
  sentiment_score: number;
  news: NewsItem[];
}

export interface Signal {
  symbol: string;
  signal_type: string;
  confidence: number;
  entry_price?: number;
  target_price?: number;
  stop_loss?: number;
  risk_reward?: number;
  expected_holding_minutes?: number;
  risk_level?: string;
  reasons: string[];
  tech_reasons: string[];
  fund_reasons: string[];
  news_sentinel_score: number;
  ai_summary?: string;
  ai_source?: string;
  generated_at?: string;
}

export interface NewsItem {
  title: string;
  source: string;
  link: string;
  summary: string;
  published_at?: string;
  symbol: string;
  sector: string;
  sentiment_score: number;
  impact: string;
  analysis_source: string;
}

export interface PortfolioStock {
  symbol: string;
  qty: number;
  avg_buy_price: number;
  current_price: number;
  current_value: number;
  invested_cost: number;
  unrealised_pnl: number;
  unrealised_pct: number;
  weight_pct: number;
  sector: string;
}

export interface PortfolioSummary {
  total_investment: number;
  current_portfolio_value: number;
  unrealised_pnl: number;
  realised_pnl: number;
  total_pnl: number;
  total_return_pct: number;
  stocks: PortfolioStock[];
  sector_allocation: Record<string, number>;
}

export interface AlertItem {
  id: number;
  symbol: string;
  condition: string;
  threshold: number;
  status: string;
  fired_at?: string;
  message: string;
  created_at: string;
}

export interface PortfolioStmt {
  total_investment: number;
  current_value?: number;
  pnl?: number;
}

export interface MarketReport {
  id: number;
  report_type: string;
  generated_at: string;
  data_source: string;
  content: any;
}

export interface DashboardData {
  snapshot: {
    indices: LiveRow[];
    top_gainers: LiveRow[];
    top_losers: LiveRow[];
    most_active: LiveRow[];
    unusual_volume: LiveRow[];
    updated_at: string;
    data_status?: DataStatus;
  };
  ai_market_summary: string;
  ai_summary_source: string;
  latest_news: NewsItem[];
  top_signals: Signal[];
  alert_notifications: AlertItem[];
  portfolio_summary: PortfolioSummary;
}
