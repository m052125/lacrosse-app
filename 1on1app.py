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
    SHEET_ID = "1hRkai8KYkb2nM8ZHA5h56JGst8pp9t8jUHu2jV-Nd2E"
    GID = "935578573"
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    try:
        df = pd.read_csv(csv_url)
        # 列名の正規化
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
    st.warning("データがまだ読み込めません。")
    st.stop()

# ==========================================
# 2. 共通ヒートマップ関数
# ==========================================
def create_3x3_heatmap(data_df, mode="course", title=""):
    """
    mode="course": 1-9の数字をマッピング
    mode="origin": 起点名(左上, 右裏等)をマッピング
    """
    grid = np.zeros((3, 3))
    
    if mode == "course":
        mapping = {
            '1': (0, 0), '2': (0, 1), '3': (0, 2),
            '4': (1, 0), '5': (1, 1), '6': (1, 2),
            '7': (2, 0), '8': (2, 1), '9': (2, 2)
        }
        col_target = 'コース'
    else:
        # 起点の名前をフィールド上の位置にマッピング
        mapping = {
            '左上': (0, 0), 'センター': (0, 1), '右上': (0, 2),
            '左横': (1, 0), '右横': (1, 2),
            '左裏': (2, 0), '右裏': (2, 2)
        }
        col_target = '起点'

    # 集計処理
    counts = data_df[col_target].dropna().astype(str).value_counts()
    for val, count in counts.items():
        if val in mapping:
            r, c = mapping[val]
            grid[r, c] = count

    fig = px.imshow(
        grid,
        labels=dict(x="左右", y="上下", color="回数"),
        x=['左', '中', '右'],
        y=['上', '中', '下'] if mode == "course" else ['上', '横', '裏'],
        text_auto=True,
        color_continuous_scale='OrRd',
        title=title
    )
    fig.update_layout(width=400, height=400, coloraxis_showscale=False)
    return fig

# ==========================================
# 3. サイドバー (モード切替)
# ==========================================
st.sidebar.header("🔍 分析メニュー")
mode = st.sidebar.radio("表示モード", ["🟡 ゴーリー詳細分析", "🔴 AT個人分析", "🔵 DF個人分析", "📊 全データ"])

# ==========================================
# 4. 各モードの表示
# ==========================================

# --- 【🟡 ゴーリー詳細分析】 ---
if mode == "🟡 ゴーリー詳細分析":
    g_list = sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)
    g_df = df[df['ゴーリー'] == selected_g].copy()
    
    st.header(f"🧤 ゴーリー: {selected_g} の詳細分析")

    # サマリー
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

    # 1. シューター(AT)ごとのデータ
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("👤 シューター(AT)別の対戦数")
        at_counts = g_df['AT'].value_counts().reset_index()
        at_counts.columns = ['シューター名', '対戦回数']
        st.plotly_chart(px.bar(at_counts, x='シューター名', y='対戦回数', color='対戦回数'), use_container_width=True)

    with col_g2:
        st.subheader("🎯 抜き方別のセーブ率")
        # 枠内ショットに限定して計算
        dodge_save = shot_data.groupby('抜き方')['結果'].apply(
            lambda x: (x == 'セーブ').sum() / len(x) * 100
        ).reset_index(name='セーブ率(%)')
        st.plotly_chart(px.bar(dodge_save, x='抜き方', y='セーブ率(%)', range_y=[0, 100], color='抜き方'), use_container_width=True)

    st.divider()

    # 2. ヒートマップセクション
    st.subheader("📊 ポジション別・コース別分析")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        # ショットを打たれた場所 (起点)
        st.plotly_chart(create_3x3_heatmap(g_df[g_df['終わり方']=='ショット'], mode="origin", title="ショットを打たれた場所 (起点)"), use_container_width=True)
    with col_h2:
        # セーブしたコース
        save_df = g_df[g_df['結果'] == 'セーブ']
        st.plotly_chart(create_3x3_heatmap(save_df, mode="course", title="セーブしたコース分布"), use_container_width=True)

# --- 【🔴 AT個人分析】 ---
elif mode == "🔴 AT個人分析":
    at_list = sorted(list(df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("AT選手を選択", at_list)
    at_df = df[df['AT'] == selected_at]
    st.header(f"👤 AT: {selected_at} の分析")
    # (前回作成したAT分析コードと同様)
    st.plotly_chart(create_3x3_heatmap(at_df[at_df['結果']=='ゴール'], mode="course", title="ゴール決定コース"), use_container_width=True)
    st.table(at_df.groupby('DF')['結果'].value_counts().unstack(fill_value=0))

# --- 【🔵 DF個人分析】 ---
elif mode == "🔵 DF個人分析":
    df_list = sorted(list(df['DF'].dropna().unique()))
    selected_df = st.sidebar.selectbox("DF選手を選択", df_list)
    st.header(f"🛡️ DF: {selected_df} の分析")
    # (起点別の抜かれ傾向を表示)
    df_df = df[df['DF'] == selected_df]
    st.plotly_chart(create_3x3_heatmap(df_df[df_df['終わり方']=='ショット'], mode="origin", title="抜かれた起点"), use_container_width=True)

else:
    st.header("📊 データ一覧")
    st.dataframe(df)
