import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="1on1 分析ダッシュボード", layout="wide")

st.title("🥍 1on1 データ分析ダッシュボード (AT強化版)")

# ==========================================
# 1. データの読み込み
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    SHEET_ID = "1hRkai8KYkb2nM8ZHA5h56JGst8pp9t8jUHu2jV-Nd2E"
    GID = "935578573"
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    try:
        df = pd.read_csv(csv_url)
        # 列名の名寄せ
        df = df.rename(columns={
            'ショットを打った手': '利き手',
            'ショットコース': 'コース',
            'ショット結果': '結果'
        })
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("データがまだありません。")
    st.stop()

# ==========================================
# 2. サイドバー (フィルター)
# ==========================================
st.sidebar.header("🔍 分析対象の絞り込み")
at_list = sorted(list(df['AT'].dropna().unique()))
selected_at = st.sidebar.selectbox("分析するATを選択", at_list)

# 基本フィルター（選択したATのデータのみ）
at_df = df[df['AT'] == selected_at]

# ==========================================
# 3. メイン表示 (AT分析タブを最優先)
# ==========================================
tab1, tab2, tab3 = st.tabs(["🔴 AT詳細分析", "🔵 DF分析", "🟡 ゴーリー分析"])

with tab1:
    st.header(f"👤 AT選手: {selected_at} の分析結果")
    
    # --- サマリー情報 ---
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("対戦したDF数", at_df['DF'].nunique())
    with col_info2:
        st.metric("対戦したゴーリー数", at_df['ゴーリー'].nunique())
    with col_info3:
        # ショット率計算 (ゴール数 / 終わり方がショットの総数)
        shot_total = len(at_df[at_df['終わり方'] == 'ショット'])
        goals = len(at_df[at_df['結果'] == 'ゴール'])
        shot_rate = (goals / shot_total * 100) if shot_total > 0 else 0
        st.metric("トータルショット率", f"{shot_rate:.1f}%")

    # --- グラフセクション1 (傾向) ---
    st.divider()
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.subheader("📊 終わり方の傾向")
        fig_end = px.pie(at_df, names='終わり方', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_end, use_container_width=True)
        
    with col_g2:
        st.subheader("🔄 抜き方の傾向")
        dodge_df = at_df[at_df['抜き方'] != "NULL"]
        fig_dodge = px.pie(dodge_df, names='抜き方', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_dodge, use_container_width=True)

    with col_g3:
        st.subheader("✋ ショットを打った手")
        hand_df = at_df[at_df['利き手'] != "NULL"]
        fig_hand = px.pie(hand_df, names='利き手', hole=0.4, color_discrete_sequence=['#EF553B', '#636EFA'])
        st.plotly_chart(fig_hand, use_container_width=True)

    # --- 表セクション (image_901cef.png の再現) ---
    st.divider()
    st.subheader("📈 詳細データ集計表")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        # 起点別ショット内訳
        st.write("**◆ 起点別ショット内訳**")
        pos_stats = at_df[at_df['終わり方'] == 'ショット'].groupby('起点')['結果'].value_counts().unstack(fill_value=0)
        # 必要な列を揃える
        for col in ['ゴール', 'セーブ', '枠外']:
            if col not in pos_stats.columns: pos_stats[col] = 0
        st.table(pos_stats[['ゴール', 'セーブ', '枠外']])

        # 左右ショット内訳
        st.write("**◆ 左右ショット内訳**")
        hand_stats = at_df[at_df['終わり方'] == 'ショット'].groupby('利き手')['結果'].value_counts().unstack(fill_value=0)
        for col in ['ゴール', 'セーブ', '枠外']:
            if col not in hand_stats.columns: hand_stats[col] = 0
        hand_stats['ショット率'] = (hand_stats['ゴール'] / (hand_stats['ゴール'] + hand_stats['セーブ'] + hand_stats['枠外']) * 100).round(1).astype(str) + '%'
        st.table(hand_stats)

    with col_t2:
        # 抜けたかどうか (起点別・抜き方別)
        st.write("**◆ 抜けたかどうか (起点×抜き方)**")
        # 「終わり方」がGBやダウンボールでないものを「抜けた」と仮定、またはデータの「抜き方」をカウント
        dodge_success = at_df.groupby(['起点', '抜き方']).size().unstack(fill_value=0)
        st.table(dodge_success)

        # 対戦相手(DF)ごとのショット率
        st.write("**◆ 対戦相手(DF)ごとのショット率**")
        df_shot_df = at_df[at_df['終わり方'] == 'ショット']
        if not df_shot_df.empty:
            df_stats = df_shot_df.groupby('DF')['結果'].apply(lambda x: (x == 'ゴール').sum() / len(x) * 100).reset_index()
            df_stats.columns = ['DF名', 'ショット率(%)']
            fig_df_rate = px.bar(df_stats, x='DF名', y='ショット率(%)', color='ショット率(%)', color_continuous_scale='OrRd')
            st.plotly_chart(fig_df_rate, use_container_width=True)

    # --- ショットコース 3x3 グリッド ---
    st.divider()
    st.subheader("🎯 ショットコース詳細 (3×3)")
    
    # コース配置図の再現
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2),
        '4': (1, 0), '5': (1, 1), '6': (1, 2),
        '7': (2, 0), '8': (2, 1), '9': (2, 2)
    }
    
    # 3x3のグリッド内に、○(ゴール), 枠外, セーブを表示する
    grid_cols = st.columns(3)
    for i in range(1, 10):
        with grid_cols[(i-1)%3]:
            c_data = at_df[at_df['コース'].astype(str) == str(i)]
            g = (c_data['結果'] == 'ゴール').sum()
            s = (c_data['結果'] == 'セーブ').sum()
            w = (c_data['結果'] == '枠外').sum()
            rate = (g / len(c_data) * 100) if len(c_data) > 0 else 0
            
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:10px; border-radius:5px; text-align:center;">
                <b>コース {i}</b><br>
                <span style="color:red;">○: {g}</span> | セーブ: {s} | 枠外: {w}<br>
                <small>ショット率: {rate:.1f}%</small>
            </div>
            """, unsafe_allow_label=True)

# --- 他のタブは既存機能を維持 ---
with tab2:
    st.header("🔵 DF分析 (全体)")
    # (既存のDF分析コードをここに配置)
    st.dataframe(df.groupby('DF').size().reset_index(name='対戦数'))

with tab3:
    st.header("🟡 ゴーリー分析 (全体)")
    # (既存のゴーリー分析コードをここに配置)
    st.dataframe(df.groupby('ゴーリー').size().reset_index(name='対戦数'))
