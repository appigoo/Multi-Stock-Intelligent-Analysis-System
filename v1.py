import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from groq import Groq
import json
import os
from datetime import datetime, timedelta
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────
# 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="多股票智能分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS 樣式
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 28px; font-weight: 600;
        background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .subtitle { font-size: 13px; color: #888; margin-bottom: 20px; }
    .metric-card {
        background: #f8f9fa; border-radius: 10px;
        padding: 14px 16px; border-left: 4px solid #ccc;
        margin-bottom: 10px;
    }
    .metric-card.bear { border-left-color: #e74c3c; }
    .metric-card.bull { border-left-color: #27ae60; }
    .metric-card.neut { border-left-color: #f39c12; }
    .metric-label { font-size: 11px; color: #888; margin-bottom: 2px; }
    .metric-value { font-size: 15px; font-weight: 600; color: #2c3e50; }
    .tag {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 11px; font-weight: 600; margin-top: 4px;
    }
    .tag-bear { background: #fde8e8; color: #c0392b; }
    .tag-bull { background: #e8f8e8; color: #1e8449; }
    .tag-neut { background: #fef9e7; color: #d68910; }
    .news-card {
        background: #fff; border: 1px solid #e8e8e8;
        border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;
    }
    .news-title { font-size: 13px; font-weight: 600; color: #2c3e50; }
    .news-meta { font-size: 11px; color: #999; margin-top: 3px; }
    .trade-box {
        border-radius: 10px; padding: 16px;
        border: 1px solid #e0e0e0; margin-bottom: 12px;
    }
    .trade-short { border-left: 4px solid #e74c3c; background: #fff9f9; }
    .trade-long  { border-left: 4px solid #27ae60; background: #f9fff9; }
    .trade-warn  { border-left: 4px solid #f39c12; background: #fffdf0; }
    .trade-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
    .price-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .price-item { background: #f8f9fa; border-radius: 6px; padding: 8px 10px; }
    .price-label { font-size: 10px; color: #999; }
    .price-val { font-size: 15px; font-weight: 700; }
    .price-val.bear { color: #e74c3c; }
    .price-val.bull { color: #27ae60; }
    .section-header {
        font-size: 14px; font-weight: 700; color: #2c3e50;
        border-bottom: 2px solid #3498db; padding-bottom: 6px;
        margin: 20px 0 12px;
    }
    .stSpinner > div { border-top-color: #3498db !important; }
    .prediction-history {
        background: #f8f9fa; border-radius: 8px;
        padding: 12px; margin-bottom: 8px;
        border-left: 3px solid #3498db;
    }
    /* ── 多股票 Dashboard 卡片 ── */
    .stock-card {
        background: #fff; border: 1px solid #e8e8e8;
        border-radius: 12px; padding: 16px;
        margin-bottom: 12px; position: relative;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .stock-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
    .stock-card.bull-card { border-top: 3px solid #27ae60; }
    .stock-card.bear-card { border-top: 3px solid #e74c3c; }
    .stock-card.neut-card { border-top: 3px solid #f39c12; }
    .stock-ticker { font-size: 18px; font-weight: 700; color: #1a1a2e; }
    .stock-name   { font-size: 11px; color: #999; margin-bottom: 8px; }
    .stock-price  { font-size: 22px; font-weight: 700; }
    .stock-chg-up   { color: #27ae60; }
    .stock-chg-down { color: #e74c3c; }
    .mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 10px; }
    .mini-item { background: #f8f9fa; border-radius: 6px; padding: 6px 8px; }
    .mini-label { font-size: 10px; color: #aaa; }
    .mini-val   { font-size: 12px; font-weight: 600; color: #2c3e50; }
    .scan-table-row-bull { background: #f0fff4 !important; }
    .scan-table-row-bear { background: #fff5f5 !important; }
    .tab-content { padding: 12px 0; }
    /* 多股票進度條 */
    .multi-progress {
        background: #e8e8e8; border-radius: 4px;
        height: 6px; margin: 8px 0;
    }
    .multi-progress-bar {
        background: linear-gradient(90deg, #3498db, #1abc9c);
        height: 6px; border-radius: 4px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 常數
# ─────────────────────────────────────────────
PERIOD_MAP = {
    "1w":  {"period": "6mo",  "interval": "1wk",  "label": "週線"},
    "1d":  {"period": "1y",   "interval": "1d",   "label": "日線"},
    "1h":  {"period": "60d",  "interval": "1h",   "label": "小時線"},
    "15m": {"period": "30d",  "interval": "15m",  "label": "15分鐘"},
    "5m":  {"period": "5d",   "interval": "5m",   "label": "5分鐘"},
}

PRESET_WATCHLISTS = {
    "科技龍頭": ["TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOGL"],
    "AI 概念":  ["NVDA", "AMD", "SMCI", "PLTR", "AI", "SOUN", "BBAI"],
    "電動車":   ["TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "F"],
    "半導體":   ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MU", "AMAT"],
    "自選":     [],
}

# ─────────────────────────────────────────────
# 工具函數
# ─────────────────────────────────────────────
def safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except:
        return default

def flatten_columns(df):
    """安全處理 yfinance MultiIndex columns（新舊版本相容）"""
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # 確保標準列名存在
    rename_map = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if 'open' in col_lower and col != 'Open':
            rename_map[col] = 'Open'
        elif 'high' in col_lower and col != 'High':
            rename_map[col] = 'High'
        elif 'low' in col_lower and col != 'Low':
            rename_map[col] = 'Low'
        elif 'close' in col_lower and 'adj' not in col_lower and col != 'Close':
            rename_map[col] = 'Close'
        elif 'volume' in col_lower and col != 'Volume':
            rename_map[col] = 'Volume'
    if rename_map:
        df = df.rename(columns=rename_map)
    return df

# ─── 技術指標（純 Python，修正版）───
def calc_sma(series, n):
    return series.rolling(window=n, min_periods=1).mean()

def calc_ema(series, n):
    return series.ewm(span=n, adjust=False, min_periods=1).mean()

def calc_rsi_wilder(series, n=14):
    """Wilder RSI — 更準確的實作"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing = EMA with alpha = 1/n
    avg_gain = gain.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bbands(series, n=20, k=2):
    mid = calc_sma(series, n)
    std = series.rolling(n, min_periods=1).std()
    return mid + k * std, mid, mid - k * std

def calc_atr(high, low, close, n=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=1).mean()

def find_support_resistance(df, n=20):
    """修正：避免 center=True 在尾端產生 NaN"""
    highs = df['High'].rolling(n, min_periods=1).max()   # 改用非 center
    lows  = df['Low'].rolling(n, min_periods=1).min()
    resistances = sorted(highs.dropna().unique(), reverse=True)[:3]
    supports    = sorted(lows.dropna().unique())[:3]
    return supports, resistances

def pivot_levels(df):
    """修正：確保至少有 2 筆資料"""
    if len(df) < 2:
        last = df.iloc[-1]
        P = safe_float(last['Close'])
        return {'P': P, 'R1': P*1.01, 'R2': P*1.02, 'S1': P*0.99, 'S2': P*0.98}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    P  = (safe_float(prev['High']) + safe_float(prev['Low']) + safe_float(prev['Close'])) / 3
    rng = safe_float(prev['High']) - safe_float(prev['Low'])
    rng = rng if rng > 0 else safe_float(prev['Close']) * 0.01
    R1 = 2 * P - safe_float(prev['Low'])
    R2 = P + rng
    S1 = 2 * P - safe_float(prev['High'])
    S2 = P - rng
    return {'P': P, 'R1': R1, 'R2': R2, 'S1': S1, 'S2': S2}


# ─── 數據載入（修正 + 加強穩定性）───
@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(ticker: str, period_key: str):
    cfg = PERIOD_MAP[period_key]
    try:
        df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                         auto_adjust=True, progress=False, timeout=15)
    except Exception as e:
        return None, {}, str(e)

    df = flatten_columns(df)
    if df is None or df.empty:
        return None, {}, "無法取得數據"
    df = df.dropna(subset=['Close', 'Open', 'High', 'Low'])
    if len(df) < 5:
        return None, {}, "數據不足"

    macro = {}

    # 宏觀指標
    for sym, key in [("^VIX","vix"), ("^GSPC","spx"), ("^TNX","tnx"), ("CL=F","oil")]:
        try:
            tmp = yf.download(sym, period="5d", interval="1d",
                              auto_adjust=True, progress=False, timeout=10)
            tmp = flatten_columns(tmp)
            if tmp is not None and not tmp.empty and len(tmp) >= 2:
                macro[key] = {
                    "close": safe_float(tmp['Close'].iloc[-1]),
                    "prev":  safe_float(tmp['Close'].iloc[-2]),
                    "chg":   safe_float((tmp['Close'].iloc[-1] - tmp['Close'].iloc[-2])
                                       / tmp['Close'].iloc[-2] * 100)
                }
        except:
            pass

    # Beta 計算（修正：使用矩陣 cov，更穩健）
    try:
        spx_d = yf.download("^GSPC", period="3mo", interval="1d",
                             auto_adjust=True, progress=False, timeout=10)
        stk_d = yf.download(ticker,  period="3mo", interval="1d",
                             auto_adjust=True, progress=False, timeout=10)
        spx_d = flatten_columns(spx_d)
        stk_d = flatten_columns(stk_d)
        if spx_d is not None and stk_d is not None:
            spx_ret = spx_d['Close'].pct_change().dropna()
            stk_ret = stk_d['Close'].pct_change().dropna()
            aligned = pd.concat([stk_ret, spx_ret], axis=1, join='inner').dropna()
            aligned.columns = ['stock', 'spx']
            if len(aligned) >= 20:
                cov_matrix = np.cov(aligned['stock'], aligned['spx'])
                macro["beta"] = safe_float(cov_matrix[0,1] / cov_matrix[1,1], 1.0)
            else:
                macro["beta"] = 1.0
    except:
        macro["beta"] = 1.0

    # 股票基本信息
    try:
        info = yf.Ticker(ticker).fast_info
        macro["company_name"] = getattr(info, 'symbol', ticker)
        try:
            full_info = yf.Ticker(ticker).info
            macro["company_name"] = full_info.get("longName", ticker)
            macro["sector"] = full_info.get("sector", "N/A")
            macro["market_cap"] = full_info.get("marketCap", 0)
            macro["week52_high"] = safe_float(full_info.get("fiftyTwoWeekHigh", 0))
            macro["week52_low"]  = safe_float(full_info.get("fiftyTwoWeekLow", 0))
        except:
            macro["company_name"] = ticker
            macro["sector"] = "N/A"
            macro["market_cap"] = 0
            macro["week52_high"] = safe_float(df['High'].max())
            macro["week52_low"]  = safe_float(df['Low'].min())
    except:
        macro["company_name"] = ticker
        macro["sector"] = "N/A"
        macro["market_cap"] = 0
        macro["week52_high"] = safe_float(df['High'].max())
        macro["week52_low"]  = safe_float(df['Low'].min())

    return df, macro, None


# ─── 快速掃描數據（不下載宏觀，速度快）───
@st.cache_data(ttl=180, show_spinner=False)
def load_quick_data(ticker: str):
    """快速載入單股票數據，用於多股票 Dashboard"""
    try:
        df = yf.download(ticker, period="3mo", interval="1d",
                         auto_adjust=True, progress=False, timeout=12)
        df = flatten_columns(df)
        if df is None or df.empty or len(df) < 10:
            return None
        df = df.dropna(subset=['Close'])

        close = df['Close']
        high  = df['High']
        low   = df['Low']

        curr  = safe_float(close.iloc[-1])
        prev  = safe_float(close.iloc[-2])
        pct   = (curr - prev) / prev * 100 if prev else 0
        sma20 = safe_float(calc_sma(close, 20).iloc[-1])
        sma50 = safe_float(calc_sma(close, 50).iloc[-1])
        rsi   = safe_float(calc_rsi_wilder(close, 14).iloc[-1])
        macd_line, macd_sig, _ = calc_macd(close)
        macd_cross = "金叉" if safe_float(macd_line.iloc[-1]) > safe_float(macd_sig.iloc[-1]) else "死叉"
        atr   = safe_float(calc_atr(high, low, close, 14).iloc[-1])
        vol   = safe_float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
        vol5  = safe_float(df['Volume'].tail(5).mean()) if 'Volume' in df.columns else 1
        vol_ratio = vol / vol5 if vol5 > 0 else 1.0

        # 簡易信號評分
        score = 0
        if curr > sma20: score += 1
        if curr > sma50: score += 1
        if rsi < 70 and rsi > 40: score += 1
        if macd_cross == "金叉": score += 1
        if vol_ratio > 1.2: score += 1

        bias = "bullish" if score >= 4 else "bearish" if score <= 1 else "neutral"

        try:
            info = yf.Ticker(ticker).info
            name = info.get("shortName", ticker)
            week52h = safe_float(info.get("fiftyTwoWeekHigh", 0))
            week52l = safe_float(info.get("fiftyTwoWeekLow", 0))
        except:
            name = ticker
            week52h = safe_float(df['High'].max())
            week52l = safe_float(df['Low'].min())

        return {
            "ticker": ticker, "name": name,
            "curr": curr, "prev": prev, "pct": pct,
            "sma20": sma20, "sma50": sma50,
            "rsi": rsi, "macd_cross": macd_cross,
            "atr": atr, "vol_ratio": vol_ratio,
            "week52h": week52h, "week52l": week52l,
            "score": score, "bias": bias,
            "df": df,  # 保留 df 供 mini 圖用
        }
    except Exception as e:
        return None


# ─── 新聞抓取（加強 fallback）───
@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(ticker: str, company_name: str):
    news_items = []
    queries = [
        f"{ticker} stock",
        f"{company_name} earnings",
        f"{ticker} analyst rating",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for q in queries:
        try:
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code != 200:
                continue
            items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
            for item in items[:4]:
                title   = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', item)
                pubdate = re.search(r'<pubDate>(.*?)</pubDate>', item)
                if title:
                    t = (title.group(1) or title.group(2) or "").strip()
                    t = re.sub(r'<[^>]+>', '', t)
                    if t:
                        news_items.append({
                            "title": t,
                            "date": pubdate.group(1)[:16] if pubdate else "N/A",
                        })
        except:
            continue

    seen = set()
    unique = []
    for n in news_items:
        key = n["title"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique[:12]


# ─── 技術指標計算（修正版）───
def compute_indicators(df):
    ind = {}
    close = df['Close']
    high  = df['High']
    low   = df['Low']

    ind['sma20']  = calc_sma(close, 20)
    ind['sma50']  = calc_sma(close, 50)
    ind['sma200'] = calc_sma(close, 200)
    ind['ema9']   = calc_ema(close, 9)
    ind['ema21']  = calc_ema(close, 21)
    ind['rsi']    = calc_rsi_wilder(close, 14)  # 修正：使用 Wilder RSI

    macd, signal, hist = calc_macd(close)
    ind['macd'] = macd; ind['macd_signal'] = signal; ind['macd_hist'] = hist

    bb_u, bb_m, bb_l = calc_bbands(close)
    ind['bb_upper'] = bb_u; ind['bb_mid'] = bb_m; ind['bb_lower'] = bb_l

    ind['atr'] = calc_atr(high, low, close, 14)   # 修正：使用 Wilder ATR

    supports, resistances = find_support_resistance(df)   # 修正：移除 center=True
    ind['supports'] = supports
    ind['resistances'] = resistances
    ind['pivots'] = pivot_levels(df)

    return ind


# ─── Groq 分析（修正版）───
def run_groq_analysis(ticker, period_key, df, macro, ind, news):
    try:
        api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
        if not api_key:
            return None, "❌ 找不到 GROQ_API_KEY，請在 Secrets 設定。"
        client = Groq(api_key=api_key)
    except Exception as e:
        return None, f"❌ Groq 初始化失敗：{e}"

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    curr_price = safe_float(last['Close'])
    prev_close = safe_float(prev['Close'])
    pct_chg    = (curr_price - prev_close) / prev_close * 100 if prev_close else 0

    rsi_val    = safe_float(ind['rsi'].iloc[-1])
    macd_val   = safe_float(ind['macd'].iloc[-1])
    macd_sig   = safe_float(ind['macd_signal'].iloc[-1])
    atr_val    = safe_float(ind['atr'].iloc[-1])
    if atr_val <= 0:
        atr_val = curr_price * 0.02  # fallback

    sma20_val  = safe_float(ind['sma20'].iloc[-1])
    sma50_val  = safe_float(ind['sma50'].iloc[-1])
    sma200_val = safe_float(ind['sma200'].iloc[-1])
    bb_upper   = safe_float(ind['bb_upper'].iloc[-1])
    bb_lower   = safe_float(ind['bb_lower'].iloc[-1])
    beta       = safe_float(macro.get("beta", 1.0))
    vix        = safe_float(macro.get("vix", {}).get("close", 20))
    vix_chg    = safe_float(macro.get("vix", {}).get("chg", 0))
    spx_chg    = safe_float(macro.get("spx", {}).get("chg", 0))
    tnx        = safe_float(macro.get("tnx", {}).get("close", 4.3))
    oil        = safe_float(macro.get("oil", {}).get("close", 80))
    pivots     = ind['pivots']
    supports   = ind['supports']
    resistances= ind['resistances']

    news_text  = "\n".join([f"- {n['title']} ({n['date']})" for n in news[:8]])
    period_label = PERIOD_MAP[period_key]["label"]

    system_prompt = """你是一位頂級量化交易分析師，擅長結合宏觀經濟、技術分析、市場情緒進行短期股價預測。
你的分析必須：
1. 數據驅動，每個判斷都有數字支撐
2. 明確給出概率分布（5個區間，百分比總和=100）
3. 給出可直接執行的入場—止損—止盈規則集
4. 倉位建議根據 VIX×Beta 動態調整
5. 嚴格按照指定 JSON 格式輸出，不得有任何額外文字

【價格邏輯鐵律 — 違反即為錯誤，必須嚴格遵守】
做空 SHORT 方向：
  - 入場區間：entry_low 到 entry_high（entry_high > entry_low）
  - 止損 stop_loss 必須 > entry_high
  - 止盈 tp1 必須 < entry_low
  - 止盈 tp2 必須 < tp1
  - 計算公式：stop_loss = entry_high + 1.0×ATR；tp1 = entry_low - 1.5×ATR；tp2 = entry_low - 2.5×ATR
  - 風險回報 = (entry_high - tp1) / (stop_loss - entry_high)，必須 ≥ 1.5

做多 LONG 方向：
  - 入場區間：entry_low 到 entry_high
  - 止損 stop_loss 必須 < entry_low
  - 止盈 tp1 必須 > entry_high
  - 止盈 tp2 必須 > tp1
  - 計算公式：stop_loss = entry_low - 1.0×ATR；tp1 = entry_high + 1.5×ATR；tp2 = entry_high + 2.5×ATR
  - 風險回報 = (tp1 - entry_low) / (entry_high - stop_loss)，必須 ≥ 1.5

輸出必須是純 JSON，無任何 markdown 或說明文字。"""

    user_prompt = f"""
分析股票：{ticker}（{macro.get('company_name','')}, {macro.get('sector','')})
時間週期：{period_label}
當前價格：${curr_price:.2f}（較前期 {pct_chg:+.2f}%）
52週高/低：${macro.get('week52_high',0):.2f} / ${macro.get('week52_low',0):.2f}

【技術指標】
- SMA20: ${sma20_val:.2f} | SMA50: ${sma50_val:.2f} | SMA200: ${sma200_val:.2f}
- 當前價 vs SMA20: {((curr_price-sma20_val)/sma20_val*100) if sma20_val else 0:+.1f}% | vs SMA200: {((curr_price-sma200_val)/sma200_val*100) if sma200_val else 0:+.1f}%
- RSI(14/Wilder): {rsi_val:.1f} {'（超買>70）' if rsi_val>70 else '（超賣<30）' if rsi_val<30 else '（中性）'}
- MACD: {macd_val:.3f} | Signal: {macd_sig:.3f} | 金叉={'是' if macd_val>macd_sig else '否'}
- 布林帶上軌: ${bb_upper:.2f} | 下軌: ${bb_lower:.2f}
- ATR(14/Wilder): ${atr_val:.2f}
- Beta: {beta:.2f}

【樞軸點支撐/阻力】
- R2: ${pivots['R2']:.2f} | R1: ${pivots['R1']:.2f} | P: ${pivots['P']:.2f}
- S1: ${pivots['S1']:.2f} | S2: ${pivots['S2']:.2f}
- 近期支撐: {', '.join([f'${s:.2f}' for s in supports[:2]])}
- 近期阻力: {', '.join([f'${r:.2f}' for r in resistances[:2]])}

【宏觀環境】
- VIX: {vix:.2f}（{vix_chg:+.1f}%）{'⚠️恐慌帶' if vix>25 else '正常'}
- SPX 最新漲跌: {spx_chg:+.2f}%
- 10年美債收益率: {tnx:.2f}%
- 油價(WTI): ${oil:.2f}

【VIX×Beta 尾部風險係數】= {vix * beta:.1f}
（>35=高尾部風險；>50=縮減倉位至0.5x）

【ATR 止損止盈計算基準 — 必須嚴格按此計算】
ATR(14/Wilder) = {atr_val:.2f}
做空示例（若入場區間在當前價附近）：
  stop_loss ≈ {curr_price + atr_val:.2f}（entry_high + ATR）
  tp1 ≈ {curr_price - atr_val*1.5:.2f}（entry_low - 1.5×ATR）
  tp2 ≈ {curr_price - atr_val*2.5:.2f}（entry_low - 2.5×ATR）
做多示例：
  stop_loss ≈ {curr_price - atr_val:.2f}（entry_low - ATR）
  tp1 ≈ {curr_price + atr_val*1.5:.2f}（entry_high + 1.5×ATR）
  tp2 ≈ {curr_price + atr_val*2.5:.2f}（entry_high + 2.5×ATR）

【最新新聞（48小時）】
{news_text if news_text else "暫無新聞數據"}

輸出純 JSON，格式：

{{
  "summary": "3句話核心判斷（中文）",
  "bias": "bullish/bearish/neutral",
  "bias_strength": 1-10,
  "macro_scores": [
    {{"name": "指標名稱", "value": "數值字符串", "signal": "bear/bull/neut", "comment": "簡評"}}
  ],
  "factor_scores": [
    {{"name": "因子名稱", "score": 0-100, "direction": "空/多/中性", "color": "bear/bull/neut"}}
  ],
  "probability": [
    {{"range": "場景描述", "prob": 整數, "color": "bear/bull/neut"}},
    {{"range": "場景描述", "prob": 整數, "color": "bear/bull/neut"}},
    {{"range": "場景描述", "prob": 整數, "color": "bear/bull/neut"}},
    {{"range": "場景描述", "prob": 整數, "color": "bear/bull/neut"}},
    {{"range": "場景描述", "prob": 整數, "color": "bear/bull/neut"}}
  ],
  "trade_short": {{
    "enabled": true/false,
    "probability": 整數,
    "entry_type": "入場方式說明",
    "entry_zone": "价格區間",
    "stop_loss": 數字,
    "tp1": 數字,
    "tp2": 數字,
    "rr_ratio": "1:X.X",
    "position_size": "X.X× 標準倉",
    "trigger": "觸發條件",
    "rationale": "理由"
  }},
  "trade_long": {{
    "enabled": true/false,
    "probability": 整數,
    "entry_type": "入場方式說明",
    "entry_zone": "价格區間",
    "stop_loss": 數字,
    "tp1": 數字,
    "tp2": 數字,
    "rr_ratio": "1:X.X",
    "position_size": "X.X× 標準倉",
    "trigger": "觸發條件",
    "rationale": "理由"
  }},
  "invalidation": ["條件1","條件2","條件3","條件4"],
  "key_levels": {{
    "strong_resistance": 數字,
    "resistance": 數字,
    "current": {curr_price:.2f},
    "support": 數字,
    "strong_support": 數字
  }},
  "news_sentiment": "bear/bull/neut",
  "news_summary": "新聞情緒2句話摘要"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()
        # 清理 markdown fences
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
        data = json.loads(raw)

        # ── 後端價格邏輯校驗（修正：更健壯的 parse_entry）──
        def parse_entry(zone_str, fallback):
            """解析入場區間字符串，支援多種格式"""
            s = str(zone_str)
            # 嘗試找 $xxx - $xxx 或 xxx-xxx 格式
            nums = re.findall(r'\$?([\d,]+\.?\d*)', s)
            vals = []
            for n in nums:
                try:
                    v = float(n.replace(',', ''))
                    if v > 1:  # 過濾掉比率數字
                        vals.append(v)
                except:
                    pass
            if len(vals) >= 2:
                return min(vals), max(vals)
            elif len(vals) == 1:
                v = vals[0]
                spread = max(atr_val * 0.3, v * 0.003)
                return round(v - spread, 2), round(v + spread, 2)
            # fallback：用當前價 ± 0.3% 作為入場區間
            spread = max(atr_val * 0.3, fallback * 0.003)
            return round(fallback - spread, 2), round(fallback + spread, 2)

        atr = atr_val if atr_val > 0 else curr_price * 0.02

        for direction in ['trade_short', 'trade_long']:
            trade = data.get(direction, {})
            if not trade or not trade.get('enabled', False):
                continue
            entry_low, entry_high = parse_entry(trade.get('entry_zone', ''), curr_price)
            sl  = safe_float(trade.get('stop_loss', 0))
            tp1 = safe_float(trade.get('tp1', 0))
            tp2 = safe_float(trade.get('tp2', 0))

            if direction == 'trade_short':
                if sl <= entry_high or sl <= 0:
                    sl = round(entry_high + atr, 2)
                if tp1 >= entry_low or tp1 <= 0:
                    tp1 = round(entry_low - atr * 1.5, 2)
                if tp2 >= tp1 or tp2 <= 0:
                    tp2 = round(tp1 - atr, 2)
                risk   = max(sl - entry_high, 0.01)
                reward = max(entry_low - tp1, 0.01)
            else:
                if sl >= entry_low or sl <= 0:
                    sl = round(entry_low - atr, 2)
                if tp1 <= entry_high or tp1 <= 0:
                    tp1 = round(entry_high + atr * 1.5, 2)
                if tp2 <= tp1 or tp2 <= 0:
                    tp2 = round(tp1 + atr, 2)
                risk   = max(entry_low - sl, 0.01)
                reward = max(tp1 - entry_high, 0.01)

            rr = reward / risk
            trade['stop_loss'] = round(sl, 2)
            trade['tp1']       = round(tp1, 2)
            trade['tp2']       = round(tp2, 2)
            trade['rr_ratio']  = f"1:{rr:.1f}"
            data[direction]    = trade

        return data, None

    except json.JSONDecodeError as e:
        snippet = raw[:400] if 'raw' in dir() else "N/A"
        return None, f"❌ JSON 解析失敗：{e}\n原始輸出：{snippet}"
    except Exception as e:
        return None, f"❌ Groq API 錯誤：{e}"


# ─── Plotly K線圖 ───
def build_chart(df, ind, analysis, ticker, period_key):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=("", "RSI(14/Wilder)", "MACD")
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'],   close=df['Close'],
        name="K線",
        increasing_line_color='#27ae60',
        decreasing_line_color='#e74c3c',
    ), row=1, col=1)

    for col_name, color, width, label in [
        ('sma20',  '#3498db', 1.2, 'SMA20'),
        ('sma50',  '#f39c12', 1.2, 'SMA50'),
        ('sma200', '#9b59b6', 1.5, 'SMA200'),
        ('ema9',   '#1abc9c', 1.0, 'EMA9'),
    ]:
        fig.add_trace(go.Scatter(
            x=df.index, y=ind[col_name],
            name=label, line=dict(color=color, width=width), opacity=0.85
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=ind['bb_upper'],
        name='BB Upper', line=dict(color='rgba(149,165,166,0.6)', width=0.8, dash='dot'),
        showlegend=False
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=ind['bb_lower'],
        name='BB Lower', line=dict(color='rgba(149,165,166,0.6)', width=0.8, dash='dot'),
        fill='tonexty', fillcolor='rgba(149,165,166,0.07)', showlegend=False
    ), row=1, col=1)

    if analysis and 'key_levels' in analysis:
        kl = analysis['key_levels']
        for price, color, label in [
            (kl.get('strong_resistance'), 'rgba(231,76,60,0.8)', 'R2'),
            (kl.get('resistance'),        'rgba(231,76,60,0.5)', 'R1'),
            (kl.get('support'),           'rgba(39,174,96,0.5)', 'S1'),
            (kl.get('strong_support'),    'rgba(39,174,96,0.8)', 'S2'),
        ]:
            if price and price > 0:
                fig.add_hline(
                    y=price, line=dict(color=color, width=1.2, dash='dash'),
                    annotation_text=f" {label} ${price:.2f}",
                    annotation_position="right", annotation_font_size=10,
                    row=1, col=1
                )

    rsi_data = ind['rsi']
    fig.add_trace(go.Scatter(
        x=df.index, y=rsi_data,
        name='RSI', line=dict(color='#8e44ad', width=1.5)
    ), row=2, col=1)
    fig.add_hline(y=70, line=dict(color='#e74c3c', width=0.8, dash='dot'), row=2, col=1)
    fig.add_hline(y=30, line=dict(color='#27ae60', width=0.8, dash='dot'), row=2, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor='rgba(142,68,173,0.04)', line_width=0, row=2, col=1)

    macd_hist = ind['macd_hist']
    colors_bar = ['#27ae60' if v >= 0 else '#e74c3c' for v in macd_hist]
    fig.add_trace(go.Bar(
        x=df.index, y=macd_hist,
        name='MACD Hist', marker_color=colors_bar, opacity=0.7
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=ind['macd'],
        name='MACD', line=dict(color='#3498db', width=1.2)
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=ind['macd_signal'],
        name='Signal', line=dict(color='#e67e22', width=1.2)
    ), row=3, col=1)

    period_label = PERIOD_MAP[period_key]["label"]
    fig.update_layout(
        title=dict(text=f"{ticker} · {period_label} · 技術分析圖", font=dict(size=15, color='#2c3e50')),
        height=650,
        xaxis_rangeslider_visible=False,
        paper_bgcolor='white', plot_bgcolor='#fafafa',
        legend=dict(orientation='h', y=1.02, x=0, font=dict(size=10), bgcolor='rgba(255,255,255,0.8)'),
        margin=dict(l=10, r=80, t=60, b=10),
        hovermode='x unified',
    )
    fig.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)', tickfont=dict(size=10))
    fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
    return fig


def build_mini_chart(df, ticker, bias):
    """迷你折線圖，用於多股票 Dashboard 卡片"""
    color = '#27ae60' if bias == 'bullish' else '#e74c3c' if bias == 'bearish' else '#f39c12'
    close = df['Close'].tail(60)
    fig = go.Figure(go.Scatter(
        x=list(range(len(close))), y=close.values,
        mode='lines', line=dict(color=color, width=2),
        fill='tozeroy', fillcolor='rgba(39,174,96,0.08)' if bias=='bullish' else 'rgba(231,76,60,0.08)' if bias=='bearish' else 'rgba(243,156,18,0.08)',
    ))
    fig.update_layout(
        height=80, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


# ─── 顯示函數 ───
def display_macro(macro_scores):
    cols = st.columns(3)
    for i, item in enumerate(macro_scores):
        tag_cls  = {"bear": "tag-bear",  "bull": "tag-bull",  "neut": "tag-neut"}.get(item.get("signal","neut"), "tag-neut")
        card_cls = {"bear": "bear", "bull": "bull", "neut": "neut"}.get(item.get("signal","neut"), "neut")
        with cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card {card_cls}">
                <div class="metric-label">{item.get('name','')}</div>
                <div class="metric-value">{item.get('value','')}</div>
                <span class="tag {tag_cls}">{item.get('comment','')}</span>
            </div>
            """, unsafe_allow_html=True)


def display_factor_bars(factors):
    color_map   = {"bear": "#e74c3c", "bull": "#27ae60", "neut": "#f39c12"}
    tag_cls_map = {"bear": "tag-bear", "bull": "tag-bull", "neut": "tag-neut"}
    for f in factors:
        score   = int(f.get('score', 50))
        color   = color_map.get(f.get('color','neut'), '#f39c12')
        tag_cls = tag_cls_map.get(f.get('color','neut'), 'tag-neut')
        st.markdown(f"""
        <div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
                <span style="font-size:12px;color:#2c3e50">{f.get('name','')}</span>
                <span class="tag {tag_cls}">{f.get('direction','')}</span>
            </div>
            <div style="background:#e8e8e8;height:7px;border-radius:3px;overflow:hidden">
                <div style="width:{score}%;background:{color};height:7px;border-radius:3px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def display_probability_chart(prob_data):
    labels = [p['range'] for p in prob_data]
    values = [p['prob'] for p in prob_data]
    bar_colors = {'bear': '#e74c3c', 'bull': '#27ae60', 'neut': '#95a5a6'}
    colors = [bar_colors.get(p.get('color','neut'), '#95a5a6') for p in prob_data]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation='h',
        marker_color=colors,
        text=[f"{v}%" for v in values], textposition='outside',
    ))
    fig.update_layout(
        height=220, margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor='white', plot_bgcolor='white',
        xaxis=dict(range=[0, max(values)+12], showgrid=True,
                   gridcolor='rgba(0,0,0,0.05)', ticksuffix='%', tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=11)), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def display_trade_box(trade, direction):
    if not trade or not trade.get('enabled', True):
        return
    is_short = direction == 'short'
    box_cls  = 'trade-short' if is_short else 'trade-long'
    label    = '做空' if is_short else '做多'
    emoji    = '🔴' if is_short else '🟢'
    prob     = trade.get('probability', 0)
    sl  = trade.get('stop_loss', 0)
    tp1 = trade.get('tp1', 0)
    tp2 = trade.get('tp2', 0)

    st.markdown(f"""
    <div class="trade-box {box_cls}">
        <div class="trade-title">{emoji} {label}方向 · 主場景概率 {prob}%</div>
        <div style="font-size:12px;color:#555;margin-bottom:10px">
            <b>入場方式：</b>{trade.get('entry_type','')}<br>
            <b>入場區間：</b>{trade.get('entry_zone','')}
        </div>
        <div class="price-grid">
            <div class="price-item">
                <div class="price-label">止損</div>
                <div class="price-val bear">${sl:.2f}</div>
            </div>
            <div class="price-item">
                <div class="price-label">止盈 T1</div>
                <div class="price-val bull">${tp1:.2f}</div>
            </div>
            <div class="price-item">
                <div class="price-label">止盈 T2</div>
                <div class="price-val bull">${tp2:.2f}</div>
            </div>
        </div>
        <div style="margin-top:10px;font-size:12px;color:#555">
            <b>風險回報：</b>{trade.get('rr_ratio','')} &nbsp;·&nbsp;
            <b>建議倉位：</b>{trade.get('position_size','')}
        </div>
        <div style="margin-top:8px;font-size:11px;color:#777;border-top:1px solid #eee;padding-top:8px">
            <b>觸發條件：</b>{trade.get('trigger','')}<br>
            <b>理由：</b>{trade.get('rationale','')}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── 複盤模組（使用 st.session_state 替代本地文件）───
def get_history():
    if 'prediction_history' not in st.session_state:
        st.session_state['prediction_history'] = []
    return st.session_state['prediction_history']

def save_prediction(ticker, period, price, bias, key_levels):
    history = get_history()
    record = {
        "id":               datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker":           ticker,
        "period":           period,
        "price_at_analysis": price,
        "bias":             bias,
        "key_levels":       key_levels,
        "actual_close":     None,
        "hit":              None,
    }
    history.append(record)
    return record["id"]

def update_actual(record_id, actual_price):
    history = get_history()
    for r in history:
        if r["id"] == record_id:
            r["actual_close"] = actual_price
            pred_price = r.get("price_at_analysis", 0)
            bias = r.get("bias", "neutral")
            if bias == "bearish":
                r["hit"] = "✅ 命中" if actual_price < pred_price else "❌ 未命中"
            elif bias == "bullish":
                r["hit"] = "✅ 命中" if actual_price > pred_price else "❌ 未命中"
            else:
                r["hit"] = "⚪ 中性"
            break


# ─────────────────────────────────────────────
# 多股票 Dashboard 渲染
# ─────────────────────────────────────────────
def render_multi_dashboard(tickers: list, period_key: str):
    st.markdown('<div class="section-header">📊 多股票快速掃描 Dashboard</div>', unsafe_allow_html=True)

    if not tickers:
        st.warning("請先選擇或輸入股票清單")
        return

    # 並發下載數據
    progress_bar = st.progress(0)
    status_text  = st.empty()

    results = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=min(len(tickers), 6)) as executor:
        future_map = {executor.submit(load_quick_data, t): t for t in tickers}
        for future in as_completed(future_map):
            t = future_map[future]
            try:
                data = future.result(timeout=20)
                results[t] = data
            except Exception as e:
                results[t] = None
            completed += 1
            progress_bar.progress(completed / len(tickers))
            status_text.text(f"已完成 {completed}/{len(tickers)} 支股票數據載入...")

    progress_bar.empty()
    status_text.empty()

    # 排序：偏多 > 中性 > 偏空，再按信號分數
    order = {"bullish": 0, "neutral": 1, "bearish": 2}
    valid = [(t, d) for t, d in results.items() if d is not None]
    valid.sort(key=lambda x: (order.get(x[1]['bias'], 1), -x[1]['score']))
    failed = [t for t, d in results.items() if d is None]

    if failed:
        st.warning(f"⚠️ 以下股票載入失敗，已略過：{', '.join(failed)}")

    # ── 彙總表 ──
    st.markdown("#### 📋 彙總覽表")
    table_rows = []
    for t, d in valid:
        bias_emoji = "🟢" if d['bias']=='bullish' else "🔴" if d['bias']=='bearish' else "⚪"
        chg_str = f"{d['pct']:+.2f}%"
        table_rows.append({
            "股票": f"{bias_emoji} {d['ticker']}",
            "名稱": d['name'][:20],
            "現價": f"${d['curr']:.2f}",
            "漲跌": chg_str,
            "RSI": f"{d['rsi']:.1f}",
            "MACD": d['macd_cross'],
            "量比": f"{d['vol_ratio']:.1f}x",
            "信號分": f"{'⭐'*d['score']} ({d['score']}/5)",
            "52W高": f"${d['week52h']:.2f}",
            "52W低": f"${d['week52l']:.2f}",
        })
    if table_rows:
        df_table = pd.DataFrame(table_rows)
        st.dataframe(df_table, use_container_width=True, hide_index=True)

    # ── 卡片視圖 ──
    st.markdown("#### 🃏 卡片視圖")
    cols_per_row = 3
    rows = [valid[i:i+cols_per_row] for i in range(0, len(valid), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, (t, d) in enumerate(row):
            with cols[idx]:
                bias    = d['bias']
                card_cls = "bull-card" if bias=='bullish' else "bear-card" if bias=='bearish' else "neut-card"
                chg_cls  = "stock-chg-up" if d['pct'] >= 0 else "stock-chg-down"
                chg_sign = "▲" if d['pct'] >= 0 else "▼"

                rsi_color = "#e74c3c" if d['rsi']>70 else "#27ae60" if d['rsi']<30 else "#888"
                bias_emoji = "🟢 偏多" if bias=='bullish' else "🔴 偏空" if bias=='bearish' else "⚪ 中性"
                score_stars = "⭐" * d['score'] + "☆" * (5 - d['score'])

                st.markdown(f"""
                <div class="stock-card {card_cls}">
                    <div class="stock-ticker">{d['ticker']}</div>
                    <div class="stock-name">{d['name'][:24]}</div>
                    <div class="stock-price {chg_cls}">${d['curr']:.2f}
                        <span style="font-size:13px"> {chg_sign}{abs(d['pct']):.2f}%</span>
                    </div>
                    <div class="mini-grid">
                        <div class="mini-item"><div class="mini-label">RSI</div>
                            <div class="mini-val" style="color:{rsi_color}">{d['rsi']:.1f}</div></div>
                        <div class="mini-item"><div class="mini-label">MACD</div>
                            <div class="mini-val">{d['macd_cross']}</div></div>
                        <div class="mini-item"><div class="mini-label">量比</div>
                            <div class="mini-val">{d['vol_ratio']:.1f}x</div></div>
                        <div class="mini-item"><div class="mini-label">ATR</div>
                            <div class="mini-val">${d['atr']:.2f}</div></div>
                    </div>
                    <div style="margin-top:8px;font-size:12px">
                        <span style="color:#888">信號：</span>{score_stars}<br>
                        <b>{bias_emoji}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 迷你 K 線
                mini_fig = build_mini_chart(d['df'], t, bias)
                st.plotly_chart(mini_fig, use_container_width=True, config={'displayModeBar': False})

                # 點擊深入分析按鈕
                if st.button(f"🔍 深入分析 {t}", key=f"deep_{t}_{period_key}"):
                    st.session_state['deep_analysis_ticker'] = t
                    st.session_state['active_tab'] = 'single'
                    st.rerun()

    # ── 相關性熱力圖 ──
    if len(valid) >= 3:
        st.markdown("#### 🔗 股票相關性矩陣（近3月日收益率）")
        try:
            tickers_valid = [t for t, _ in valid]
            all_closes = {}
            for t, d in valid:
                if 'df' in d and len(d['df']) >= 20:
                    all_closes[t] = d['df']['Close'].pct_change().dropna()

            if len(all_closes) >= 2:
                corr_df = pd.DataFrame(all_closes).corr()
                mask = np.tril(np.ones_like(corr_df, dtype=bool))
                z_vals = corr_df.values
                labels = corr_df.columns.tolist()

                heatmap_fig = go.Figure(go.Heatmap(
                    z=z_vals, x=labels, y=labels,
                    colorscale='RdYlGn', zmin=-1, zmax=1,
                    text=np.round(z_vals, 2),
                    texttemplate='%{text}',
                    textfont={"size": 11},
                ))
                heatmap_fig.update_layout(
                    height=300 + len(labels)*20,
                    margin=dict(l=10, r=10, t=20, b=10),
                    paper_bgcolor='white',
                )
                st.plotly_chart(heatmap_fig, use_container_width=True)
        except:
            pass


# ─────────────────────────────────────────────
# 單股票深入分析
# ─────────────────────────────────────────────
def render_single_analysis(ticker: str, period_key: str):
    if not ticker:
        st.warning("請輸入股票代號")
        return

    with st.spinner(f"正在載入 {ticker} 市場數據..."):
        df, macro, err = load_market_data(ticker, period_key)

    if err or df is None or df.empty:
        st.error(f"❌ 無法取得 {ticker} 的數據：{err}")
        return

    with st.spinner("計算技術指標..."):
        ind = compute_indicators(df)

    with st.spinner("抓取最新新聞..."):
        news = fetch_news(ticker, macro.get("company_name", ticker))

    with st.spinner("🤖 Groq AI 深度分析中（約 10–20 秒）..."):
        analysis, error = run_groq_analysis(ticker, period_key, df, macro, ind, news)

    if error:
        st.error(error)
        return

    # ── 頂部摘要 ──
    curr_price = safe_float(df['Close'].iloc[-1])
    prev_close = safe_float(df['Close'].iloc[-2]) if len(df) > 1 else curr_price
    pct_chg    = (curr_price - prev_close) / prev_close * 100 if prev_close else 0
    bias       = analysis.get("bias", "neutral")
    bias_map   = {"bullish": ("🟢 偏多", "#27ae60"), "bearish": ("🔴 偏空", "#e74c3c"), "neutral": ("⚪ 中性", "#888")}
    bias_label, bias_color = bias_map.get(bias, ("⚪ 中性", "#888"))

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"### {macro.get('company_name', ticker)} ({ticker})")
        st.caption(f"{macro.get('sector','')} · {PERIOD_MAP[period_key]['label']} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with col2:
        st.metric("當前價格", f"${curr_price:.2f}", f"{pct_chg:+.2f}%")
    with col3:
        vix_close = macro.get('vix', {}).get('close', 0)
        vix_chg_v = macro.get('vix', {}).get('chg', 0)
        st.metric("VIX", f"{vix_close:.2f}", f"{vix_chg_v:+.1f}%")
    with col4:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0">
            <div style="font-size:11px;color:#888">AI 偏向</div>
            <div style="font-size:22px;font-weight:700;color:{bias_color}">{bias_label}</div>
            <div style="font-size:11px;color:#888">強度 {analysis.get('bias_strength',5)}/10</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#f0f4ff;border-left:4px solid #3498db;
                border-radius:8px;padding:12px 16px;margin:12px 0">
        <div style="font-size:12px;color:#888;margin-bottom:4px">📊 AI 核心判斷</div>
        <div style="font-size:14px;color:#2c3e50;line-height:1.7">{analysis.get('summary','')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📊 技術分析圖表</div>', unsafe_allow_html=True)
    fig = build_chart(df, ind, analysis, ticker, period_key)
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown('<div class="section-header">🌍 宏觀環境評分</div>', unsafe_allow_html=True)
        macro_scores = analysis.get("macro_scores", [])
        if macro_scores:
            display_macro(macro_scores)

        st.markdown('<div class="section-header">🎯 多因子信號評分</div>', unsafe_allow_html=True)
        factors = analysis.get("factor_scores", [])
        if factors:
            display_factor_bars(factors)

    with right:
        st.markdown('<div class="section-header">📰 新聞情緒</div>', unsafe_allow_html=True)
        news_sent = analysis.get("news_sentiment", "neut")
        sent_map  = {"bear": ("🔴 偏空","tag-bear"), "bull": ("🟢 偏多","tag-bull"), "neut": ("⚪ 中性","tag-neut")}
        sent_label, sent_cls = sent_map.get(news_sent, ("⚪ 中性","tag-neut"))
        st.markdown(f"""
        <div style="margin-bottom:10px">
            <span class="tag {sent_cls}">{sent_label}</span>
            <span style="font-size:12px;color:#555;margin-left:8px">{analysis.get('news_summary','')}</span>
        </div>
        """, unsafe_allow_html=True)
        for n in news[:6]:
            st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{n['title'][:80]}{'...' if len(n['title'])>80 else ''}</div>
                <div class="news-meta">{n['date']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📈 走勢概率分布</div>', unsafe_allow_html=True)
    prob_data = analysis.get("probability", [])
    if prob_data:
        display_probability_chart(prob_data)

    st.markdown('<div class="section-header">💼 入場—止損—止盈 規則集</div>', unsafe_allow_html=True)
    col_s, col_l = st.columns(2)
    with col_s:
        display_trade_box(analysis.get("trade_short"), "short")
    with col_l:
        display_trade_box(analysis.get("trade_long"), "long")

    invalidation = analysis.get("invalidation", [])
    if invalidation:
        st.markdown(f"""
        <div class="trade-box trade-warn">
            <div class="trade-title">⚠️ 場景無效化條件（立即離場）</div>
            {"".join([f'<div style="font-size:12px;color:#7d6608;margin:4px 0">• {c}</div>' for c in invalidation])}
        </div>
        """, unsafe_allow_html=True)

    save_prediction(ticker, period_key, curr_price, bias, analysis.get("key_levels", {}))
    st.markdown("---")
    st.caption(f"⏱️ 分析完成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · LLaMA-3.3-70B via Groq · RSI/ATR 使用 Wilder Smoothing")


# ─────────────────────────────────────────────
# 主界面
# ─────────────────────────────────────────────
def main():
    st.markdown('<div class="main-title">📈 多股票智能分析系統</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Groq LLaMA-3.3-70B · 技術面 + 宏觀 + 情緒 · 多股票並發掃描 · 入場/止損/止盈</div>', unsafe_allow_html=True)

    # Session state 初始化
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 'multi'
    if 'deep_analysis_ticker' not in st.session_state:
        st.session_state['deep_analysis_ticker'] = 'TSLA'

    # ── 側邊欄 ──
    with st.sidebar:
        st.markdown("### ⚙️ 分析設定")

        period_key = st.selectbox(
            "時間週期",
            options=list(PERIOD_MAP.keys()),
            format_func=lambda x: f"{x} — {PERIOD_MAP[x]['label']}",
            index=1, key="period_select"
        )

        st.markdown("---")
        st.markdown("### 📋 多股票掃描")
        watchlist_name = st.selectbox("預設股票組合", options=list(PRESET_WATCHLISTS.keys()))
        preset_tickers = PRESET_WATCHLISTS[watchlist_name]

        custom_input = st.text_area(
            "自訂股票（每行一個或逗號分隔）",
            value="\n".join(preset_tickers) if watchlist_name != "自選" else "TSLA\nAAPL\nNVDA\nMSFT\nMETA",
            height=160,
            help="支援任意美股代號",
        )

        # 解析輸入
        raw_tickers = re.split(r'[\n,\s]+', custom_input.upper().strip())
        multi_tickers = [t.strip() for t in raw_tickers if t.strip() and re.match(r'^[A-Z\.\^]{1,8}$', t.strip())]
        multi_tickers = list(dict.fromkeys(multi_tickers))  # 去重保順序

        st.caption(f"已選 {len(multi_tickers)} 支股票：{', '.join(multi_tickers[:8])}{'...' if len(multi_tickers)>8 else ''}")

        scan_btn = st.button("🚀 啟動多股票掃描", type="primary", use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔍 單股票深入分析")
        single_ticker = st.text_input(
            "股票代號",
            value=st.session_state.get('deep_analysis_ticker', 'TSLA'),
            key="single_ticker_input"
        ).upper().strip()
        analyze_btn = st.button("📊 深入分析", use_container_width=True)

        # ── 複盤追蹤 ──
        st.markdown("---")
        st.markdown("### 📋 複盤追蹤")
        history = get_history()
        ticker_history = [h for h in history if h.get('ticker') == single_ticker]
        if ticker_history:
            st.markdown(f"**{single_ticker}** 共 {len(ticker_history)} 筆記錄")
            for rec in ticker_history[-3:][::-1]:
                hit_icon = rec.get('hit', '⏳')
                st.markdown(f"""
                <div class="prediction-history">
                    <div style="font-size:12px;font-weight:600">{rec['timestamp']} · {rec['period']}</div>
                    <div style="font-size:11px;color:#555">${rec['price_at_analysis']:.2f} · {rec['bias']}</div>
                    <div style="font-size:11px">{hit_icon}</div>
                </div>
                """, unsafe_allow_html=True)

            pending = [r for r in ticker_history if r.get('hit') is None]
            if pending:
                st.markdown("**更新實際收盤：**")
                rec_opts = {r['id']: f"{r['timestamp']} (${r['price_at_analysis']:.2f})" for r in pending}
                sel_id = st.selectbox("選擇記錄", list(rec_opts.keys()), format_func=lambda x: rec_opts[x])
                actual = st.number_input("實際收盤價 $", min_value=0.01, step=0.01)
                if st.button("更新複盤"):
                    update_actual(sel_id, actual)
                    st.success("✅ 已更新")
                    st.rerun()

            completed_recs = [r for r in ticker_history if r.get('hit') and r['hit'] != '⚪ 中性']
            if completed_recs:
                hits = sum(1 for r in completed_recs if '✅' in r.get('hit',''))
                rate = hits / len(completed_recs) * 100
                st.metric("方向命中率", f"{rate:.0f}%", f"{hits}/{len(completed_recs)}")

        st.markdown("---")
        st.caption("⚠️ 本工具僅供參考，不構成投資建議。交易有風險，請自行判斷。")

    # ── 主體：Tab 式佈局 ──
    tab1, tab2 = st.tabs(["🌐 多股票 Dashboard", "📊 單股票深入分析"])

    with tab1:
        if scan_btn or st.session_state.get('_multi_loaded'):
            if scan_btn:
                st.session_state['_multi_loaded'] = True
                st.session_state['_multi_tickers'] = multi_tickers
                st.session_state['_multi_period']  = period_key
            render_multi_dashboard(
                st.session_state.get('_multi_tickers', multi_tickers),
                st.session_state.get('_multi_period', period_key)
            )
        else:
            st.info("👆 在左側選擇股票組合，點擊「啟動多股票掃描」開始")
            st.markdown("""
            **多股票掃描功能：**
            - 🚀 並發下載，同時分析最多 10+ 支股票
            - 📋 彙總覽表：現價、漲跌、RSI、MACD、量比、信號分
            - 🃏 卡片視圖：含迷你走勢圖
            - 🔗 相關性熱力圖
            - 🔍 一鍵跳轉單股票深入分析
            """)

    with tab2:
        # 若從多股票卡片點擊跳轉
        jump_ticker = st.session_state.get('deep_analysis_ticker', '')
        display_ticker = single_ticker or jump_ticker

        if analyze_btn or (st.session_state.get('active_tab') == 'single' and display_ticker):
            if analyze_btn:
                st.session_state['deep_analysis_ticker'] = single_ticker
            st.session_state['active_tab'] = 'single'
            render_single_analysis(display_ticker, period_key)
        else:
            st.info("👈 在左側輸入股票代號，點擊「深入分析」")
            st.markdown("""
            **深入分析功能：**
            - 📊 互動式 K 線圖（均線 + 布林帶 + 支撐阻力）
            - 🌍 宏觀環境評分（VIX / SPX / 美債 / 油價）
            - 📰 新聞情緒（Google News RSS）
            - 🎯 多因子信號評分
            - 📈 5區間概率分布（VIX 尾部校準）
            - 💼 入場—止損—止盈規則集（ATR 動態計算）
            - 🔄 複盤命中率追蹤
            """)


if __name__ == "__main__":
    main()
