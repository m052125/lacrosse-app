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
    # ユーザー提供のIDとGID
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
    st.warning("データがまだ読み込めません。Unityアプリからデータを送信してください。")
    st.stop()

# ==========================================
# 2. 共通ヒートマップ関数 (3×3)
# ==========================================
def create_3x3_heatmap(data_df, mode="course", title=""):
    """
    mode="course": ゴールの1-9番
    mode="origin": フィールドの起点名
    """
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
        # 起点名をフィールド上の3x3位置にマッピング
        mapping = {
            '左上': (0, 0), 'センター': (0, 1), '右上': (0, 2),
            '左横': (1, 0), '右横': (1, 2),
            '左裏': (2, 0), '右裏': (2, 2)
        }
        col_target = '起点'
        y_labels = ['上', '横', '裏']

    # カウント集計
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
mode = st.sidebar.radio("表示モード", ["🟡 ゴーリー詳細分析", "🔴 AT個人分析", "🔵 DF個人分析", "📊 全データ"])

# ==========================================
# 4. 各モードの表示ロジック
# ==========================================

# --- 【🟡 ゴーリー詳細分析】 ---
if mode == "🟡 ゴーリー詳細分析":
    g_list = sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)
    g_df = df[df['ゴーリー'] == selected_g].copy()
    
    st.header(f"🧤 ゴーリー: {selected_g} の分析")

    # サマリーメトリクス
    shot_df = g_df[g_df['終わり方'] == 'ショット']
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("被ショット数", len(shot_df))
    with col2:
        save_count = (g_df['結果'] == 'セーブ').sum()
        st.metric("セーブ数", save_count)
    with col3:
        valid_shots = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])]
        save_rate = (save_count / len(valid_shots) * 100) if not valid_shots.empty else 0
        st.metric("セーブ率", f"{save_rate:.1f}%")

    st.divider()

    # シューターと抜き方の相関分析
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("👤 シューター(AT)別 セーブ傾向")
        at_stats = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])].groupby('AT')['結果'].apply(
            lambda x: (x == 'セーブ').sum() / len(x) * 100
        ).reset_index(name='セーブ率(%)')
        st.plotly_chart(px.bar(at_stats, x='AT', y='セーブ率(%)', color='セーブ率(%)', color_continuous_scale='Blues'), use_container_width=True)

    with col_g2:
        st.subheader("🔄 抜き方別のセーブ成功率")
        dodge_save = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])].groupby('抜き方')['結果'].apply(
            lambda x: (x == 'セーブ').sum() / len(x) * 100
        ).reset_index(name='セーブ率(%)')
        st.plotly_chart(px.bar(dodge_save, x='抜き方', y='セーブ率(%)', range_y=[0, 100], color='抜き方'), use_container_width=True)

    st.divider()
    
    # ヒートマップ (起点とコース)
    st.subheader("📍 ショット位置とセーブコースの視覚化")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.plotly_chart(create_3x3_heatmap(shot_df, mode="origin", title="ショットを打たれた場所 (起点)"), use_container_width=True)
    with col_h2:
        st.plotly_chart(create_3x3_heatmap(g_df[g_df['結果']=='セーブ'], mode="course", title="セーブしたコース分布"), use_container_width=True)

# --- 【🔴 AT個人分析】 ---
elif mode == "🔴 AT個人分析":
    at_list = sorted(list(df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("AT選手を選択", at_list)
    at_df = df[df['AT'] == selected_at]
    
    st.header(f"👤 AT: {selected_at} のパフォーマンス")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        st.write("**◆ 終わり方の傾向**")
        st.plotly_chart(px.pie(at_df, names='終わり方', hole=0.4), use_container_width=True)
    with col_a2:
        st.write("**◆ 抜き方の傾向**")
        st.plotly_chart(px.pie(at_df[at_df['抜き方']!="NULL"], names='抜き方', hole=0.4), use_container_width=True)
    with col_a3:
        st.write("**◆ 打った手の傾向**")
        st.plotly_chart(px.pie(at_df[at_df['利き手']!="NULL"], names='利き手', hole=0.4), use_container_width=True)

    st.divider()
    
    # 集計マトリックス (image_901cef.png 再現)
    st.subheader("📊 起点・左右別ショット内訳")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        pivot_pos = at_df[at_df['終わり方'] == 'ショット'].groupby('起点')['結果'].value_counts().unstack(fill_value=0)
        st.table(pivot_pos)
    with col_t2:
        pivot_hand = at_df[at_df['終わり方'] == 'ショット'].groupby('利き手')['結果'].value_counts().unstack(fill_value=0)
        st.table(pivot_hand)

    st.subheader("🎯 ゴール決定コース (3×3)")
    st.plotly_chart(create_3x3_heatmap(at_df[at_df['結果']=='ゴール'], mode="course", title="得点エリア分布"), use_container_width=True)

# --- 【🔵 DF個人分析】 ---
elif mode == "🔵 DF個人分析":
    df_list = sorted(list(df['DF'].dropna().unique()))
    selected_df = st.sidebar.selectbox("DF選手を選択", df_list)
    df_df = df[df['DF'] == selected_df].copy()
    
    st.header(f"🛡️ DF: {selected_df} の分析")

    # 起点×抜き方マトリックス
    st.subheader("📋 抜かれた起点と方向の分析")
    df_df['抜かれた'] = df_df['終わり方'].apply(lambda x: 1 if x == 'ショット' else 0)
    df_df['抜かれなかった'] = df_df['終わり方'].apply(lambda x: 1 if x != 'ショット' else 0)
    
    pivot_df = pd.DataFrame(index=df_df['起点'].unique())
    for d in ['イン抜き', 'アウト抜き']:
        pivot_df[f"{d}で抜かれた"] = df_df[df_df['抜き方'] == d].groupby('起点')['抜かれた'].sum()
    
    pivot_df = pivot_df.fillna(0).astype(int)
    pivot_df['抜かれた合計'] = pivot_df.sum(axis=1)
    pivot_df['抜かれなかった'] = df_df.groupby('起点')['抜かれなかった'].sum()
    st.table(pivot_df)

    st.plotly_chart(create_3x3_heatmap(df_df[df_df['終わり方']=='ショット'], mode="origin", title="ショットを許した起点マップ"), use_container_width=True)

else:
    st.header("📊 全データ一覧")
    st.dataframe(df.sort_values('タイムスタンプ', ascending=False))
