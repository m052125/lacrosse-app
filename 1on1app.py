import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="1on1 総合分析ダッシュボード", layout="wide")

st.title("🥍 1on1 総合戦略分析ダッシュボード")

# ==========================================
# 1. データの読み込み (Googleスプレッドシート)
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    SHEET_ID = "1hRkai8KYkb2nM8ZHA5h56JGst8pp9t8jUHu2jV-Nd2E"
    GID = "935578573"
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    try:
        df = pd.read_csv(csv_url)
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
    st.warning("データがまだ読み込めません。Unityアプリからデータを送信してください。")
    st.stop()

# ==========================================
# 2. 共通ヒートマップ関数 (3×3)
# ==========================================
def create_3x3_heatmap(data_df, mode="course", title=""):
    grid = np.zeros((3, 3))
    
    if mode == "course":
        mapping = {
            '1': (0, 0), '2': (0, 1), '3': (0, 2),
            '4': (1, 0), '5': (1, 1), '6': (1, 2),
            '7': (2, 0), '8': (2, 1), '9': (2, 2)
        }
        col_target = 'コース'
        y_labels = ['上', '中', '下']
    else:
        mapping = {
            '左上': (0, 0), 'センター': (0, 1), '右上': (0, 2),
            '左横': (1, 0), '右横': (1, 2),
            '左裏': (2, 0), '右裏': (2, 2)
        }
        col_target = '起点'
        y_labels = ['上', '横', '裏']

    counts = data_df[col_target].dropna().astype(str).value_counts()
    for val, count in counts.items():
        if val in mapping:
            r, c = mapping[val]
            grid[r, c] = count

    fig = px.imshow(
        grid,
        labels=dict(x="左右", y="位置", color="回数"),
        x=['左', '中', '右'],
        y=y_labels,
        text_auto=True,
        color_continuous_scale='OrRd',
        title=title
    )
    fig.update_layout(width=450, height=450, coloraxis_showscale=False)
    return fig

# ==========================================
# 3. サイドバー (分析モード切替)
# ==========================================
st.sidebar.header("🔍 メインメニュー")
mode = st.sidebar.radio("表示モード", ["🔴 AT個人分析", "🔵 DF個人分析", "🟡 ゴーリー個人分析", "📊 全データ"])

# ==========================================
# 4. 各モードの表示ロジック
# ==========================================

# --- 【🔴 AT個人分析】 ---
if mode == "🔴 AT個人分析":
    at_list = sorted(list(df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("分析するATを選択", at_list)
    at_df = df[df['AT'] == selected_at]
    
    st.header(f"👤 AT選手: {selected_at} の分析結果")
    
    # --- サマリー情報 ---
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("対戦したDF数", at_df['DF'].nunique())
    with col_info2:
        st.metric("対戦したゴーリー数", at_df['ゴーリー'].nunique())
    with col_info3:
        shot_total = len(at_df[at_df['終わり方'] == 'ショット'])
        goals = len(at_df[at_df['結果'] == 'ゴール'])
        shot_rate = (goals / shot_total * 100) if shot_total > 0 else 0
        st.metric("トータルショット率", f"{shot_rate:.1f}%")

    # --- グラフセクション ---
    st.divider()
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.subheader("📊 終わり方の傾向")
        st.plotly_chart(px.pie(at_df, names='終わり方', hole=0.4), use_container_width=True)
    with col_g2:
        st.subheader("🔄 抜き方の傾向")
        dodge_df = at_df[at_df['抜き方'] != "NULL"]
        st.plotly_chart(px.pie(dodge_df, names='抜き方', hole=0.4), use_container_width=True)
    with col_g3:
        st.subheader("✋ ショットを打った手")
        hand_df = at_df[at_df['利き手'] != "NULL"]
        st.plotly_chart(px.pie(hand_df, names='利き手', hole=0.4), use_container_width=True)

    # --- 表セクション ---
    st.divider()
    st.subheader("📈 詳細データ集計表")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write("**◆ 起点別ショット内訳**")
        pos_stats = at_df[at_df['終わり方'] == 'ショット'].groupby('起点')['結果'].value_counts().unstack(fill_value=0)
        for col in ['ゴール', 'セーブ', '枠外']:
            if col not in pos_stats.columns: pos_stats[col] = 0
        st.table(pos_stats[['ゴール', 'セーブ', '枠外']])
    with col_t2:
        st.write("**◆ 抜けたかどうか (起点×抜き方)**")
        dodge_success = at_df.groupby(['起点', '抜き方']).size().unstack(fill_value=0)
        st.table(dodge_success)

    st.subheader("🎯 ショットコース詳細 (3×3)")
    st.plotly_chart(create_3x3_heatmap(at_df[at_df['結果']=='ゴール'], mode="course", title="ゴール決定コース"), use_container_width=True)

# --- 【🔵 DF個人分析】 ---
elif mode == "🔵 DF個人分析":
    df_list = sorted(list(df['DF'].dropna().unique()))
    selected_df = st.sidebar.selectbox("分析するDFを選択", df_list)
    target_df = df[df['DF'] == selected_df].copy()
    
    st.header(f"🛡️ DF選手: {selected_df} の分析結果")

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("総対戦数", len(target_df))
    with col_info2:
        goals = len(target_df[target_df['結果'] == 'ゴール'])
        stop_rate = ((len(target_df) - goals) / len(target_df) * 100) if len(target_df) > 0 else 0
        st.metric("トータル阻止率", f"{stop_rate:.1f}%")
    with col_info3:
        st.metric("対戦したAT数", target_df['AT'].nunique())

    st.divider()
    st.subheader("📊 抜かれたかどうか (起点×抜き方)")
    target_df['抜かれた'] = target_df['終わり方'].apply(lambda x: 1 if x == 'ショット' else 0)
    target_df['抜かれなかった'] = target_df['終わり方'].apply(lambda x: 1 if x != 'ショット' else 0)
    
    df_pivot = pd.DataFrame(index=target_df['起点'].unique())
    for d in ['イン抜き', 'アウト抜き']:
        df_pivot[f"{d}で抜かれた"] = target_df[target_df['抜き方'] == d].groupby('起点')['抜かれた'].sum()
    df_pivot = df_pivot.fillna(0).astype(int)
    df_pivot['抜かれた合計'] = df_pivot.sum(axis=1)
    df_pivot['抜かれなかった'] = target_df.groupby('起点')['抜かれなかった'].sum()
    st.table(df_pivot)

    st.plotly_chart(create_3x3_heatmap(target_df[target_df['抜かれた']==1], mode="origin", title="ショットを許した起点マップ"), use_container_width=True)

# --- 【🟡 ゴーリー詳細分析】 ---
elif mode == "🟡 ゴーリー個人分析":
    g_list = sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)
    g_df = df[df['ゴーリー'] == selected_g].copy()
    
    st.header(f"🧤 ゴーリー: {selected_g} の詳細分析")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総被ショット数", len(g_df[g_df['終わり方'] == 'ショット']))
    with col2:
        save_total = (g_df['結果'] == 'セーブ').sum()
        st.metric("総セーブ数", save_total)
    with col3:
        shot_data = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])]
        save_rate = (save_total / len(shot_data) * 100) if not shot_data.empty else 0
        st.metric("トータルセーブ率", f"{save_rate:.1f}%")

    st.divider()
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("👤 シューター(AT)別の対戦数")
        st.plotly_chart(px.bar(g_df['AT'].value_counts().reset_index(), x='AT', y='count'), use_container_width=True)
    with col_g2:
        st.subheader("🎯 抜き方別のセーブ率")
        dodge_save = shot_data.groupby('抜き方')['結果'].apply(lambda x: (x == 'セーブ').sum() / len(x) * 100).reset_index(name='セーブ率(%)')
        st.plotly_chart(px.bar(dodge_save, x='抜き方', y='セーブ率(%)', range_y=[0, 100]), use_container_width=True)

    st.divider()
    st.subheader("📊 ポジション別・コース別分析")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.plotly_chart(create_3x3_heatmap(g_df[g_df['終わり方']=='ショット'], mode="origin", title="ショット起点ヒートマップ"), use_container_width=True)
    with col_h2:
        st.plotly_chart(create_3x3_heatmap(g_df[g_df['結果'] == 'セーブ'], mode="course", title="セーブコース分布"), use_container_width=True)

# --- 【📊 全データ】 ---
else:
    st.header("📊 全データ一覧")
    st.dataframe(df.sort_values('タイムスタンプ', ascending=False))
