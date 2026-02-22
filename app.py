import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="ラクロス総合分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 総合分析ダッシュボード")

# ヒートマップ作成用の共通関数
def create_heatmap(data, title, color_scale, key_id):
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    z = np.zeros((3, 3))
    counts = data['コース'].value_counts()
    for r in range(3):
        for c in range(3):
            val = grid_names[r][c]
            z[r][c] = counts.get(int(val), 0) + counts.get(str(val), 0)
    
    fig = px.imshow(
        z, x=['左', '中', '右'], y=['上', '中', '下'],
        text_auto=True, color_continuous_scale=color_scale, title=title
    )
    fig.update_layout(width=350, height=350, margin=dict(l=20, r=20, t=40, b=20))
    return st.plotly_chart(fig, use_container_width=False, key=key_id)

try:
    # データの読み込み
    df = pd.read_csv('FreeShootData.csv')
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    
    # 基本判定フラグの作成
    df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
    df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
    df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)

    # リスト取得
    shooter_ids = sorted(df['背番号'].unique().astype(str))
    goalie_names = sorted(df['ゴーリー'].unique().astype(str))
    
    # === メインタブ構成 ===
    tab_list = ["チーム全体", "🧤 ゴーリー集計"] + [f"🏃 {s}" for s in shooter_ids] + [f"🧤 {g}" for g in goalie_names]
    tabs = st.tabs(tab_list)

    # --- 1. チーム全体タブ ---
    with tabs[0]:
        st.header("🏢 チーム全体の成績")
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            total_s = len(df)
            total_g = df['ゴール'].sum()
            st.metric("総シュート数", f"{total_s}本")
            st.metric("総ゴール数", f"{total_g}本")
            st.metric("チーム決定率", f"{total_g/total_s:.1%}" if total_s > 0 else "0%")
        
        with col2:
            st.subheader("🔥 チーム得点コース")
            create_heatmap(df[df['結果'] == 'ゴール'], "チーム全体の得点傾向", "Reds", "overall_heat")

        with col3:
            st.subheader("📋 直近のデータ")
            st.dataframe(df.sort_values('日時', ascending=False).head(10), use_container_width=True)

    # --- 2. ゴーリー集計タブ ---
    with tabs[1]:
        st.header("🧤 ゴーリー陣 総合分析")
        
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader("📊 セーブ率ランキング")
            g_stats = df.groupby('ゴーリー').agg(
                枠内被弾=('枠内', 'sum'),
                失点=('ゴール', 'sum'),
                セーブ=('セーブ', 'sum')
            ).reset_index()
            g_stats['セーブ率'] = (g_stats['セーブ'] / g_stats['枠内被弾']).apply(lambda x: f"{x:.1%}" if x > 0 else "0.0%")
            st.dataframe(g_stats.sort_values('セーブ', ascending=False), use_container_width=True, hide_index=True)

        with col_g2:
            st.subheader("🔥 チーム失点コース")
            # ゴーリー陣全体がどこを決められているか
            create_heatmap(df[df['結果'] == 'ゴール'], "ゴーリー陣全体の苦手傾向", "Oranges", "goalies_total_heat")

    # --- 3. 選手(シューター)別タブ ---
    for i, s_id in enumerate(shooter_ids):
        with tabs[i + 2]:
            st.header(f"🏃 選手詳細: {s_id}")
            s_df = df[df['背番号'].astype(str) == s_id]
            
            c1, c2 = st.columns([3, 2])
            with c1:
                st.subheader("📈 決定率の推移")
                trend = s_df.groupby('日時').agg(率=('ゴール', 'mean')).reset_index()
                fig = px.line(trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1])
                st.plotly_chart(fig, use_container_width=True, key=f"trend_s_{s_id}")
            with c2:
                st.subheader("🔥 得点コース")
                create_heatmap(s_df[s_df['結果'] == 'ゴール'], f"{s_id} の得点エリア", "Reds", f"heat_s_{s_id}")

    # --- 4. ゴーリー詳細タブ ---
    offset = 2 + len(shooter_ids)
    for i, g_name in enumerate(goalie_names):
        with tabs[i + offset]:
            st.header(f"🧤 ゴーリー詳細: {g_name}")
            g_df = df[df['ゴーリー'].astype(str) == g_name]
            
            gc1, gc2 = st.columns([3, 2])
            with gc1:
                st.subheader("📈 セーブ率の推移")
                g_trend = g_df[g_df['枠内']==1].groupby('日時').agg(率=('セーブ', 'mean')).reset_index()
                fig_g = px.line(g_trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1])
                st.plotly_chart(fig_g, use_container_width=True, key=f"trend_g_{g_name}")
            with gc2:
                st.subheader("⚠️ 失点コース")
                create_heatmap(g_df[g_df['結果'] == 'ゴール'], f"{g_name} の失点エリア", "Oranges", f"heat_g_{g_name}")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
