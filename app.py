import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="ラクロス総合分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 リアルタイム分析")

# --- 設定：スプレッドシートのURL ---
RAW_URL = "https://docs.google.com/spreadsheets/d/1Bx8lfO0kx0771QewN3J92CL7P0_M-IRx92jXPW7ELqs/edit?usp=sharing"

# URL変換
if "/edit" in RAW_URL:
    CSV_URL = RAW_URL.split("/edit")[0] + "/export?format=csv"
else:
    CSV_URL = RAW_URL

# --- 関数：2x5 シュートエリアヒートマップ ---
def create_area_heatmap(data, title, mode="shooter"):
    # エリア定義（1-5を上段、6-10を下段に配置）
    area_map = {
        1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (0, 3), 5: (0, 4),
        6: (1, 0), 7: (1, 1), 8: (1, 2), 9: (1, 3), 10: (1, 4)
    }
    z = np.zeros((2, 5))
    text_labels = np.full((2, 5), "", dtype=object)

    for area_num, (r, c) in area_map.items():
        area_data = data[data['シュートエリア'].astype(str) == str(area_num)]
        total = len(area_data)
        
        if total > 0:
            if mode == "shooter":
                # シューター：得点率 (ゴール数 / 総シュート数)
                success = area_data['ゴール'].sum()
                rate = success / total
                label = f"{rate:.0%}<br>({success}/{total})"
            else:
                # ゴーリー：セーブ率 (セーブ数 / 枠内シュート数)
                on_target = area_data['枠内'].sum()
                if on_target > 0:
                    saves = area_data['セーブ'].sum()
                    rate = saves / on_target
                    label = f"{rate:.0%}<br>({saves}/{on_target})"
                else:
                    rate = 0
                    label = "0%<br>(0/0)"
            z[r][c] = rate
            text_labels[r][c] = label
        else:
            z[r][c] = 0
            text_labels[r][c] = "データ無"

    colorscale = "Reds" if mode == "shooter" else "Blues"
    
    fig = px.imshow(
        z, x=['左2', '左1', '中央', '右1', '右2'], y=['内側', '外側'],
        text_auto=False, color_continuous_scale=colorscale, title=title,
        range_color=[0, 1] # 0%〜100%で固定
    )
    fig.update_traces(text=text_labels, texttemplate="%{text}")
    fig.update_layout(width=500, height=300, margin=dict(l=20, r=20, t=40, b=20))
    return st.plotly_chart(fig, use_container_width=True)

# --- 関数：3x3 ゴールコースヒートマップ（既存） ---
def create_course_heatmap(data, title, color_scale, key_id):
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    z = np.zeros((3, 3))
    counts = data['コース'].value_counts()
    for r in range(3):
        for c in range(3):
            val = grid_names[r][c]
            z[r][c] = counts.get(int(val), 0) + counts.get(str(val), 0)
    fig = px.imshow(z, x=['左', '中', '右'], y=['上', '中', '下'], text_auto=True, color_continuous_scale=color_scale, title=title)
    fig.update_layout(width=350, height=350, margin=dict(l=20, r=20, t=40, b=20))
    return st.plotly_chart(fig, use_container_width=False, key=key_id)

try:
    df_raw = pd.read_csv(CSV_URL)

    if not df_raw.empty:
        # ★解決策：最初の7列を抜き出す
        df = df_raw.iloc[:, :7].copy()
        df.columns = ['日時', 'ゴーリー', '背番号', '打つ位置', 'シュートエリア', 'コース', '結果']
        
        # 整形
        df['背番号'] = "#" + df['背番号'].astype(str).str.extract('(\d+)', expand=False).str.zfill(2)
        df['日時'] = pd.to_datetime(df['日時']).dt.date
        df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
        df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
        df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)

        shooter_ids = sorted(df['背番号'].unique().astype(str))
        goalie_names = sorted(df['ゴーリー'].unique().astype(str))
        tab_list = ["チーム全体", "🧤 ゴーリー集計"] + [f"🏃 {s}" for s in shooter_ids] + [f"🧤 {g}" for g in goalie_names]
        tabs = st.tabs(tab_list)

        # --- チーム全体 ---
        with tabs[0]:
            st.header("🏢 チーム全体の得点エリア分析")
            create_area_heatmap(df, "全シュートの得点率（位置別）", mode="shooter")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("総シュート数", f"{len(df)}本")
                create_course_heatmap(df[df['結果'] == 'ゴール'], "得点コース傾向", "Reds", "overall_c")
            with col2:
                st.subheader("📋 最新データ")
                st.dataframe(df.sort_values('日時', ascending=False).head(5), use_container_width=True)

        # --- ゴーリー集計 ---
        with tabs[1]:
            st.header("🧤 ゴーリー陣 セーブエリア分析")
            create_area_heatmap(df, "全ゴーリーのセーブ率（位置別）", mode="goalie")
            g_stats = df.groupby('ゴーリー').agg(枠内=('枠内', 'sum'), セーブ=('セーブ', 'sum')).reset_index()
            g_stats['セーブ率'] = (g_stats['セーブ'] / g_stats['枠内']).apply(lambda x: f"{x:.1%}" if x > 0 else "0.0%")
            st.dataframe(g_stats.sort_values('セーブ', ascending=False), use_container_width=True, hide_index=True)

        # --- 個別詳細 ---
        # 選手
        for i, s_id in enumerate(shooter_ids):
            with tabs[i + 2]:
                st.header(f"🏃 選手詳細: {s_id}")
                s_df = df[df['背番号'].astype(str) == s_id]
                create_area_heatmap(s_df, f"{s_id} の得点率ヒートマップ", mode="shooter")

        # ゴーリー
        offset = 2 + len(shooter_ids)
        for i, g_name in enumerate(goalie_names):
            with tabs[i + offset]:
                st.header(f"🧤 ゴーリー詳細: {g_name}")
                g_df = df[df['ゴーリー'].astype(str) == g_name]
                create_area_heatmap(g_df, f"{g_name} のセーブ率ヒートマップ", mode="goalie")

        if st.button('データを更新'):
            st.rerun()
    else:
        st.warning("スプレッドシートにデータがまだありません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    if 'df_raw' in locals():
        st.info(f"列数を確認してください: {len(df_raw.columns)} 列")
