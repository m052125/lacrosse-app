import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="1on1 分析ダッシュボード", layout="wide")

st.title("🥍 1on1 戦略分析ダッシュボード")

# ==========================================
# 1. データの読み込み
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    # スプレッドシートのIDとGID
    SHEET_ID = "1hRkai8KYkb2nM8ZHA5h56JGst8pp9t8jUHu2jV-Nd2E"
    GID = "935578573"
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    try:
        df = pd.read_csv(csv_url)
        # Unityから送られてくる列名の正規化
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
    st.warning("データが読み込めません。スプレッドシートの共有設定を確認してください。")
    st.stop()

# ==========================================
# 2. サイドバー (分析モード選択)
# ==========================================
st.sidebar.header("🔍 分析メニュー")
mode = st.sidebar.radio("表示モード", ["🔴 AT個人分析", "🔵 DF個人分析", "🟡 ゴーリー分析", "📊 全データ"])

# ==========================================
# 3. 各モードの表示ロジック
# ==========================================

# ------------------------------------------
# 【AT個人分析】
# ------------------------------------------
if mode == "🔴 AT個人分析":
    at_list = sorted(list(df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("AT選手を選択", at_list)
    at_df = df[df['AT'] == selected_at]
    
    st.header(f"👤 AT: {selected_at} のパフォーマンス詳細")

    # サマリー指標
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        shot_total = len(at_df[at_df['終わり方'] == 'ショット'])
        st.metric("総ショット数", shot_total)
    with col_m2:
        goals = len(at_df[at_df['結果'] == 'ゴール'])
        st.metric("得点数", goals)
    with col_m3:
        success_rate = (goals / shot_total * 100) if shot_total > 0 else 0
        st.metric("ショット決定率", f"{success_rate:.1f}%")
    with col_m4:
        st.metric("対戦DF人数", at_df['DF'].nunique())

    # 傾向分析（円グラフ）
    st.divider()
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.write("**◆ 終わり方の傾向**")
        st.plotly_chart(px.pie(at_df, names='終わり方', hole=0.4), use_container_width=True)
    with col_c2:
        st.write("**◆ 抜き方の傾向**")
        dodge_df = at_df[at_df['抜き方'] != "NULL"]
        st.plotly_chart(px.pie(dodge_df, names='抜き方', hole=0.4), use_container_width=True)
    with col_c3:
        st.write("**◆ 打った手の傾向**")
        hand_df = at_df[at_df['利き手'] != "NULL"]
        st.plotly_chart(px.pie(hand_df, names='利き手', hole=0.4), use_container_width=True)

    # 起点・左右別ショット内訳表
    st.divider()
    st.subheader("📊 ショット内訳マトリックス")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write("**◆ 起点別ショット内訳**")
        pivot_pos = at_df[at_df['終わり方'] == 'ショット'].groupby('起点')['結果'].value_counts().unstack(fill_value=0)
        st.table(pivot_pos)
    with col_t2:
        st.write("**◆ 左右ショット決定率**")
        pivot_hand = at_df[at_df['終わり方'] == 'ショット'].groupby('利き手')['結果'].value_counts().unstack(fill_value=0)
        if not pivot_hand.empty and 'ゴール' in pivot_hand.columns:
            pivot_hand['決定率(%)'] = (pivot_hand['ゴール'] / pivot_hand.sum(axis=1) * 100).round(1)
        st.table(pivot_hand)

    # 3x3 コース別詳細
    st.divider()
    st.subheader("🎯 ショットコース詳細 (3×3)")
    grid_cols = st.columns(3)
    for i in range(1, 10):
        with grid_cols[(i-1)%3]:
            c_data = at_df[at_df['コース'].astype(str) == str(i)]
            g, s, w = (c_data['結果'] == 'ゴール').sum(), (c_data['結果'] == 'セーブ').sum(), (c_data['結果'] == '枠外').sum()
            total_c = len(c_data)
            rate_c = (g / total_c * 100) if total_c > 0 else 0
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:10px; border-radius:5px; text-align:center; background:#fff;">
                <b>コース {i}</b><br>
                <span style="color:red; font-size:1.2em;">○: {g}</span> | セ: {s} | 外: {w}<br>
                <small>決定率: {rate_c:.1f}%</small>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------
# 【DF個人分析】
# ------------------------------------------
elif mode == "🔵 DF個人分析":
    df_list = sorted(list(df['DF'].dropna().unique()))
    selected_df = st.sidebar.selectbox("DF選手を選択", df_list)
    target_df = df[df['DF'] == selected_df].copy()
    
    st.header(f"🛡️ DF: {selected_df} のディフェンス分析")

    # サマリー
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.metric("総守備回数", len(target_df))
    with col_d2:
        # ショット阻止率 = (ショットを打たれた総数 - ゴール数) / ショットを打たれた総数
        shot_received = len(target_df[target_df['終わり方'] == 'ショット'])
        goals_allowed = len(target_df[target_df['結果'] == 'ゴール'])
        stop_rate = ((shot_received - goals_allowed) / shot_received * 100) if shot_received > 0 else 0
        st.metric("ショット阻止率", f"{stop_rate:.1f}%")
    with col_d3:
        # 完封率 = 終わり方がショット以外だった割合
        shutout_rate = (len(target_df[target_df['終わり方'] != 'ショット']) / len(target_df) * 100) if len(target_df) > 0 else 0
        st.metric("ショット未許容率", f"{shutout_rate:.1f}%")

    # 起点×抜き方マトリックス
    st.divider()
    st.subheader("📋 抜かれた起点・方向の分析")
    
    # データの加工
    target_df['抜かれた'] = target_df['終わり方'].apply(lambda x: 1 if x == 'ショット' else 0)
    target_df['抜かれなかった'] = target_df['終わり方'].apply(lambda x: 1 if x != 'ショット' else 0)
    
    # 起点別の集計
    df_pivot = pd.DataFrame(index=target_df['起点'].unique())
    for dodge in ['イン抜き', 'アウト抜き']:
        dodge_data = target_df[target_df['抜き方'] == dodge].groupby('起点')['抜かれた'].sum()
        df_pivot[f"{dodge}で抜かれた"] = dodge_data
    
    df_pivot = df_pivot.fillna(0).astype(int)
    df_pivot['抜かれた合計'] = df_pivot.sum(axis=1)
    df_pivot['抜かれなかった'] = target_df.groupby('起点')['抜かれなかった'].sum()
    
    st.table(df_pivot)

    # グラフ分析
    col_dg1, col_dg2 = st.columns(2)
    with col_dg1:
        st.write("**◆ 対戦AT別の被ショット率**")
        at_stats = target_df.groupby('AT').apply(lambda x: (x['終わり方'] == 'ショット').sum() / len(x) * 100).reset_index(name='被ショット率')
        st.plotly_chart(px.bar(at_stats, x='AT', y='被ショット率', color='被ショット率', color_continuous_scale='Reds'), use_container_width=True)
    with col_dg2:
        st.write("**◆ ショットを打たれた場所(起点)**")
        shot_origins = target_df[target_df['終わり方'] == 'ショット']
        st.plotly_chart(px.pie(shot_origins, names='起点', hole=0.4), use_container_width=True)

# ------------------------------------------
# 【ゴーリー分析】
# ------------------------------------------
elif mode == "🟡 ゴーリー分析":
    g_list = sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)
    g_df = df[df['ゴーリー'] == selected_g]
    
    st.header(f"🧤 Goalie: {selected_g} のセーブ分析")
    
    # 3x3 セーブ率ヒートマップ
    shot_df = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])]
    if not shot_df.empty:
        mapping = {'1':(0,0), '2':(0,1), '3':(0,2), '4':(1,0), '5':(1,1), '6':(1,2), '7':(2,0), '8':(2,1), '9':(2,2)}
        grid = np.zeros((3, 3))
        for c_num in mapping.keys():
            c_shots = shot_df[shot_df['コース'].astype(str) == c_num]
            if not c_shots.empty:
                r, c = mapping[c_num]
                grid[r, c] = round((c_shots['結果'] == 'セーブ').sum() / len(c_shots) * 100, 1)
        
        fig_g = px.imshow(grid, x=['左','中','右'], y=['上','中','下'], text_auto=True, color_continuous_scale='Blues', title="コース別セーブ率(%)")
        st.plotly_chart(fig_g)
    else:
        st.info("集計対象のショットがありません。")

# ------------------------------------------
# 【全データ】
# ------------------------------------------
else:
    st.header("📊 蓄積データ一覧")
    st.dataframe(df.sort_values('タイムスタンプ', ascending=False))
