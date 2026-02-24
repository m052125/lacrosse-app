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

# 起点の2×2マッピング関数
def create_2x2_origin_heatmap(data_df, title=""):
    grid = np.zeros((2, 2))
    # 四隅の起点を2x2にマッピング
    mapping = {
        '左上': (0, 0), '右上': (0, 1),
        '左裏': (1, 0), '右裏': (1, 1)
    }
    
    counts = data_df['起点'].dropna().astype(str).value_counts()
    for val, count in counts.items():
        if val in mapping:
            r, c = mapping[val]
            grid[r, c] = count

    fig = px.imshow(
        grid,
        labels=dict(x="左右", y="位置", color="回数"),
        x=['左', '右'],
        y=['上', '裏'],
        text_auto=True,
        color_continuous_scale='YlOrRd',
        title=title
    )
    fig.update_layout(width=350, height=350, coloraxis_showscale=False)
    return fig

# ==========================================
# 3. サイドバー (分析モード切替)
# ==========================================
st.sidebar.header("🔍 メインメニュー")
mode = st.sidebar.radio("表示モード", ["🔴 AT分析", "🔵 DF分析", "🟡 ゴーリー分析", "📊 全データ"])

# ==========================================
# 4. 各モードの表示ロジック
# ==========================================

# --- 【🔴 AT個人分析】 ---
if mode == "🔴 AT分析":
    at_list = ["全体"] + sorted(list(df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("分析するATを選択", at_list)
    
    if selected_at == "全体":
        at_df = df.dropna(subset=['AT'])
    else:
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
        st.metric("合計ショット率", f"{shot_rate:.1f}%")

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
    # --- 【新規】打った場所(1-10)ごとのショット率 ---
    st.divider()
    st.subheader("📍 打った位置別のショット決定率")
    if 'ショット位置' in at_df.columns:
        at_shot_df = at_df[at_df['終わり方'] == 'ショット'].dropna(subset=['ショット位置'])
        if not at_shot_df.empty:
            loc_stats = at_shot_df.groupby('ショット位置').agg(
                打った数=('結果', 'count'),
                ゴール数=('結果', lambda x: (x == 'ゴール').sum())
            ).reset_index()
            loc_stats['ショット率(%)'] = (loc_stats['ゴール数'] / loc_stats['打った数'] * 100).round(1)
            
            # X軸を文字列にして1〜10の順番を揃えやすくする
            loc_stats['ショット位置'] = loc_stats['ショット位置'].astype(str)
            fig_at_loc = px.bar(loc_stats, x='ショット位置', y='ショット率(%)', color='ショット率(%)', 
                                color_continuous_scale='Reds', text_auto=True, title="どのエリアから決めているか")
            st.plotly_chart(fig_at_loc, use_container_width=True)
        else:
            st.info("ショット位置のデータがまだありません。")
    else:
        st.info("スプレッドシートに「ショット位置」の列がまだありません。")
    
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
elif mode == "🔵 DF分析":
    df_list = ["全体"] + sorted(list(df['DF'].dropna().unique()))
    selected_df = st.sidebar.selectbox("分析するDFを選択", df_list)
    
    if selected_df == "全体":
        target_df = df.dropna(subset=['DF']).copy()
    else:
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
    st.subheader("📍 ショットを打たれた位置の分布")
    if 'ショット位置' in target_df.columns:
        df_shot_df = target_df[target_df['終わり方'] == 'ショット'].dropna(subset=['ショット位置'])
        if not df_shot_df.empty:
            df_shot_df['ショット位置'] = df_shot_df['ショット位置'].astype(str)
            fig_df_loc = px.pie(df_shot_df, names='ショット位置', hole=0.3, title="どのエリアまで侵入を許しているか")
            st.plotly_chart(fig_df_loc, use_container_width=True)
        else:
            st.info("ショット位置のデータがまだありません。")
    else:
        st.info("スプレッドシートに「ショット位置」の列がまだありません。")
        
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
elif mode == "🟡 ゴーリー分析":
    # ゴーリー選択
    g_list = ["全体"] + sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("分析するゴーリーを選択", g_list)
    
    if selected_g == "全体":
        g_full_df = df.dropna(subset=['ゴーリー']).copy()
    else:
        g_full_df = df[df['ゴーリー'] == selected_g].copy()
    
    # 【新規】シューター（AT）選択プルダウン
    at_options = ["全体"] + sorted(list(g_full_df['AT'].dropna().unique()))
    selected_at = st.sidebar.selectbox("シューター(AT)を絞り込む", at_options)
    
    # データのフィルタリング
    if selected_at == "全体":
        g_df = g_full_df
        header_name = "全体"
    else:
        g_df = g_full_df[g_full_df['AT'] == selected_at]
        header_name = selected_at
    
    st.header(f"🧤 ゴーリー: {selected_g} (対 {header_name}) の分析結果")

    st.subheader("📍 打たれた位置別のセーブ率")
    if 'ショット位置' in g_df.columns:
        g_shot_df = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])].dropna(subset=['ショット位置'])
        if not g_shot_df.empty:
            g_loc_stats = g_shot_df.groupby('ショット位置').agg(
                被ショット数=('結果', 'count'),
                セーブ数=('結果', lambda x: (x == 'セーブ').sum())
            ).reset_index()
            g_loc_stats['セーブ率(%)'] = (g_loc_stats['セーブ数'] / g_loc_stats['被ショット数'] * 100).round(1)
            
            g_loc_stats['ショット位置'] = g_loc_stats['ショット位置'].astype(str)
            fig_g_loc = px.bar(g_loc_stats, x='ショット位置', y='セーブ率(%)', color='セーブ率(%)', 
                               color_continuous_scale='Blues', text_auto=True, title="どのエリアからのショットを止めやすいか")
            st.plotly_chart(fig_g_loc, use_container_width=True)
        else:
            st.info("ショット位置のデータがまだありません。")
    else:
        st.info("スプレッドシートに「ショット位置」の列がまだありません。")
        
    st.subheader(f"📊 {header_name} に対するセーブ実績")
    shot_results = g_df[g_df['結果'].isin(['ゴール', 'セーブ'])]
    
    if not shot_results.empty:
        # シューター別のセーブ率算出
        at_stats = shot_results.groupby('AT').agg(
            対戦数=('結果', 'count'),
            セーブ数=('結果', lambda x: (x == 'セーブ').sum())
        ).reset_index()
        at_stats['セーブ率(%)'] = (at_stats['セーブ数'] / at_stats['対戦数'] * 100).round(1)
        at_stats['ラベル'] = at_stats['AT'] + " (" + at_stats['セーブ率(%)'].astype(str) + "%)"
        
        # 円グラフでセーブ成功の内訳を表示
        fig_save_pie = px.pie(at_stats, values='セーブ数', names='ラベル', hole=0.4, title="誰のショットをよく止めているか")
        st.plotly_chart(fig_save_pie, use_container_width=True)
    else:
        st.info("集計可能なショットデータがまだありません。")

    st.divider()

    # 2. 円グラフセクション
    col_pie1, col_pie2 = st.columns(2)
    with col_pie1:
        st.subheader("🥯 シューター(AT)の割合")
        fig_at_pie = px.pie(g_df, names='AT', hole=0.3, title="対戦したシューター分布")
        st.plotly_chart(fig_at_pie, use_container_width=True)
        
    with col_pie2:
        st.subheader("🥯 抜き方の割合")
        dodge_df = g_df[g_df['抜き方'] != "NULL"]
        fig_dodge_pie = px.pie(dodge_df, names='抜き方', hole=0.3, title="許した抜き方の分布")
        st.plotly_chart(fig_dodge_pie, use_container_width=True)

    st.divider()

    # 3. ヒートマップセクション
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        # ショット起点ヒートマップ (2x2)
        st.plotly_chart(create_2x2_origin_heatmap(g_df[g_df['終わり方']=='ショット'], title="ショット起点 (2×2マップ)"), use_container_width=True)
    with col_h2:
        # セーブコース (3x3)
        st.plotly_chart(create_3x3_heatmap(g_df[g_df['結果'] == 'セーブ'], title="セーブコース分布 (3×3)"), use_container_width=True)

# --- 【📊 全データ】 ---
else:
    st.header("📊 全データ一覧")
    st.dataframe(df.sort_values('タイムスタンプ', ascending=False))
