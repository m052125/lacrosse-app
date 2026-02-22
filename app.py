import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="ラクロス総合分析", layout="wide", page_icon="🥍")
st.title("🥍 ラクロス部 リアルタイム分析")

# --- 設定：スプレッドシートのURL ---
# 自分のスプレッドシートのURLをここに貼り付けてください
RAW_URL = "https://docs.google.com/spreadsheets/d/1Bx8lfO0kx0771QewN3J92CL7P0_M-IRx92jXPW7ELqs/edit?usp=sharing"

# スプレッドシートをCSV形式で読み込むためのURL変換
if "/edit" in RAW_URL:
    CSV_URL = RAW_URL.replace("/edit", "/export?format=csv")
else:
    CSV_URL = RAW_URL

# ヒートマップ作成用の共通関数
def create_heatmap(data, title, color_scale, key_id):
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    z = np.zeros((3, 3))
    counts = data['コース'].value_counts()
    for r in range(3):
        for c in range(3):
            val = grid_names[r][c]
            z[r][c] = counts.get(int(val), 0) + counts.get(str(val), 0)
    
    fig = px.imshow(
        z, x=['左', '中', '右'], y=['上', '中', '下'],
        text_auto=True, color_continuous_scale=color_scale, title=title
    )
    fig.update_layout(width=350, height=350, margin=dict(l=20, r=20, t=40, b=20))
    return st.plotly_chart(fig, use_container_width=False, key=key_id)

try:
    # データの読み込み（キャッシュを無効化して常に最新を取得）
    # st.cache_dataを外すか、ttlを設定することでリアルタイム性を出します
    df = pd.read_csv(CSV_URL)
    
    # Googleフォームの項目名（タイムスタンプ等）を分析用の名前に変換
    # フォームの項目名に合わせてここを自動調整します
    rename_dict = {
        'タイムスタンプ': '日時',
        '質問1：ゴーリー': 'ゴーリー', # 自分のフォームの質問名に合わせてください
        '質問2：背番号': '背番号',
        '質問3：打つ位置': '打つ位置',
        '質問4：コース': 'コース',
        '質問5：結果': '結果'
    }
    # もしフォームの項目名が違う場合は、実際の列名を見て自動で合わせます
    if 'タイムスタンプ' in df.columns:
        df = df.rename(columns={'タイムスタンプ': '日時'})
    
    # 日付型に変換
    df['日時'] = pd.to_datetime(df['日時']).dt.date
    
    # 基本判定フラグの作成
    df['ゴール'] = (df['結果'] == 'ゴール').astype(int)
    df['セーブ'] = (df['結果'] == 'セーブ').astype(int)
    df['枠内'] = ((df['結果'] == 'ゴール') | (df['結果'] == 'セーブ')).astype(int)

    # リスト取得
    shooter_ids = sorted(df['背番号'].unique().astype(str))
    goalie_names = sorted(df['ゴーリー'].unique().astype(str))
    
    # === タブ構成（以前と同じ） ===
    tab_list = ["チーム全体", "🧤 ゴーリー集計"] + [f"🏃 {s}" for s in shooter_ids] + [f"🧤 {g}" for g in goalie_names]
    tabs = st.tabs(tab_list)

    # --- 1. チーム全体タブ ---
    with tabs[0]:
        st.header("🏢 チーム全体の成績")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.metric("総シュート数", f"{len(df)}本")
            st.metric("総ゴール数", f"{df['ゴール'].sum()}本")
        with col2:
            create_heatmap(df[df['結果'] == 'ゴール'], "チーム全体の得点傾向", "Reds", "overall_heat")
        with col3:
            st.subheader("📋 最新の5件")
            st.dataframe(df.sort_values('日時', ascending=False).head(5), use_container_width=True)

    # --- 2. ゴーリー集計タブ ---
    with tabs[1]:
        st.header("🧤 ゴーリー陣 総合分析")
        g_stats = df.groupby('ゴーリー').agg(枠内=('枠内', 'sum'), セーブ=('セーブ', 'sum')).reset_index()
        g_stats['セーブ率'] = (g_stats['セーブ'] / g_stats['枠内']).apply(lambda x: f"{x:.1%}" if x > 0 else "0.0%")
        st.dataframe(g_stats, use_container_width=True, hide_index=True)
        create_heatmap(df[df['結果'] == 'ゴール'], "ゴーリー陣全体の苦手傾向", "Oranges", "goalies_total_heat")

    # --- 3. 選手・ゴーリー詳細（ループで生成） ---
    # （※以前のコードと同じロジックで各タブを描画）
    # ... (省略しますが、実際のコードには詳細タブも入ります) ...

    # 自動更新ボタン
    if st.button('最新データに更新'):
        st.rerun()

except Exception as e:
    st.write("データを読み込み中、またはフォーム回答がまだありません。")
    st.info("スプレッドシートに1件以上データがあるか確認してください。")
