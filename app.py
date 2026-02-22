import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib import font_manager

# --- ★フォント設定の魔法 ---
# GitHubにアップロードしたフォントファイルを読み込む
font_path = 'msmincho.ttc'  # アップロードしたファイル名に合わせてください
font_prop = font_manager.FontProperties(fname=font_path)

st.set_page_config(page_title="シュート分析", layout="wide")
st.title("🥍 ラクロス部 シュート分析ダッシュボード")

try:
    df = pd.read_csv('FreeShootData.csv')
    df['ゴール判定'] = (df['結果'] == 'ゴール').astype(int)
    
    # === 絞り込みメニュー ===
    st.sidebar.header("検索フィルタ")
    player_list = ['全体'] + list(df['背番号'].unique())
    selected_player = st.sidebar.selectbox("選手を選択", player_list)
    
    if selected_player != '全体':
        df = df[df['背番号'] == selected_player]
        st.subheader(f"分析対象: {selected_player}")
    else:
        st.subheader("分析対象: 全体")

    # --- ① 数値まとめ ---
    col1, col2, col3 = st.columns(3)
    col1.metric("総シュート数", f"{len(df)}本")
    col2.metric("総ゴール数", f"{df['ゴール判定'].sum()}本")
    rate = df['ゴール判定'].sum() / len(df) if len(df) > 0 else 0
    col3.metric("ゴール決定率", f"{rate:.1%}")
    
    st.divider()
    
    # --- ② 表のサイズ調整（幅と高さを指定） ---
    st.header("シューター別成績")
    shooter_stats = df.groupby('背番号').agg(
        シュート数=('結果', 'count'),
        ゴール数=('ゴール判定', 'sum')
    )
    shooter_stats['決定率'] = (shooter_stats['ゴール数'] / shooter_stats['シュート数']).apply(lambda x: f"{x:.1%}")
    
    # 幅を500px、高さを300pxに制限して表示
    st.dataframe(shooter_stats, width=500, height=300)
    
    st.divider()
    
    # --- ③ ヒートマップ ---
    st.header("コース別ゴール数")
    goals = df[df['結果'] == 'ゴール']
    course_counts = goals['コース'].astype(str).value_counts()
    
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    heatmap_data = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            name = grid_names[i][j]
            if name in course_counts:
                heatmap_data[i][j] = course_counts[name]
                
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(heatmap_data, annot=True, cmap="Reds", fmt="g",
                xticklabels=['左', '中央', '右'], 
                yticklabels=['上', '中', '下'],
                linewidths=1, linecolor='gray', ax=ax)
    
    # グラフの各パーツに日本語フォントを適用
    plt.title('コース別ヒートマップ', fontproperties=font_prop)
    ax.set_xticklabels(['左', '中央', '右'], fontproperties=font_prop)
    ax.set_yticklabels(['上', '中', '下'], fontproperties=font_prop)
    
    st.pyplot(fig)

except FileNotFoundError:
    st.warning("CSVファイルが見つかりません。")
