import datetime
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ページの設定（ワイドモードで広く見やすく）
st.set_page_config(page_title="ACWI 高級ダッシュボード", layout="wide")

# カスタムCSSでデザインを少しリッチに調整
st.markdown("""
    <style>
    .metric-container { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🌐 ACWI（全世界株式）投資ダッシュボード")

# サイドバーの設定
st.sidebar.header("📊 表示設定")
period_choice = st.sidebar.selectbox(
    "表示期間",
    options=["1ヶ月 (1m)", "3ヶ月 (3m)", "6ヶ月 (6m)", "1年 (1y)", "5年 (5y)", "全期間 (max)"],
    index=3
)

period_mapping = {
    "1ヶ月 (1m)": "1mo",
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
    # 出来高なども含めて1日単位のデータを取得
    history = stock.history(period=period, interval="1d")
    return stock.info, history


try:
    with st.spinner("リアルタイムデータを読み込み中..."):
        info, df_history = get_acwi_data(selected_period)

    if not df_history.empty:
        # 価格情報の抽出
        current_price = info.get('regularMarketPrice') or info.get('currentPrice') or df_history['Close'].iloc[-1]
        previous_close = info.get('previousClose') or df_history['Close'].iloc[-2]

        # 前日比の計算
        price_diff = current_price - previous_close
        price_diff_pct = (price_diff / previous_close) * 100
        currency = info.get('currency', 'USD')

        # ----------------- 1. 上部メトリクス（主要指標） -----------------
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

        # ----------------- 2. グラフィカルなPlotlyチャート -----------------
        st.subheader(f"📈 詳細株価推移 ({period_choice})")

        # Plotlyでエリア（面）グラフを作成
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_history.index,
            y=df_history['Close'],
            mode='lines',
            fill='tozeroy',  # 下部を塗りつぶし
            fillcolor='rgba(26, 115, 232, 0.1)',  # 薄い青色のグラデーション風
            line=dict(color='#1A73E8', width=2.5),
            name="終値 (Close)",
            hovertemplate="<b>日付:</b> %{x|%Y/%m/%d}<br><b>株価:</b> %{y:,.2f} ドル<extra></extra>"
        ))

        # グラフのデザインを洗練させる
        fig.update_layout(
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=0, r=0, t=10, b=0),
            height=450,
            xaxis=dict(
                showgrid=True,
                gridcolor='#f0f0f0',
                linecolor='#d0d0d0',
                title_text=""
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#f0f0f0',
                linecolor='#d0d0d0',
                title_text=f"価格 ({currency})",
                side="right"  # 投資サイトのように右側に軸を配置
            )
        )

        # Streamlit画面にグラフを出力
        st.plotly_chart(fig, use_container_width=True)

        # ----------------- 3. 下部詳細データ -----------------
        with st.expander("📊 直近のデータテーブルを表示"):
            # 日付を見やすく整形して最新順に表示
            df_display = df_history[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).copy()
            df_display.index = df_display.index.strftime('%Y/%m/%d')
            st.dataframe(df_display.iloc[::-1], use_container_width=True)

    else:
        st.warning("チャートデータの取得に失敗しました。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
