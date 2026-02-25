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
    GID = "1086529984"
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
# 【新規追加】テスト用の先輩・コーチメンバーリスト
# ==========================================
test_members = ['#11', '#26', '#67', 'パズーさん', 'りむさん', 'うりさん', 'ばらさん', 'いずさん', 'はなさん']

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

# 【新規追加】AT分析用：コース別 決定率ヒートマップ
def create_at_course_heatmap(data_df, title=""):
    grid_color = np.zeros((3, 3)) # 色（決定率）用
    grid_text = np.empty((3, 3), dtype=object) # テキスト表示用
    
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2),
        '4': (1, 0), '5': (1, 1), '6': (1, 2),
        '7': (2, 0), '8': (2, 1), '9': (2, 2)
    }
    
    shot_df = data_df[data_df['終わり方'] == 'ショット'].copy()
    # 小数点を排除してきれいな文字列に
    shot_df['コース_clean'] = pd.to_numeric(shot_df['コース'], errors='coerce').fillna(0).astype(int).astype(str)
    
    for course_num, (r, c) in mapping.items():
        course_data = shot_df[shot_df['コース_clean'] == course_num]
        total_shots = len(course_data)
        goals = len(course_data[course_data['結果'] == 'ゴール'])
        if total_shots > 0:
            rate = (goals / total_shots) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"{goals}/{total_shots}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = "0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="位置", color="決定率(%)"),
        x=['左', '中', '右'], y=['上', '中', '下'], color_continuous_scale='Reds', title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=450, height=450, coloraxis_showscale=True)
    return fig

# 【新規追加・DF分析用】起点別 被ショット率ヒートマップ
def create_df_origin_ratio_heatmap(data_df, title=""):
    grid_color = np.full((3, 3), np.nan) 
    grid_text = np.full((3, 3), "", dtype=object) 
    
    mapping = {
        '左上': (0, 0), 'センター': (0, 1), '右上': (0, 2),
        '左横': (1, 0), '右横': (1, 2),
        '左裏': (2, 0), '右裏': (2, 2)
    }
    
    data_df = data_df.copy()
    data_df['起点_clean'] = data_df['起点'].astype(str).str.strip()
    
    for origin, (r, c) in mapping.items():
        origin_data = data_df[data_df['起点_clean'] == origin]
        total_matchups = len(origin_data)
        shots_allowed = len(origin_data[origin_data['終わり方'] == 'ショット'])
        
        if total_matchups > 0:
            rate = (shots_allowed / total_matchups) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"{shots_allowed}/{total_matchups}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = "0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="位置", color="被ショット率(%)"),
        x=['左', '中', '右'], y=['上', '横', '裏'], color_continuous_scale='Reds', title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=450, height=450, coloraxis_showscale=True)
    return fig

# 【ゴーリー分析用】起点別 セーブ率ヒートマップ (2x2)
def create_goalie_origin_ratio_heatmap(data_df, title=""):
    grid_color = np.zeros((2, 2))
    grid_text = np.empty((2, 2), dtype=object)
    mapping = {'左上': (0, 0), '右上': (0, 1), '左裏': (1, 0), '右裏': (1, 1)}
    
    shot_df = data_df[data_df['終わり方'] == 'ショット'].copy()
    shot_df['起点_clean'] = shot_df['起点'].astype(str).str.strip()
    
    for origin, (r, c) in mapping.items():
        origin_shots = shot_df[shot_df['起点_clean'] == origin]
        total_shots = len(origin_shots)
        saves = len(origin_shots[origin_shots['結果'] == 'セーブ'])
        
        if total_shots > 0:
            rate = (saves / total_shots) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"{saves}/{total_shots}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = "0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="位置", color="セーブ率(%)"),
        x=['左', '右'], y=['上', '裏'], color_continuous_scale='Blues', title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=350, height=350, coloraxis_showscale=True)
    return fig

# 【ゴーリー分析用】コース別 セーブ率ヒートマップ (3x3)
def create_goalie_course_ratio_heatmap(data_df, title=""):
    grid_color = np.zeros((3, 3)) 
    grid_text = np.empty((3, 3), dtype=object) 
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2),
        '4': (1, 0), '5': (1, 1), '6': (1, 2),
        '7': (2, 0), '8': (2, 1), '9': (2, 2)
    }
    
    shot_df = data_df[data_df['終わり方'] == 'ショット'].copy()
    shot_df['コース_clean'] = pd.to_numeric(shot_df['コース'], errors='coerce').fillna(0).astype(int).astype(str)
    
    for course_num, (r, c) in mapping.items():
        course_data = shot_df[shot_df['コース_clean'] == course_num]
        total_shots = len(course_data)
        saves = len(course_data[course_data['結果'] == 'セーブ'])
        
        if total_shots > 0:
            rate = (saves / total_shots) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"{saves}/{total_shots}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = "0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="位置", color="セーブ率(%)"),
        x=['左', '中', '右'], y=['上', '中', '下'], color_continuous_scale='Blues', title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=450, height=450, coloraxis_showscale=True)
    return fig

# 【修正】ショット位置(1-10)の2x5割合ヒートマップ
def create_shot_position_heatmap(data_df, mode="AT", title=""):
    grid_color = np.zeros((2, 5)) 
    grid_text = np.empty((2, 5), dtype=object) 
    
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2), '4': (0, 3), '5': (0, 4),
        '6': (1, 0), '7': (1, 1), '8': (1, 2), '9': (1, 3), '10': (1, 4)
    }
    
    shot_df = data_df[data_df['終わり方'] == 'ショット'].copy()
    shot_df['ショット位置_clean'] = pd.to_numeric(shot_df['ショット位置'], errors='coerce').fillna(0).astype(int).astype(str)
    
    for loc_num, (r, c) in mapping.items():
        loc_data = shot_df[shot_df['ショット位置_clean'] == loc_num]
        total_shots = len(loc_data)
        
        if mode == "AT":
            success = len(loc_data[loc_data['結果'] == 'ゴール'])
            color_scale = 'Reds'
            c_label = "決定率(%)"
        elif mode == "DF":
            success = len(loc_data[loc_data['結果'] == 'ゴール'])
            color_scale = 'Oranges'
            c_label = "失点率(%)"
        elif mode == "G":
            success = len(loc_data[loc_data['結果'] == 'セーブ'])
            color_scale = 'Blues'
            c_label = "セーブ率(%)"
            
        if total_shots > 0:
            rate = (success / total_shots) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"[{loc_num}]<br>{success}/{total_shots}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = f"[{loc_num}]<br>0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="段", color=c_label),
        x=['1', '2', '3', '4', '5'], y=['上段', '下段'], 
        color_continuous_scale=color_scale, title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=700, height=350, coloraxis_showscale=True)
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
    unique_at = set(df['AT'].dropna().unique().tolist() + test_members)
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
            # 【修正点】NULLなどを排除し、「右手」「左手」に完全一致するものだけを円グラフにする
            hand_df = at_df[at_df['利き手'].isin(['右手', '左手'])]
            if not hand_df.empty:
                st.plotly_chart(px.pie(hand_df, names='利き手', hole=0.4), use_container_width=True)
            else:
                st.info("利き手のデータがありません。")
                
    # --- 【修正】打った場所の2x5ヒートマップ ---
    st.divider()
    st.subheader("📍 打った位置別のショット決定率")
    if 'ショット位置' in at_df.columns:
        st.plotly_chart(create_shot_position_heatmap(at_df, mode="AT", title="どのエリアから決めているか (決定率)"), use_container_width=True)
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

    st.divider()
    st.subheader("🎯 コース別 ショット決定率 (3×3)")
    # 【修正点】単純な回数ではなく、新たに作成した決定率ベースのヒートマップ関数を呼び出す
    st.plotly_chart(create_at_course_heatmap(at_df, title="ゴール数 / ショット数 (決定率%)"), use_container_width=True)

    # ----------------------------------------------------
    # 【追加】ATの苦手なDFランキング
    # ----------------------------------------------------
    st.divider()
    if selected_at == "全体":
        st.subheader("🏆 全DFのショット阻止率ランキング (AT全体がショットに行けなかった割合)")
    else:
        st.subheader(f"⚠️ {selected_at} の苦手なDFランキング (ショットに行けなかった割合)")
        
    # DFごとの対戦成績を計算
    df_stats = at_df.groupby('DF').agg(
        対戦数=('終わり方', 'count'),
        ショット数=('終わり方', lambda x: (x == 'ショット').sum())
    ).reset_index()
    
    df_stats['ショットに行けなかった数'] = df_stats['対戦数'] - df_stats['ショット数']
    df_stats['ショットに行けなかった割合(%)'] = (df_stats['ショットに行けなかった数'] / df_stats['対戦数'] * 100).round(1)
    
    # 割合が高い順（苦手な順）にソート。割合が同じ場合は対戦数が多い順
    df_stats = df_stats.sort_values(by=['ショットに行けなかった割合(%)', '対戦数'], ascending=[False, False])
    df_stats = df_stats.reset_index(drop=True)
    df_stats.index = df_stats.index + 1 # 順位を1からにする
    
    st.dataframe(df_stats, use_container_width=True)

# --- 【🔵 DF個人分析】 ---
elif mode == "🔵 DF分析":
    unique_df_names = set(df['DF'].dropna().unique().tolist() + test_members)
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

    # --- 【修正】ショットを打たれた場所の2x5ヒートマップ ---
    st.divider()
    st.subheader("📍 ショットを打たれた位置の失点率")
    if 'ショット位置' in target_df.columns:
        st.plotly_chart(create_shot_position_heatmap(target_df, mode="DF", title="どのエリアからのショットで失点しやすいか (失点率)"), use_container_width=True)
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

    # 【修正点】回数ではなく、割合（被ショット数 / その起点での対戦数）を表示するヒートマップに変更
    st.plotly_chart(create_df_origin_ratio_heatmap(target_df, title="起点別 被ショット率マップ (3×3)"), use_container_width=True)

    # ----------------------------------------------------
    # 【追加】DFの苦手なATランキング
    # ----------------------------------------------------
    st.divider()
    if selected_df == "全体":
        st.subheader("🏆 全ATの突破率ランキング (DF全体が抜かれた割合)")
    else:
        st.subheader(f"⚠️ {selected_df} の苦手なATランキング (抜かれた割合)")
        
    at_stats = target_df.groupby('AT').agg(
        対戦数=('終わり方', 'count'),
        抜かれた数=('終わり方', lambda x: (x == 'ショット').sum())
    ).reset_index()
    
    at_stats['抜かれた割合(%)'] = (at_stats['抜かれた数'] / at_stats['対戦数'] * 100).round(1)
    
    # 抜かれた割合が高い順（苦手な順）にソート
    at_stats = at_stats.sort_values(by=['抜かれた割合(%)', '対戦数'], ascending=[False, False])
    at_stats = at_stats.reset_index(drop=True)
    at_stats.index = at_stats.index + 1
    
    st.dataframe(at_stats, use_container_width=True)

# --- 【🟡 ゴーリー詳細分析】 ---
elif mode == "🟡 ゴーリー分析":
    # ゴーリー選択
    unique_g_names = set(df['ゴーリー'].dropna().unique().tolist())
    g_list = ["全体"] + sorted(list(unique_g_names))
    selected_g = st.sidebar.selectbox("分析するゴーリーを選択", g_list)
    if selected_g == "全体":
        g_full_df = df.dropna(subset=['ゴーリー']).copy()
    else:
        g_full_df = df[df['ゴーリー'] == selected_g].copy()

    unique_at_options = set(g_full_df['AT'].dropna().unique().tolist() + test_members)
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

    # --- 【修正】打たれた場所の2x5ヒートマップ ---
    st.subheader("📍 打たれた位置別のセーブ率")
    if 'ショット位置' in g_df.columns:
        st.plotly_chart(create_shot_position_heatmap(g_df, mode="G", title="どのエリアからのショットを止めやすいか (セーブ率)"), use_container_width=True)
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
        # 【修正点】回数ではなく、割合（セーブ数 / その起点から打たれたショット数）の2x2マップ
        st.plotly_chart(create_goalie_origin_ratio_heatmap(g_df, title="起点別 セーブ率マップ (2×2)"), use_container_width=True)
    with col_h2:
        # 【修正点】回数ではなく、割合（セーブ数 / そのコースに打たれたショット数）の3x3マップ
        st.plotly_chart(create_goalie_course_ratio_heatmap(g_df, title="コース別 セーブ率分布 (3×3)"), use_container_width=True)

    # ----------------------------------------------------
    # 【追加】ゴーリーの苦手なATランキング
    # ----------------------------------------------------
    st.divider()
    if selected_g == "全体":
        st.subheader("🏆 全ATの決定率ランキング (ゴーリー全体から見たセーブ率ワースト)")
    else:
        st.subheader(f"⚠️ {selected_g} の苦手なATランキング (セーブ率ワースト)")
        
    # ※特定のシューターで絞り込んでいる場合でも、ランキングは全員の中から出すため「g_full_df」を使用
    g_full_shot_results = g_full_df[g_full_df['結果'].isin(['ゴール', 'セーブ'])]
    
    if not g_full_shot_results.empty:
        g_ranking_stats = g_full_shot_results.groupby('AT').agg(
            被ショット数=('結果', 'count'),
            セーブ数=('結果', lambda x: (x == 'セーブ').sum())
        ).reset_index()
        
        g_ranking_stats['セーブ率(%)'] = (g_ranking_stats['セーブ数'] / g_ranking_stats['被ショット数'] * 100).round(1)
        
        # セーブ率が低い順（苦手な順）にソート
        g_ranking_stats = g_ranking_stats.sort_values(by=['セーブ率(%)', '被ショット数'], ascending=[True, False])
        g_ranking_stats = g_ranking_stats.reset_index(drop=True)
        g_ranking_stats.index = g_ranking_stats.index + 1
        
        st.dataframe(g_ranking_stats, use_container_width=True)
# --- 【📊 全データ】 ---
else:
    st.header("📊 全データ一覧")
    st.dataframe(df.sort_values('タイムスタンプ', ascending=False))
