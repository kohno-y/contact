import streamlit as st
import yfinance as yf

# ページの設定
st.set_page_config(page_title="株価チェッカー", layout="centered")

# タイトルの表示
st.title("🌐 全世界株式（ACWI）株価情報")


# yfinanceからデータを取得
@st.cache_data(ttl=3600)  # 1時間キャッシュしてデータ取得を高速化
def get_stock_data():
    stock = yf.Ticker("ACWI")
    return stock.info


try:
    with st.spinner("データを取得中..."):
        info = get_stock_data()

    # 状況に応じて適切な価格キーを取得（infoの仕様変更対策）
    current_price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
    currency = info.get('currency', 'USD')

    if current_price:
        # メトリック（大きな文字）で株価を表示
        st.metric(label="現在の株価", value=f"{current_price} {currency}")

        # 追加情報の表示（オマケ）
        with st.expander("詳細情報を表示"):
            st.write(f"**企業・ファンド名:** {info.get('longName')}")
            st.write(f"**本日の最高値:** {info.get('dayHigh')} {currency}")
            st.write(f"**本日の最安値:** {info.get('dayLow')} {currency}")
    else:
        st.error("株価データの取得に失敗しました。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")