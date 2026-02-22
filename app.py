import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import japanize_matplotlib

# Windowsの標準フォントを設定（文字化け対策）
# plt.rcParams['font.family'] = 'Meiryo'

st.set_page_config(page_title="フリシュー分析", layout="wide")
st.title("🥍 ラクロス部 フリシュー分析ダッシュボード")

try:
    df = pd.read_csv('FreeShootData.csv')
    df['ゴール判定'] = (df['結果'] == 'ゴール').astype(int)
    
    # === 🌟 新機能：画面左側に「絞り込みメニュー」を作る ===
    st.sidebar.header("🔍 絞り込み設定")
    
    # CSVの中にある背番号を自動で集めて、選択肢のリストを作る
    player_list = ['全体'] + list(df['背番号'].unique())
    selected_player = st.sidebar.selectbox("選手を選択してください", player_list)
    
    # 選んだ選手に合わせてデータを絞り込む
    if selected_player != '全体':
        # df（データ）を、選ばれた背番号のものだけに書き換える
        df = df[df['背番号'] == selected_player]
        st.subheader(f"📊 【{selected_player}】の成績")
    else:
        st.subheader("📊 【全体】の成績")
        
    # =========================================================

    # 絞り込まれたデータを使って計算（自動で数字が変わります！）
    col1, col2, col3 = st.columns(3)
    col1.metric("総ショット本数", f"{len(df)} 本")
    col2.metric("総ゴール数", f"{df['ゴール判定'].sum()} 本")
    rate = df['ゴール判定'].sum() / len(df) if len(df) > 0 else 0
    col3.metric("ショット率", f"{rate:.1%}")
    
    st.divider()
    
    # ヒートマップも、選んだ選手のデータだけで自動生成されます
    st.header("🔥 コース別 ゴール数")
    goals = df[df['結果'] == 'ゴール']
    course_counts = goals['コース'].astype(str).value_counts()
    
    grid_names = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
    heatmap_data = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            name = grid_names[i][j]
            if name in course_counts:
                heatmap_data[i][j] = course_counts[name]
                
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(heatmap_data, annot=True, cmap="Reds", fmt="g",
                xticklabels=['左', '中央', '右'], yticklabels=['上', '中', '下'],
                linewidths=1, linecolor='gray', ax=ax)
    st.pyplot(fig)

except FileNotFoundError:
    st.warning("⚠️ 同じフォルダに 'FreeShootData.csv' を置いてください！")