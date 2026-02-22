import streamlit as st
import pandas as pd
import plotly.express as px  # 最新のグラフツール
import numpy as np

# ページの設定
st.set_page_config(page_title="シュート分析", layout="wide")
st.title("🥍 ラクロス部 シュート分析ダッシュボード")

try:
    # データの読み込み
    df = pd.read_csv('FreeShootData.csv')
    df['結果数値'] = (df['結果'] == 'ゴール').astype(int)
    
    # --- サイドバーで絞り込み ---
    st.sidebar.header("絞り込み設定")
    player_list = ['全体'] + sorted(list(df['背番号'].unique().astype(str)))
    selected_player = st.sidebar.selectbox("選手を選択", player_list)
    
    if selected_player != '全体':
        display_df = df[df['背番号'].astype(str) == selected_player]
        st.subheader(f"📊 分析対象: {selected_player}")
    else:
        display_df = df
        st.subheader("📊 分析対象: 全体")

    # --- ① スコア表示 ---
    col1, col2, col3 = st.columns(3)
    total_shots = len(display_df)
    total_goals = display_df['結果数値'].sum()
    rate = total_goals / total_shots if total_shots > 0 else 0
    
    col1.metric("総シュート数", f"{total_shots}本")
    col2.metric("総ゴール数", f"{total_goals}本")
    col3.metric("ゴール決定率", f"{rate:.1%}")
    
    st.divider()
    
    # --- ② 表の表示（サイズをコンパクトに） ---
    st.header("🏃 シューター別成績")
    shooter_stats = df.groupby('背番号').agg(
        シュート数=('結果', 'count'),
        ゴール数=('結果数値', 'sum')
    ).reset_index()
    shooter_stats['決定率'] = (shooter_stats['ゴール数'] / shooter_stats['シュート数'] * 100).round(1).astype(str) + "%"
    
    # 表の幅を小さく、高さを固定
    st.dataframe(shooter_stats, width=450, height=300, hide_index=True)
    
    st.divider()
    
    # --- ③ ヒートマップ（Plotlyなら日本語が勝手に映る！） ---
    st.header("🔥 コース別ゴール数")
    goals = display_df[display_df['結果'] == 'ゴール']
    
    # 1〜9番のグリッドデータを作成
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    z_data = np.zeros((3, 3))
    
    counts = goals['コース'].value_counts()
    for i in range(3):
        for j in range(3):
            val = grid_names[i][j]
            z_data[i][j] = counts.get(int(val) if val.isdigit() else val, 0)

    # Plotlyでヒートマップ作成（これで日本語化けがなくなります！）
    fig = px.imshow(
        z_data,
        labels=dict(x="左右", y="上下", color="ゴール数"),
        x=['左', '中央', '右'],
        y=['上', '中', '下'],
        text_auto=True,
        color_continuous_scale="Reds"
    )
    # グラフの見た目を調整
    fig.update_layout(width=500, height=500)
    
    st.plotly_chart(fig, use_container_width=False)

# --- ④ 決定率の推移グラフ（新機能！） ---
st.header("📈 ゴール決定率の推移")

# 日付ごとに決定率を計算
trend_df = display_df.groupby('日付').agg(
    決定率=('結果数値', 'mean')
).reset_index()
trend_df['決定率'] = (trend_df['決定率'] * 100).round(1)

# 線グラフを作成
fig_line = px.line(
    trend_df, x='日付', y='決定率',
    title='日別の決定率推移 (%)',
    markers=True
)
st.plotly_chart(fig_line, use_container_width=True)

except FileNotFoundError:
    st.warning("CSVファイルが見つかりません。")

