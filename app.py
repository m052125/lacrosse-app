import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="選手別シュート分析", layout="wide", page_icon="🥍")
st.title("🥍 選手別シュート分析ダッシュボード")

try:
    # データの読み込み
    df = pd.read_csv('FreeShootData.csv')
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    df['結果数値'] = (df['結果'] == 'ゴール').astype(int)
    
    # 選手リストの作成
    player_ids = sorted(df['背番号'].unique().astype(str))
    tab_titles = ["チーム全体"] + player_ids
    
    # === 選手ごとにタブを作成 ===
    tabs = st.tabs(tab_titles)

    for i, tab in enumerate(tabs):
        target_player = tab_titles[i]
        
        with tab:
            # データの絞り込み
            if target_player == "チーム全体":
                display_df = df
                st.header("🏢 チーム全体の分析")
            else:
                display_df = df[df['背番号'].astype(str) == target_player]
                st.header(f"🏃 選手詳細: {target_player}")

            # --- ① 基本スコア ---
            col1, col2, col3 = st.columns(3)
            total_shots = len(display_df)
            total_goals = display_df['結果数値'].sum()
            rate = total_goals / total_shots if total_shots > 0 else 0
            
            col1.metric("総シュート数", f"{total_shots}本")
            col2.metric("総ゴール数", f"{total_goals}本")
            col3.metric("ゴール決定率", f"{rate:.1%}")
            
            st.divider()

            # --- ② 分析グラフ（推移とヒートマップ） ---
            col_graph_left, col_graph_right = st.columns([3, 2])

            with col_graph_left:
                st.subheader("📈 ゴール決定率の推移")
                trend_df = display_df.groupby('日時').agg(決定率=('結果数値', 'mean')).reset_index()
                trend_df['決定率'] = (trend_df['決定率'] * 100).round(1)
                
                fig_line = px.line(trend_df, x='日時', y='決定率', markers=True, text='決定率')
                fig_line.update_traces(textposition="top center", line_color="#3366CC")
                fig_line.update_layout(yaxis_range=[-5, 110], height=400)
                
                # 🌟 エラー対策：keyに選手名を入れる
                st.plotly_chart(fig_line, use_container_width=True, key=f"line_chart_{target_player}")

            with col_graph_right:
                st.subheader("🔥 コース別ゴール数")
                goals = display_df[display_df['結果'] == 'ゴール']
                grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
                z_data = np.zeros((3, 3))
                counts = goals['コース'].value_counts()
                for r in range(3):
                    for c in range(3):
                        val = grid_names[r][c]
                        z_data[r][c] = counts.get(int(val), 0) + counts.get(str(val), 0)

                fig_heat = px.imshow(
                    z_data, x=['左', '中央', '右'], y=['上', '中', '下'],
                    text_auto=True, color_continuous_scale="Reds"
                )
                fig_heat.update_layout(width=350, height=350, margin=dict(l=20, r=20, t=20, b=20))
                
                # 🌟 エラー対策：keyに選手名を入れる
                st.plotly_chart(fig_heat, use_container_width=False, key=f"heat_map_{target_player}")

            # --- ③ 詳細データの出力（表） ---
            st.divider()
            st.subheader("📋 記録データ一覧")
            output_df = display_df[['日時', '打つ位置', 'コース', '結果']].sort_values('日時', ascending=False)
            st.dataframe(output_df, use_container_width=True, height=300)

except Exception as e:
    st.error(f"データの読み込み中にエラーが発生しました: {e}")
