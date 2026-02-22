import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページの設定：タイトルとアイコン
st.set_page_config(page_title="ラクロス分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 シュート分析ダッシュボード")

try:
    # CSVを読み込む（実際の項目名に合わせます）
    df = pd.read_csv('FreeShootData.csv')
    
    # 日時データを変換（エラーを無視して変換）
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    # ゴール判定を数値化
    df['結果数値'] = (df['結果'] == 'ゴール').astype(int)
    
    # --- サイドバー：フィルタ機能 ---
    st.sidebar.image("https://img.icons8.com/ios-filled/100/ffffff/lacrosse.png", width=80)
    st.sidebar.header("🔍 フィルタ設定")
    
    # 選手の選択
    player_list = ['全体'] + sorted(list(df['背番号'].unique().astype(str)))
    selected_player = st.sidebar.selectbox("選手を選択", player_list)
    
    # 打つ位置の選択（新機能！）
    pos_list = ['すべて'] + sorted(list(df['打つ位置'].unique().astype(str)))
    selected_pos = st.sidebar.selectbox("打つ位置を選択", pos_list)
    
    # データの絞り込み
    display_df = df.copy()
    if selected_player != '全体':
        display_df = display_df[display_df['背番号'].astype(str) == selected_player]
    if selected_pos != 'すべて':
        display_df = display_df[display_df['打つ位置'].astype(str) == selected_pos]

    # --- ① メイン指標（上部に並べる） ---
    col1, col2, col3, col4 = st.columns(4)
    total_shots = len(display_df)
    total_goals = display_df['結果数値'].sum()
    rate = total_goals / total_shots if total_shots > 0 else 0
    
    col1.metric("総シュート数", f"{total_shots}本")
    col2.metric("総ゴール数", f"{total_goals}本")
    col3.metric("ゴール決定率", f"{rate:.1%}")
    col4.metric("選択中の位置", selected_pos)
    
    st.divider()

    # --- ② 決定率の推移グラフ（成長の見える化） ---
    st.header("📈 ゴール決定率の推移")
    # 日付ごとに集計
    trend_df = display_df.groupby('日時').agg(決定率=('結果数値', 'mean')).reset_index()
    trend_df['決定率'] = (trend_df['決定率'] * 100).round(1)
    
    fig_line = px.line(trend_df, x='日時', y='決定率', markers=True, text='決定率',
                      title=f"{selected_player} の成長記録")
    fig_line.update_traces(textposition="top center", line_color="#EF553B")
    fig_line.update_layout(yaxis_range=[-5, 110], height=400)
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()
    
    # --- ③ 下段：成績表 と ヒートマップ を並べる ---
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.header("🏃 選手別ランキング")
        # 選手ごとに集計
        stats = df.groupby('背番号').agg(
            シュート=('結果', 'count'),
            ゴール=('結果数値', 'sum')
        ).reset_index()
        stats['決定率'] = (stats['ゴール'] / stats['シュート'] * 100).round(1)
        stats = stats.sort_values('決定率', ascending=False)
        
        # 表のサイズをコンパクトに（500px幅）
        st.dataframe(stats, width=500, height=400, hide_index=True)

    with right_col:
        st.header("🔥 ゴールコース別")
        goals = display_df[display_df['結果'] == 'ゴール']
        grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
        z_data = np.zeros((3, 3))
        counts = goals['コース'].value_counts()
        for i in range(3):
            for j in range(3):
                val = grid_names[i][j]
                # コース番号が数字か文字列かに関わらず取得できるように
                z_data[i][j] = counts.get(int(val), 0) + counts.get(str(val), 0)

        fig_heat = px.imshow(
            z_data, x=['左', '中央', '右'], y=['上', '中', '下'],
            text_auto=True, color_continuous
