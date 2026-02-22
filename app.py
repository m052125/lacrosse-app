import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="シュート分析", layout="wide")
st.title("🥍 ラクロス部 シュート分析ダッシュボード")

try:
    # 読み込み時に列の名前を強制的に指定する（CSVに1行目がない場合への対策）
    # もしCSVの列の順番が「日時, 背番号, 結果, コース」ならこのままでOKです
    df = pd.read_csv('FreeShootData.csv', names=['日時', '背番号', '結果', 'コース'], header=None)
    
    # 日時データをPythonが扱える形式に変換（時間が含まれていても日付だけに揃える）
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    df['結果数値'] = (df['結果'] == 'ゴール').astype(int)
    
    # --- サイドバー絞り込み ---
    st.sidebar.header("🔍 絞り込み")
    player_list = ['全体'] + sorted(list(df['背番号'].unique().astype(str)))
    selected_player = st.sidebar.selectbox("選手を選択", player_list)
    
    if selected_player != '全体':
        display_df = df[df['背番号'].astype(str) == selected_player]
    else:
        display_df = df

    # --- ① スコア表示 ---
    col1, col2, col3 = st.columns(3)
    total_shots = len(display_df)
    total_goals = display_df['結果数値'].sum()
    rate = total_goals / total_shots if total_shots > 0 else 0
    col1.metric("総シュート数", f"{total_shots}本")
    col2.metric("総ゴール数", f"{total_goals}本")
    col3.metric("決定率", f"{rate:.1%}")
    
    st.divider()

    # --- ② 決定率の推移グラフ（新機能！） ---
    st.header("📈 ゴール決定率の推移")
    trend_df = display_df.groupby('日時').agg(決定率=('結果数値', 'mean')).reset_index()
    trend_df['決定率'] = (trend_df['決定率'] * 100).round(1)
    
    fig_line = px.line(trend_df, x='日時', y='決定率', markers=True, text='決定率')
    fig_line.update_layout(yaxis_range=[0, 105]) # 縦軸を0-100に固定
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()
    
    # --- ③ 表とヒートマップを横に並べる（見た目改善） ---
    col_left, col_right = st.columns([1, 1]) # 画面を5:5で分割

    with col_left:
        st.header("🏃 選手別成績")
        shooter_stats = df.groupby('背番号').agg(
            シュート=('結果', 'count'),
            ゴール=('結果数値', 'sum')
        ).reset_index()
        shooter_stats['決定率'] = (shooter_stats['ゴール'] / shooter_stats['シュート'] * 100).round(1).astype(str) + "%"
        # 表のサイズをコンパクトに
        st.dataframe(shooter_stats, width=400, height=300, hide_index=True)

    with col_right:
        st.header("🔥 コース別ゴール数")
        goals = display_df[display_df['結果'] == 'ゴール']
        grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
        z_data = np.zeros((3, 3))
        counts = goals['コース'].value_counts()
        for i in range(3):
            for j in range(3):
                val = grid_names[i][j]
                z_data[i][j] = counts.get(int(val) if val.isdigit() else str(val), 0)

        fig_heat = px.imshow(
            z_data, x=['左', '中央', 'right'], y=['上', '中', '下'],
            text_auto=True, color_continuous_scale="Reds"
        )
        fig_heat.update_layout(width=400, height=400)
        st.plotly_chart(fig_heat, use_container_width=False)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("CSVファイルの列が『日時, 背番号, 結果, コース』の順になっているか確認してください。")
