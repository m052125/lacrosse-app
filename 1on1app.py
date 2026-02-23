import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="1on1 分析ダッシュボード", layout="wide")

st.title("🥍 1on1 データ分析ダッシュボード")

# ==========================================
# 1. データの読み込み
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    # スプレッドシートIDとGID
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
    st.warning("データがまだありません。スプレッドシートの共有設定を確認してください。")
    st.stop()

# ==========================================
# 2. ヒートマップ描画用関数
# ==========================================
def create_shot_heatmap(data_df, title_label, mode="count"):
    """
    3x3のヒートマップを作成する関数
    mode="count": ゴール数などを集計
    mode="rate": セーブ率などを計算
    """
    # 1〜9のコースを3x3の座標にマッピング
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2),
        '4': (1, 0), '5': (1, 1), '6': (1, 2),
        '7': (2, 0), '8': (2, 1), '9': (2, 2)
    }
    
    grid = np.zeros((3, 3))
    
    if mode == "count":
        # 純粋な回数をカウント
        counts = data_df['コース'].dropna().astype(str).value_counts()
        for val, count in counts.items():
            if val in mapping:
                r, c = mapping[val]
                grid[r, c] = count
        z_label = "回数"
        colors = "Reds"
    
    else:
        # セーブ率の計算
        for course_num in mapping.keys():
            course_data = data_df[data_df['コース'].astype(str) == course_num]
            if not course_data.empty:
                save_rate = (course_data['結果'] == 'セーブ').sum() / len(course_data) * 100
                r, c = mapping[course_num]
                grid[r, c] = round(save_rate, 1)
        z_label = "セーブ率(%)"
        colors = "Blues"

    fig = px.imshow(
        grid,
        labels=dict(x="左右", y="上下", color=z_label),
        x=['左', '中', '右'],
        y=['上', '中', '下'],
        text_auto=True,
        color_continuous_scale=colors,
        title=title_label
    )
    fig.update_layout(width=450, height=450, coloraxis_showscale=False)
    return fig

# ==========================================
# 3. サイドバー (フィルター)
# ==========================================
st.sidebar.header("🔍 絞り込み")
at_list = ["すべて"] + sorted(list(df['AT'].dropna().unique()))
df_list = ["すべて"] + sorted(list(df['DF'].dropna().unique()))
g_list = ["すべて"] + sorted(list(df['ゴーリー'].dropna().unique()))

selected_at = st.sidebar.selectbox("ATを選択", at_list)
selected_df = st.sidebar.selectbox("DFを選択", df_list)
selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)

filtered_df = df.copy()
if selected_at != "すべて": filtered_df = filtered_df[filtered_df['AT'] == selected_at]
if selected_df != "すべて": filtered_df = filtered_df[filtered_df['DF'] == selected_df]
if selected_g != "すべて": filtered_df = filtered_df[filtered_df['ゴーリー'] == selected_g]

# ==========================================
# 4. メイン表示
# ==========================================
tab1, tab2, tab3 = st.tabs(["🔴 AT分析", "🔵 DF分析", "🟡 ゴーリー分析"])

with tab1:
    st.subheader("アタック分析")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**◆ 抜き方の傾向**")
        dodge_df = filtered_df[filtered_df['抜き方'] != "NULL"]
        if not dodge_df.empty:
            fig_dodge = px.pie(dodge_df, names='抜き方', hole=0.4)
            st.plotly_chart(fig_dodge, use_container_width=True)
    
    with col2:
        st.write("**◆ 得点コース（3×3）**")
        goal_df = filtered_df[filtered_df['結果'] == 'ゴール']
        if not goal_df.empty:
            st.plotly_chart(create_shot_heatmap(goal_df, "ゴール決定コース"), use_container_width=True)
        else:
            st.info("ゴールのデータがありません")

with tab2:
    st.subheader("ディフェンス分析")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**◆ 許した抜き方（苦手な方向）**")
        if not filtered_df.empty:
            df_dodge = filtered_df[filtered_df['抜き方'] != "NULL"]
            fig_df_dodge = px.bar(df_dodge['抜き方'].value_counts().reset_index(), x='抜き方', y='count', color='抜き方')
            st.plotly_chart(fig_df_dodge, use_container_width=True)
    with col2:
        st.write("**◆ 攻められた起点**")
        fig_pos = px.pie(filtered_df, names='起点')
        st.plotly_chart(fig_pos, use_container_width=True)

with tab3:
    st.subheader("ゴーリー分析")
    st.write("**◆ コース別セーブ率（3×3）**")
    # 枠内ショット（ゴール or セーブ）のみを対象
    shot_df = filtered_df[filtered_df['結果'].isin(['ゴール', 'セーブ'])]
    if not shot_df.empty:
        st.plotly_chart(create_shot_heatmap(shot_df, "セーブ率ヒートマップ(%)", mode="rate"), use_container_width=True)
    else:
        st.info("ショットのデータがありません")

with st.expander("📊 全データを確認"):
    st.dataframe(filtered_df)
