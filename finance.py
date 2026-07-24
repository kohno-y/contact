import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ページの設定（ワイドモードで広く見やすく）
st.set_page_config(page_title="ACWI MACDダッシュボード", layout="wide")

st.title("🌐 ACWI（全世界株式）MACD 投資ダッシュボード")

# サイドバーの設定
st.sidebar.header("📊 表示設定")
period_choice = st.sidebar.selectbox(
    "表示期間",
    options=["3ヶ月 (3m)", "6ヶ月 (6m)", "1年 (1y)", "5年 (5y)", "全期間 (max)"],
    index=2  # デフォルトは1年
)

period_mapping = {
    "3ヶ月 (3m)": "3mo",
    "6ヶ月 (6m)": "6mo",
    "1年 (1y)": "1y",
    "5年 (5y)": "5y",
    "全期間 (max)": "max"
}
selected_period = period_mapping[period_choice]


@st.cache_data(ttl=3600)
def get_acwi_data(period):
    stock = yf.Ticker("ACWI")
    # MACDの計算（12日・26日）を正確に行うため、少し長めに過去データを取得して後で切り出す
    history = stock.history(period="max", interval="1d")
    return stock.info, history


try:
    with st.spinner("リアルタイムデータを読み込み中..."):
        info, df_all = get_acwi_data(selected_period)

    if not df_all.empty:
        # --- MACDの計算 ---
        # 1. 短期（12日）と長期（26日）の指数平滑移動平均（EMA）を計算
        ema12 = df_all['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df_all['Close'].ewm(span=26, adjust=False).mean()
        # 2. MACD線を算出
        df_all['MACD'] = ema12 - ema26
        # 3. シグナル線（MACDの9日EMA）を算出
        df_all['Signal'] = df_all['MACD'].ewm(span=9, adjust=False).mean()
        # 4. ヒストグラム（MACDとシグナルの差）を算出
        df_all['Hist'] = df_all['MACD'] - df_all['Signal']

        # 選択された期間に応じて表示データをフィルタリング
        # yfinanceのhistory(period=...)と挙動を合わせるための簡易スライス
        now = df_all.index[-1]
        if selected_period == "3mo":
            start_date = now - datetime.timedelta(days=90)
        elif selected_period == "6mo":
            start_date = now - datetime.timedelta(days=180)
        elif selected_period == "1y":
            start_date = now - datetime.timedelta(days=365)
        elif selected_period == "5y":
            start_date = now - datetime.timedelta(days=365 * 5)
        else:
            start_date = df_all.index[0]

        df_history = df_all.loc[start_date:]

        # 価格情報の抽出
        current_price = info.get('regularMarketPrice') or info.get('currentPrice') or df_history['Close'].iloc[-1]
        previous_close = info.get('previousClose') or df_history['Close'].iloc[-2]

        price_diff = current_price - previous_close
        price_diff_pct = (price_diff / previous_close) * 100
        currency = info.get('currency', 'USD')

        # 上部メトリクス（主要指標）
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="現在の株価",
                value=f"{current_price:,.2f} {currency}",
                delta=f"{price_diff:+,.2f} ({price_diff_pct:+.2f}%)"
            )
        with col2:
            st.metric(label="本日の始値", value=f"{df_history['Open'].iloc[-1]:,.2f}")
        with col3:
            st.metric(label="52週最高値", value=f"{info.get('fiftyTwoWeekHigh', 0):,.2f}")
        with col4:
            st.metric(label="52週最安値", value=f"{info.get('fiftyTwoWeekLow', 0):,.2f}")

        st.markdown("---")

        # --- 2段構成のグラフを作成（上が株価、下がMACD） ---
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,  # 上下のグラフの横軸（日付）を連動させる
            vertical_spacing=0.05,  # グラフ間の隙間
            row_heights=[0.6, 0.4]  # 比率（株価60%、MACD40%）
        )

        # 【上段】株価エリアグラフ
        fig.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history['Close'],
            mode='lines',
            fill='tozeroy',
            fillcolor='rgba(26, 115, 232, 0.05)',
            line=dict(color='#1A73E8', width=2.5),
            name="株価 (Close)",
            hovertemplate="<b>株価:</b> %{y:,.2f} ドル<extra></extra>"
        ), row=1, col=1)

        # 【下段】MACD線（青）
        fig.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history['MACD'],
            mode='lines',
            line=dict(color='#00D1B2', width=1.5),
            name="MACD",
            hovertemplate="<b>MACD:</b> %{y:.3f}<extra></extra>"
        ), row=2, col=1)

        # 【下段】シグナル線（赤・点線）
        fig.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history['Signal'],
            mode='lines',
            line=dict(color='#FF3860', width=1.5, dash='dot'),
            name="Signal",
            hovertemplate="<b>Signal:</b> %{y:.3f}<extra></extra>"
        ), row=2, col=1)

        # 【下段】ヒストグラム（棒グラフ）
        # プラスは薄い緑、マイナスは薄い赤に色分け
        hist_colors = ['rgba(76, 175, 80, 0.6)' if val >= 0 else 'rgba(244, 67, 54, 0.6)' for val in df_history['Hist']]
        fig.add_trace(go.Bar(
            x=df_history.index,
            y=df_history['Hist'],
            marker_color=hist_colors,
            name="Histogram",
            hovertemplate="<b>Hist:</b> %{y:.3f}<extra></extra>"
        ), row=2, col=1)

        # 全体のデザイン調整
        fig.update_layout(
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=0, r=0, t=10, b=0),
            height=650,  # 二画面にするため全体の高さを少し高く
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # 軸の見た目の調整
        fig.update_xaxes(showgrid=True, gridcolor='#f0f0f0', linecolor='#d0d0d0')
        fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', linecolor='#d0d0d0', side="right")

        # 各グラフの縦軸ラベル
        fig.update_yaxes(title_text=f"価格 ({currency})", row=1, col=1)
        fig.update_yaxes(title_text="MACD", row=2, col=1)

        # 画面に描画
        st.plotly_chart(fig, use_container_width=True)

        # 下部詳細データ
        with st.expander("📊 直近のデータテーブルを表示"):
            df_display = df_history[['Open', 'High', 'Low', 'Close', 'MACD', 'Signal']].tail(10).copy()
            df_display.index = df_display.index.strftime('%Y/%m/%d')
            st.dataframe(df_display.iloc[::-1], use_container_width=True)

    else:
        st.warning("チャートデータの取得に失敗しました。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")