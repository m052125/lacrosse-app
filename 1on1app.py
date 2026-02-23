import streamlit as st
import pandas as pd
import plotly.express as px

# ページ設定（横広に表示）
st.set_page_config(page_title="1on1 分析ダッシュボード", layout="wide")

st.title("🥍 1on1 データ分析ダッシュボード")

# ==========================================
# 1. データの読み込み (Googleスプレッドシートから)
# ==========================================
@st.cache_data(ttl=60) # 60秒ごとにデータをキャッシュ更新
def load_data():
    # いただいたURLから抽出したIDとシート番号（gid）
    SHEET_ID = "1hRkai8KYkb2nM8ZHA5h56JGst8pp9t8jUHu2jV-Nd2E"
    GID = "935578573"
    
    # 指定のシートをCSVとして読み込むURL
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    try:
        df = pd.read_csv(csv_url)
        
        # フォームのヘッダー名（列の名前）を、プログラムが扱いやすい名前に変換する
        df = df.rename(columns={
            'ショットを打った手': '利き手',
            'ショットコース': 'コース',
            'ショット結果': '結果'
        })
        return df
    except Exception as e:
        # エラーの具体的な理由を画面に表示する
        st.error(f"エラーが発生しました: {e}")
        return pd.DataFrame()

df = load_data()

# データが空の場合のストップ処理
if df.empty:
    st.warning("データを取得できませんでした。スプレッドシートの右上「共有」設定が「リンクを知っている全員（閲覧者）」になっているか確認してください。")
    st.stop()

# ==========================================
# 2. サイドバー (フィルター設定)
# ==========================================
st.sidebar.header("🔍 絞り込みフィルター")

# 選手のリストを取得してフィルターを作成（NULLや空欄を排除）
at_list = ["すべて"] + list(df['AT'].dropna().unique())
df_list = ["すべて"] + list(df['DF'].dropna().unique())
g_list = ["すべて"] + list(df['ゴーリー'].dropna().unique())

selected_at = st.sidebar.selectbox("ATを選択", at_list)
selected_df = st.sidebar.selectbox("DFを選択", df_list)
selected_g = st.sidebar.selectbox("ゴーリーを選択", g_list)

# フィルターの適用
filtered_df = df.copy()
if selected_at != "すべて":
    filtered_df = filtered_df[filtered_df['AT'] == selected_at]
if selected_df != "すべて":
    filtered_df = filtered_df[filtered_df['DF'] == selected_df]
if selected_g != "すべて":
    filtered_df = filtered_df[filtered_df['ゴーリー'] == selected_g]

# ==========================================
# 3. メイン画面 (ダッシュボード表示)
# ==========================================

tab1, tab2, tab3 = st.tabs(["🔴 AT分析", "🔵 DF分析", "🟡 ゴーリー分析"])

# --- 【タブ1】AT分析 ---
with tab1:
    st.subheader(f"AT成績: {selected_at if selected_at != 'すべて' else '全体'}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**◆ 抜き方（イン/アウト）別の使用割合**")
        if '抜き方' in filtered_df.columns:
            dodge_df = filtered_df[filtered_df['抜き方'] != "NULL"]
            dodge_counts = dodge_df['抜き方'].value_counts().reset_index()
            dodge_counts.columns = ['抜き方', '回数']
            if not dodge_counts.empty:
                fig_dodge = px.pie(dodge_counts, values='回数', names='抜き方', hole=0.4)
                st.plotly_chart(fig_dodge, use_container_width=True)
            else:
                st.info("データがありません")
            
    with col2:
        st.markdown("**◆ 左右どちらの手で打ったか**")
        if '利き手' in filtered_df.columns:
            # NULLや空欄を除外
            hand_df = filtered_df[filtered_df['利き手'] != "NULL"]
            hand_counts = hand_df['利き手'].value_counts().reset_index()
            hand_counts.columns = ['利き手', '回数']
            if not hand_counts.empty:
                fig_hand = px.bar(hand_counts, x='利き手', y='回数', color='利き手')
                st.plotly_chart(fig_hand, use_container_width=True)
            else:
                st.info("データがありません")

    st.markdown("**◆ ショットコース別の決定数**")
    if 'コース' in filtered_df.columns and '結果' in filtered_df.columns:
        goal_df = filtered_df[filtered_df['結果'] == 'ゴール']
        if not goal_df.empty:
            course_counts = goal_df['コース'].value_counts().reset_index()
            course_counts.columns = ['コース', 'ゴール数']
            fig_course = px.bar(course_counts, x='コース', y='ゴール数', color='ゴール数', 
                                color_continuous_scale='Reds')
            st.plotly_chart(fig_course, use_container_width=True)
        else:
            st.info("ゴールが決まったデータがまだありません")

# --- 【タブ2】DF分析 ---
with tab2:
    st.subheader(f"DF成績: {selected_df if selected_df != 'すべて' else '全体'}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**◆ 許した抜き方（抜かれやすい方向）**")
        if '抜き方' in filtered_df.columns:
            df_dodge = filtered_df[filtered_df['抜き方'] != "NULL"]
            dodge_counts = df_dodge['抜き方'].value_counts().reset_index()
            dodge_counts.columns = ['抜かれた方向', '回数']
            if not dodge_counts.empty:
                fig_df_dodge = px.bar(dodge_counts, x='抜かれた方向', y='回数', color='抜かれた方向')
                st.plotly_chart(fig_df_dodge, use_container_width=True)
            else:
                st.info("データがありません")
            
    with col2:
        st.markdown("**◆ アタックの起点（どのエリアから攻められているか）**")
        if '起点' in filtered_df.columns:
            pos_df = filtered_df[filtered_df['起点'] != "NULL"]
            pos_counts = pos_df['起点'].value_counts().reset_index()
            pos_counts.columns = ['起点', '回数']
            if not pos_counts.empty:
                fig_pos = px.pie(pos_counts, values='回数', names='起点')
                st.plotly_chart(fig_pos, use_container_width=True)
            else:
                st.info("データがありません")

# --- 【タブ3】G（ゴーリー）分析 ---
with tab3:
    st.subheader(f"ゴーリー成績: {selected_g if selected_g != 'すべて' else '全体'}")
    
    st.markdown("**◆ コース別 セーブ率**")
    if 'コース' in filtered_df.columns and '結果' in filtered_df.columns:
        # 枠内ショット（ゴール または セーブ）のみを対象に計算
        shot_df = filtered_df[filtered_df['結果'].isin(['ゴール', 'セーブ'])]
        
        if not shot_df.empty:
            save_stats = shot_df.groupby('コース')['結果'].apply(
                lambda x: (x == 'セーブ').sum() / len(x) * 100
            ).reset_index()
            save_stats.columns = ['コース', 'セーブ率(%)']
            save_stats['セーブ率(%)'] = save_stats['セーブ率(%)'].round(1)
            
            fig_save = px.bar(save_stats, x='コース', y='セーブ率(%)', 
                              color='セーブ率(%)', color_continuous_scale='Blues',
                              range_y=[0, 100])
            st.plotly_chart(fig_save, use_container_width=True)
        else:
            st.info("集計対象となる枠内ショット（ゴール・セーブ）のデータがまだありません。")

# ==========================================
# 4. 生データの表示
# ==========================================
with st.expander("📊 生データを表示 (テーブル)"):
    st.dataframe(filtered_df)
