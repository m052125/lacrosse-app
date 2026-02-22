import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="ラクロス総合分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 総合分析ダッシュボード")

try:
    # データの読み込み
    df = pd.read_csv('FreeShootData.csv')
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    
    # 基本判定フラグの作成
    df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
    df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
    # 枠内シュート（ゴールかセーブされたもの）
    df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)

    # 選手（シューター）とゴーリーのリスト取得
    shooter_ids = sorted(df['背番号'].unique().astype(str))
    goalie_names = sorted(df['ゴーリー'].unique().astype(str))
    
    # === メインタブ構成 ===
    # 「全体」「ゴーリー集計」の後に、各選手のタブを並べる
    tab_list = ["チーム全体", "🧤 ゴーリー集計"] + [f"🏃 {s}" for s in shooter_ids] + [f"🧤 {g}" for g in goalie_names]
    tabs = st.tabs(tab_list)

    # --- 1. チーム全体タブ ---
    with tabs[0]:
        st.header("🏢 チーム全体の成績")
        col1, col2, col3 = st.columns(3)
        total_s = len(df)
        total_g = df['ゴール'].sum()
        col1.metric("総シュート数", f"{total_s}本")
        col2.metric("総ゴール数", f"{total_g}本")
        col3.metric("平均決定率", f"{total_g/total_s:.1%}" if total_s > 0 else "0%")
        
        st.subheader("📋 全データ履歴")
        st.dataframe(df.sort_values('日時', ascending=False), use_container_width=True, height=400)

    # --- 2. ゴーリー集計タブ ---
    with tabs[1]:
        st.header("🧤 ゴーリー別 セーブ率ランキング")
        g_stats = df.groupby('ゴーリー').agg(
            枠内被弾=('枠内', 'sum'),
            失点=('ゴール', 'sum'),
            セーブ=('セーブ', 'sum'),
            総被シュート=('結果', 'count')
        ).reset_index()
        
        # セーブ率 = セーブ数 / 枠内シュート数
        g_stats['セーブ率'] = (g_stats['セーブ'] / g_stats['枠内被弾'])
        g_stats_display = g_stats.copy()
        g_stats_display['セーブ率'] = g_stats_display['セーブ率'].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "0.0%")
        
        st.dataframe(g_stats_display.sort_values('セーブ', ascending=False), use_container_width=True, hide_index=True)

    # --- 3. 選手(シューター)別タブ ---
    for i, s_id in enumerate(shooter_ids):
        with tabs[i + 2]:
            st.header(f"🏃 選手詳細: {s_id}")
            s_df = df[df['背番号'].astype(str) == s_id]
            
            c1, c2, c3 = st.columns(3)
            s_total = len(s_df)
            s_goal = s_df['ゴール'].sum()
            c1.metric("シュート数", f"{s_total}本")
            c2.metric("ゴール数", f"{s_goal}本")
            c3.metric("決定率", f"{s_goal/s_total:.1%}" if s_total > 0 else "0%")
            
            # 推移とヒートマップ
            g_col1, g_col2 = st.columns([3, 2])
            with g_col1:
                st.subheader("📈 決定率の推移")
                trend = s_df.groupby('日時').agg(率=('ゴール', 'mean')).reset_index()
                fig = px.line(trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1])
                st.plotly_chart(fig, use_container_width=True, key=f"trend_s_{s_id}")
            
            with g_col2:
                st.subheader("🔥 得点コース")
                goals = s_df[s_df['結果'] == 'ゴール']
                z = np.zeros((3, 3))
                counts = goals['コース'].value_counts()
                for r, names in enumerate([['1','2','3'],['4','5','6'],['7','8','9']]):
                    for c, n in enumerate(names):
                        z[r][c] = counts.get(int(n), 0) + counts.get(str(n), 0)
                fig_h = px.imshow(z, x=['左','中','右'], y=['上','中','下'], text_auto=True, color_continuous_scale="Reds")
                st.plotly_chart(fig_h, use_container_width=False, width=350, key=f"heat_s_{s_id}")

    # --- 4. ゴーリー詳細タブ ---
    offset = 2 + len(shooter_ids)
    for i, g_name in enumerate(goalie_names):
        with tabs[i + offset]:
            st.header(f"🧤 ゴーリー詳細: {g_name}")
            g_df = df[df['ゴーリー'].astype(str) == g_name]
            
            c1, c2, c3 = st.columns(3)
            g_shots = g_df['枠内'].sum()
            g_saves = g_df['セーブ'].sum()
            c1.metric("枠内被弾数", f"{g_shots}本")
            c2.metric("セーブ数", f"{g_saves}本")
            c3.metric("セーブ率", f"{g_saves/g_shots:.1%}" if g_shots > 0 else "0%")
            
            g_col1, g_col2 = st.columns([3, 2])
            with g_col1:
                st.subheader("📈 セーブ率の推移")
                g_trend = g_df[g_df['枠内']==1].groupby('日時').agg(率=('セーブ', 'mean')).reset_index()
                fig_g = px.line(g_trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1])
                st.plotly_chart(fig_g, use_container_width=True, key=f"trend_g_{g_name}")
            
            with g_col2:
                st.subheader("⚠️ 失点コース（弱点）")
                losses = g_df[g_df['結果'] == 'ゴール']
                z_g = np.zeros((3, 3))
                counts_g = losses['コース'].value_counts()
                for r, names in enumerate([['1','2','3'],['4','5','6'],['7','8','9']]):
                    for c, n in enumerate(names):
                        z_g[r][c] = counts_g.get(int(n), 0) + counts_g.get(str(n), 0)
                fig_hg = px.imshow(z_g, x=['左','中','右'], y=['上','中','下'], text_auto=True, color_continuous_scale="Oranges")
                st.plotly_chart(fig_hg, use_container_width=False, width=350, key=f"heat_g_{g_name}")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
