import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="フリシュー総合分析ダッシュボード", layout="wide", page_icon="🥍")
st.title("🥍 フリシュー 総合戦略分析ダッシュボード")

# ==========================================
# 1. データの読み込み (Googleスプレッドシート)
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    RAW_URL = "https://docs.google.com/spreadsheets/d/1Bx8lfO0kx0771QewN3J92CL7P0_M-IRx92jXPW7ELqs/edit?usp=sharing"
    if "/edit" in RAW_URL:
        csv_url = RAW_URL.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = RAW_URL
        
    try:
        df_raw = pd.read_csv(csv_url)
        if df_raw.empty:
            return pd.DataFrame()
            
        # 最初の7列を抜き出して名前を固定
        df = df_raw.iloc[:, :7].copy()
        df.columns = ['日時', 'ゴーリー', '背番号', '打つ位置', 'シュートエリア', 'コース', '結果']
        
        # データの整形
        df['背番号'] = "#" + df['背番号'].astype(str).str.extract('(\d+)', expand=False).str.zfill(2)
        df['日時_raw'] = pd.to_datetime(df['日時'], errors='coerce') # フィルター用に日時型を保持
        df['日時'] = df['日時_raw'].dt.date
        df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
        df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
        df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)
        
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

raw_df = load_data()

if raw_df.empty:
    st.warning("データがまだ読み込めません。Unityアプリからデータを送信してください。")
    st.stop()

# ==========================================
# サイドバー：期間フィルター
# ==========================================
st.sidebar.header("📅 期間フィルター")

valid_dates_df = raw_df.dropna(subset=['日時_raw'])

if not valid_dates_df.empty:
    min_date = valid_dates_df['日時_raw'].min().date()
    max_date = valid_dates_df['日時_raw'].max().date()
    
    selected_date_range = st.sidebar.date_input(
        "分析する期間を選択",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if isinstance(selected_date_range, tuple):
        if len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = raw_df[(raw_df['日時_raw'] >= start_dt) & (raw_df['日時_raw'] <= end_dt)].copy()
        elif len(selected_date_range) == 1:
            start_date = selected_date_range[0]
            start_dt = pd.to_datetime(start_date)
            end_dt = start_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = raw_df[(raw_df['日時_raw'] >= start_dt) & (raw_df['日時_raw'] <= end_dt)].copy()
        else:
            df = raw_df.copy()
    else:
        df = raw_df.copy()
else:
    df = raw_df.copy()

st.sidebar.markdown("---")

# ==========================================
# 2. 共通ヒートマップ関数
# ==========================================

# 2x5 シュートエリアヒートマップ
def create_area_heatmap(data_df, title="", mode="shooter"):
    area_map = {
        1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (0, 3), 5: (0, 4),
        6: (1, 0), 7: (1, 1), 8: (1, 2), 9: (1, 3), 10: (1, 4)
    }
    z = np.zeros((2, 5))
    text_labels = np.full((2, 5), "", dtype=object)

    for area_num, (r, c) in area_map.items():
        area_data = data_df[data_df['シュートエリア'].astype(str) == str(area_num)]
        total = len(area_data)
        
        if total > 0:
            if mode == "shooter":
                success = area_data['ゴール'].sum()
                rate = (success / total) * 100
                label = f"[{area_num}]<br>{success}/{total}<br>({rate:.1f}%)"
            else:
                on_target = area_data['枠内'].sum()
                if on_target > 0:
                    saves = area_data['セーブ'].sum()
                    rate = (saves / on_target) * 100
                    label = f"[{area_num}]<br>{saves}/{on_target}<br>({rate:.1f}%)"
                else:
                    rate = 0
                    label = f"[{area_num}]<br>0/0<br>(0.0%)"
            z[r][c] = rate
            text_labels[r][c] = label
        else:
            z[r][c] = 0
            text_labels[r][c] = f"[{area_num}]<br>0/0<br>(0.0%)"

    colorscale = "Reds" if mode == "shooter" else "Blues"
    c_label = "決定率(%)" if mode == "shooter" else "セーブ率(%)"
    
    fig = px.imshow(
        z, x=['左2', '左1', '中央', '右1', '右2'], y=['上段', '下段'],
        text_auto=False, color_continuous_scale=colorscale, title=title,
        labels=dict(x="左右", y="段", color=c_label)
    )
    fig.update_traces(text=text_labels, texttemplate="%{text}")
    fig.update_layout(width=700, height=350, coloraxis_showscale=True)
    return fig

# 3x3 コース別ヒートマップ
def create_course_heatmap(data_df, title="", mode="shooter"):
    grid_color = np.zeros((3, 3))
    grid_text = np.empty((3, 3), dtype=object)
    mapping = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2),
        '4': (1, 0), '5': (1, 1), '6': (1, 2),
        '7': (2, 0), '8': (2, 1), '9': (2, 2)
    }
    
    data_df = data_df.copy()
    data_df['コース_clean'] = pd.to_numeric(data_df['コース'], errors='coerce').fillna(0).astype(int).astype(str)
    
    for course_num, (r, c) in mapping.items():
        course_data = data_df[data_df['コース_clean'] == course_num]
        
        if mode == "shooter":
            total_shots = len(course_data)
            success = len(course_data[course_data['結果'] == 'ゴール'])
            colorscale = 'Reds'
            c_label = "決定率(%)"
            base_total = total_shots
        else:
            on_target_data = course_data[course_data['枠内'] == 1]
            base_total = len(on_target_data)
            success = len(on_target_data[on_target_data['結果'] == 'セーブ'])
            colorscale = 'Blues'
            c_label = "セーブ率(%)"
            
        if base_total > 0:
            rate = (success / base_total) * 100
            grid_color[r, c] = rate
            grid_text[r, c] = f"{success}/{base_total}<br>({rate:.1f}%)"
        else:
            grid_color[r, c] = 0
            grid_text[r, c] = "0/0<br>(0.0%)"
            
    fig = px.imshow(
        grid_color, labels=dict(x="左右", y="位置", color=c_label),
        x=['左', '中', '右'], y=['上', '中', '下'], color_continuous_scale=colorscale, title=title
    )
    fig.update_traces(text=grid_text, texttemplate="%{text}")
    fig.update_layout(width=450, height=450, coloraxis_showscale=True)
    return fig

# ==========================================
# 3. サイドバー (分析モード切替)
# ==========================================
st.sidebar.header("🔍 メインメニュー")
mode = st.sidebar.radio("表示モード", ["🏢 チーム全体", "🔴 シューター分析", "🔵 ゴーリー分析", "📊 全データ"])

# ==========================================
# 4. 各モードの表示ロジック
# ==========================================

# --- 【🏢 チーム全体】 ---
if mode == "🏢 チーム全体":
    st.header("🏢 チーム全体の成績")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総シュート数", f"{len(df)} 本")
    with col2:
        goals = df['ゴール'].sum()
        rate = (goals / len(df) * 100) if len(df) > 0 else 0
        st.metric("総ゴール数 (決定率)", f"{goals} 本 ({rate:.1f}%)")
    with col3:
        saves = df['セーブ'].sum()
        on_target = df['枠内'].sum()
        save_rate = (saves / on_target * 100) if on_target > 0 else 0
        st.metric("チーム全体セーブ率", f"{save_rate:.1f}%")

    st.divider()
    st.subheader("📍 チーム得点傾向 (エリア・コース)")
    col_h1, col_h2 = st.columns([3, 2])
    with col_h1:
        st.plotly_chart(create_area_heatmap(df, title="どのエリアから決めているか", mode="shooter"), use_container_width=True)
    with col_h2:
        st.plotly_chart(create_course_heatmap(df, title="どのコースに決めているか", mode="shooter"), use_container_width=True)

# --- 【🔴 シューター分析】 ---
elif mode == "🔴 シューター分析":
    shooter_list = ["全体"] + sorted(list(df['背番号'].dropna().unique()))
    selected_shooter = st.sidebar.selectbox("分析するシューターを選択", shooter_list)
    
    if selected_shooter == "全体":
        s_df = df.copy()
        st.header("🔴 シューター全員 の分析結果")
    else:
        s_df = df[df['背番号'] == selected_shooter].copy()
        st.header(f"👤 シューター: {selected_shooter} の分析結果")
        
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("総シュート数", len(s_df))
    with col_info2:
        goals = s_df['ゴール'].sum()
        rate = (goals / len(s_df) * 100) if len(s_df) > 0 else 0
        st.metric("ゴール数", goals)
    with col_info3:
        st.metric("ショット決定率", f"{rate:.1f}%")

    st.divider()
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.subheader("📈 決定率の推移")
        trend = s_df.groupby('日時').agg(率=('ゴール', 'mean')).reset_index()
        fig_trend = px.line(trend, x='日時', y='率', markers=True, title="日別の決定率変化")
        fig_trend.update_layout(yaxis=dict(tickformat=".0%", range=[-0.1, 1.1]))
        st.plotly_chart(fig_trend, use_container_width=True)
    with col_t2:
        st.subheader("📊 結果の内訳")
        st.plotly_chart(px.pie(s_df, names='結果', hole=0.4, title="シュート結果"), use_container_width=True)

    st.divider()
    st.subheader("📍 打った位置とコースの決定率")
    col_h1, col_h2 = st.columns([3, 2])
    with col_h1:
        st.plotly_chart(create_area_heatmap(s_df, title="打ったエリア別の決定率", mode="shooter"), use_container_width=True)
    with col_h2:
        st.plotly_chart(create_course_heatmap(s_df, title="コース別の決定率", mode="shooter"), use_container_width=True)

    st.divider()
    st.subheader("🏆 苦手なゴーリーランキング (シュートを止められた割合)")
    g_stats = s_df[s_df['枠内']==1].groupby('ゴーリー').agg(
        枠内シュート数=('枠内', 'count'),
        セーブされた数=('セーブ', 'sum')
    ).reset_index()
    g_stats['阻止された割合(%)'] = (g_stats['セーブされた数'] / g_stats['枠内シュート数'] * 100).round(1)
    g_stats = g_stats.sort_values(by=['阻止された割合(%)', '枠内シュート数'], ascending=[False, False]).reset_index(drop=True)
    g_stats.index = g_stats.index + 1
    st.dataframe(g_stats, use_container_width=True)

# --- 【🔵 ゴーリー分析】 ---
elif mode == "🔵 ゴーリー分析":
    goalie_list = ["全体"] + sorted(list(df['ゴーリー'].dropna().unique()))
    selected_g = st.sidebar.selectbox("分析するゴーリーを選択", goalie_list)
    
    if selected_g == "全体":
        g_df = df.copy()
        st.header("🔵 ゴーリー全員 の分析結果")
    else:
        g_df = df[df['ゴーリー'] == selected_g].copy()
        st.header(f"🧤 ゴーリー: {selected_g} の分析結果")
        
    on_target_df = g_df[g_df['枠内'] == 1].copy()
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("被枠内シュート数", len(on_target_df))
    with col_info2:
        saves = on_target_df['セーブ'].sum()
        st.metric("セーブ数", saves)
    with col_info3:
        rate = (saves / len(on_target_df) * 100) if len(on_target_df) > 0 else 0
        st.metric("セーブ率", f"{rate:.1f}%")

    st.divider()
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.subheader("📈 セーブ率の推移")
        trend = on_target_df.groupby('日時').agg(率=('セーブ', 'mean')).reset_index()
        fig_trend = px.line(trend, x='日時', y='率', markers=True, title="日別のセーブ率変化")
        fig_trend.update_layout(yaxis=dict(tickformat=".0%", range=[-0.1, 1.1]))
        st.plotly_chart(fig_trend, use_container_width=True)
    with col_t2:
        st.subheader("🥯 シュートを打ってきた選手")
        st.plotly_chart(px.pie(g_df, names='背番号', hole=0.3, title="対戦したシューター分布"), use_container_width=True)

    st.divider()
    st.subheader("📍 打たれた位置とコースのセーブ率")
    col_h1, col_h2 = st.columns([3, 2])
    with col_h1:
        st.plotly_chart(create_area_heatmap(g_df, title="エリア別 セーブ率マップ", mode="goalie"), use_container_width=True)
    with col_h2:
        st.plotly_chart(create_course_heatmap(g_df, title="コース別 セーブ率マップ", mode="goalie"), use_container_width=True)

    st.divider()
    st.subheader("⚠️ 苦手なシューターランキング (失点してしまった割合)")
    s_stats = on_target_df.groupby('背番号').agg(
        被枠内シュート=('枠内', 'count'),
        失点数=('ゴール', 'sum')
    ).reset_index()
    s_stats['失点率(%)'] = (s_stats['失点数'] / s_stats['被枠内シュート'] * 100).round(1)
    s_stats = s_stats.sort_values(by=['失点率(%)', '被枠内シュート'], ascending=[False, False]).reset_index(drop=True)
    s_stats.index = s_stats.index + 1
    st.dataframe(s_stats, use_container_width=True)

# --- 【📊 全データ】 ---
else:
    st.header("📊 全データ一覧")
    st.dataframe(df.drop(columns=['日時_raw']).sort_values('日時', ascending=False), use_container_width=True)
