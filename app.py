import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="ラクロス総合分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 リアルタイム分析")

# --- 設定：スプレッドシートのURL ---
RAW_URL = "https://docs.google.com/spreadsheets/d/1Bx8lfO0kx0771QewN3J92CL7P0_M-IRx92jXPW7ELqs/edit?usp=sharing"

# URLをCSV形式に変換
if "/edit" in RAW_URL:
    CSV_URL = RAW_URL.split("/edit")[0] + "/export?format=csv"
else:
    CSV_URL = RAW_URL

# ヒートマップ作成用関数
def create_heatmap(data, title, color_scale, key_id):
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
    # データを読み込む
    df_raw = pd.read_csv(CSV_URL)

    if not df_raw.empty:
        # ★解決策：最初の6列だけを抜き出して、名前を固定する
        # これで、スプレッドシートに余計な列（7列目以降）があっても無視できます
        df = df_raw.iloc[:, :6].copy()
        df.columns = ['日時', 'ゴーリー', '背番号', '打つ位置', 'コース', '結果']
        
        # データの整形
        df['日時'] = pd.to_datetime(df['日時']).dt.date
        df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
        df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
        df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)

        # UIの構築（以前と同じ）
        shooter_ids = sorted(df['背番号'].unique().astype(str))
        goalie_names = sorted(df['ゴーリー'].unique().astype(str))
        tab_list = ["チーム全体", "🧤 ゴーリー集計"] + [f"🏃 {s}" for s in shooter_ids] + [f"🧤 {g}" for g in goalie_names]
        tabs = st.tabs(tab_list)

        # --- チーム全体 ---
        with tabs[0]:
            st.header("🏢 チーム全体の成績")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.metric("総シュート数", f"{len(df)}本")
                st.metric("総ゴール数", f"{df['ゴール'].sum()}本")
            with col2:
                create_heatmap(df[df['結果'] == 'ゴール'], "チーム全体の得点傾向", "Reds", "overall_heat")
            with col3:
                st.subheader("📋 最新データ（直近5件）")
                st.dataframe(df.sort_values('日時', ascending=False).head(5), use_container_width=True)

        # --- ゴーリー集計 ---
        with tabs[1]:
            st.header("🧤 ゴーリー陣 総合分析")
            g_stats = df.groupby('ゴーリー').agg(枠内=('枠内', 'sum'), セーブ=('セーブ', 'sum')).reset_index()
            g_stats['セーブ率'] = (g_stats['セーブ'] / g_stats['枠内']).apply(lambda x: f"{x:.1%}" if x > 0 else "0.0%")
            st.dataframe(g_stats.sort_values('セーブ', ascending=False), use_container_width=True, hide_index=True)
            create_heatmap(df[df['結果'] == 'ゴール'], "ゴーリー陣全体の苦手傾向", "Oranges", "goalies_total_heat")

        # --- 個別タブのループ描画 ---
        # 選手詳細
        for i, s_id in enumerate(shooter_ids):
            with tabs[i + 2]:
                st.header(f"🏃 選手詳細: {s_id}")
                s_df = df[df['背番号'].astype(str) == s_id]
                c1, c2 = st.columns([3, 2])
                with c1:
                    trend = s_df.groupby('日時').agg(率=('ゴール', 'mean')).reset_index()
                    st.plotly_chart(px.line(trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1]), key=f"t_s_{s_id}")
                with c2:
                    create_heatmap(s_df[s_df['結果'] == 'ゴール'], "得点エリア", "Reds", f"h_s_{s_id}")

        # ゴーリー詳細
        offset = 2 + len(shooter_ids)
        for i, g_name in enumerate(goalie_names):
            with tabs[i + offset]:
                st.header(f"🧤 ゴーリー詳細: {g_name}")
                g_df = df[df['ゴーリー'].astype(str) == g_name]
                gc1, gc2 = st.columns([3, 2])
                with gc1:
                    g_trend = g_df[g_df['枠内']==1].groupby('日時').agg(率=('セーブ', 'mean')).reset_index()
                    st.plotly_chart(px.line(g_trend, x='日時', y='率', markers=True, range_y=[-0.1, 1.1]), key=f"t_g_{g_name}")
                with gc2:
                    create_heatmap(g_df[g_df['結果'] == 'ゴール'], "失点エリア", "Oranges", f"h_g_{g_name}")

        if st.button('データを更新'):
            st.rerun()

    else:
        st.warning("スプレッドシートにデータがまだありません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    # デバッグ用に実際の列数を表示させる
    if 'df_raw' in locals():
        st.info(f"現在のスプレッドシートの列数: {len(df_raw.columns)} 列")
        st.write("実際の列名:", list(df_raw.columns))
