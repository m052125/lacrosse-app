import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# フォント設定は標準に戻します
plt.rcParams['font.family'] = 'sans-serif'

st.set_page_config(page_title="Shot Analysis", layout="wide")
st.title("🥍 Lacrosse Shot Analysis")

try:
    df = pd.read_csv('FreeShootData.csv')
    df['Goal_Flag'] = (df['結果'] == 'ゴール').astype(int)
    
    # === 絞り込みメニュー ===
    st.sidebar.header("Filter")
    player_list = ['All'] + list(df['背番号'].unique())
    selected_player = st.sidebar.selectbox("Select Player", player_list)
    
    if selected_player != 'All':
        df = df[df['背番号'] == selected_player]
        st.subheader(f"Analysis: {selected_player}")
    else:
        st.subheader("Analysis: All Players")

    # --- ① スコア表示 ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Shots", f"{len(df)}")
    col2.metric("Total Goals", f"{df['Goal_Flag'].sum()}")
    rate = df['Goal_Flag'].sum() / len(df) if len(df) > 0 else 0
    col3.metric("Goal Rate", f"{rate:.1%}")
    
    st.divider()
    
    # --- ② 表のサイズ調整（ここを修正！） ---
    st.header("Shooter Stats")
    shooter_stats = df.groupby('背番号').agg(
        Shots=('結果', 'count'),
        Goals=('Goal_Flag', 'sum')
    )
    shooter_stats['Rate'] = (shooter_stats['Goals'] / shooter_stats['Shots']).apply(lambda x: f"{x:.1%}")
    
    # 列の幅を小さくし、高さを制限して表示します
    st.dataframe(shooter_stats, width=500, height=300)
    
    st.divider()
    
    # --- ③ ヒートマップ（英語化） ---
    st.header("Shot Course Heatmap")
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
                xticklabels=['Left', 'Center', 'Right'], 
                yticklabels=['Top', 'Middle', 'Bottom'],
                linewidths=1, linecolor='gray', ax=ax)
    st.pyplot(fig)

except FileNotFoundError:
    st.warning("Please place 'FreeShootData.csv' in the same folder.")
