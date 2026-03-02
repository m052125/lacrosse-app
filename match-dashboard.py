import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from datetime import datetime

st.set_page_config(
page_title="京大女子ラクロス｜試合データ分析",
page_icon="🥍",
layout="wide"
)

# ========== カスタムCSS ==========

st.markdown("""

<style>
  .block-container { padding-top: 1.5rem; }
  .metric-card {
    background: #0d1526; border: 1px solid #1e2f4d;
    border-radius: 12px; padding: 16px 20px; text-align: center;
  }
  .metric-val { font-size: 2rem; font-weight: 900; line-height: 1; }
  .metric-lbl { font-size: 0.7rem; color: #8ba3c7; margin-top: 4px; letter-spacing: 0.05em; }
  .tool-tag {
    display: inline-block; background: #131f35; border: 1px solid #1e2f4d;
    border-radius: 20px; padding: 3px 10px; font-size: 0.7rem; color: #60a5fa; margin: 2px;
  }
  .section-badge {
    display: inline-block; background: rgba(37,99,235,0.15); color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.3); border-radius: 20px;
    padding: 3px 12px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    margin-bottom: 8px;
  }
</style>

""", unsafe_allow_html=True)

# ========== ユーティリティ ==========

COURSE_NAMES = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

def sec_to_mmss(sec):
if sec is None or sec == 0:
return "0:00"
m, s = divmod(int(sec), 60)
return f"{m}:{s:02d}"

def make_goalie_heatmap(shots, side, title, enemy_name="相手"):
grid_color = np.zeros((3, 3))
grid_text  = np.empty((3, 3), dtype=object)
for r in range(3):
for c in range(3):
idx = r * 3 + c
cell = [s for s in shots if s.get('side') == side and s.get(‘course’) == idx]
total = len(cell)
saves = len([s for s in cell if s.get(‘result’) == ‘save’])
goals = len([s for s in cell if s.get(‘result’) == ‘goal’])
if total > 0:
rate = saves / total * 100
grid_color[r, c] = rate
grid_text[r, c]  = f”{saves}/{total}<br>({rate:.0f}%)”
else:
grid_color[r, c] = 0
grid_text[r, c]  = “—”
team_label = “京大” if side == “kyoto” else enemy_name
fig = px.imshow(
grid_color,
labels=dict(x=“左右”, y=“高さ”, color=“セーブ率(%)”),
x=[‘左’, ‘中’, ‘右’], y=[‘上’, ‘中’, ‘下’],
color_continuous_scale=‘Blues’, zmin=0, zmax=100, title=title
)
fig.update_traces(text=grid_text, texttemplate=”%{text}”)
fig.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10), coloraxis_showscale=False)
return fig

def make_shot_course_heatmap(shots, side, result_filter=None, title=””, enemy_name=“相手”):
“”“コース別 被ショット数または得点数ヒートマップ”””
filtered = [s for s in shots if s.get(‘side’) == side]
if result_filter:
filtered = [s for s in filtered if s.get(‘result’) == result_filter]
grid = np.zeros((3, 3))
for s in filtered:
c = s.get(‘course’, -1)
if 0 <= c < 9:
grid[c // 3][c % 3] += 1
color_scale = ‘Reds’ if result_filter == ‘goal’ else ‘OrRd’
fig = px.imshow(
grid, x=[‘左’, ‘中’, ‘右’], y=[‘上’, ‘中’, ‘下’],
color_continuous_scale=color_scale, title=title,
text_auto=True
)
fig.update_layout(height=280, margin=dict(t=40, b=10, l=10, r=10), coloraxis_showscale=False)
return fig

# ========== サイドバー ==========

st.sidebar.image(“https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/120px-PNG_transparency_demonstration_1.png”, width=0)
st.sidebar.markdown(”## 🥍 試合データ分析”)
st.sidebar.markdown(”—”)

st.sidebar.markdown(”### 📁 JSONファイルをアップロード”)
uploaded_files = st.sidebar.file_uploader(
“各ツールからエクスポートしたJSONを選択（複数可）”,
type=[“json”],
accept_multiple_files=True,
help=“game_data・possession・gb_foul・draw・goalie の各JSONに対応”
)

# ========== JSON読み込み・分類 ==========

data = {
“game”:       None,
“possession”: None,
“gb_foul”:    None,
“draw”:       None,
“goalie”:     None,
}

tool_map = {
“GameDataTool”:    “game”,
“PossessionTool”:  “possession”,
“GBFoulTool”:      “gb_foul”,
“DrawTool”:        “draw”,
“GoalieTool”:      “goalie”,
}

loaded_tools = []
match_info   = {}

if uploaded_files:
for f in uploaded_files:
try:
d = json.load(f)
tool_str = d.get(“meta”, {}).get(“tool”, “”)
for key, val in tool_map.items():
if key in tool_str:
data[val] = d
loaded_tools.append(val)
if not match_info:
match_info = d.get(“meta”, {})
break
except Exception as e:
st.sidebar.error(f”読み込みエラー: {f.name}”)

# ロード状態表示

st.sidebar.markdown(”### 📦 ロード状態”)
status_icons = {
“game”:       (“📊”, “スコアシート/TO”),
“possession”: (“⏱”,  “ポゼッション”),
“gb_foul”:    (“🏃”, “GB・ファール”),
“draw”:       (“🥍”, “ドロー”),
“goalie”:     (“🥅”, “ゴーリー”),
}
for key, (icon, name) in status_icons.items():
ok = data[key] is not None
st.sidebar.markdown(
f”{‘✅’ if ok else ‘⬜’} {icon} {name}”,
)

# メニュー

st.sidebar.markdown(”—”)
menu = st.sidebar.radio(
“📌 表示する分析”,
[“🏠 試合サマリー”, “📊 スコア・ショット”, “🔄 ターンオーバー”,
“⏱ ポゼッション”, “🏃 GB・ファール”, “🥍 ドローデータ”, “🥅 ゴーリーデータ”]
)

# ========================================

# 試合情報ヘッダー

# ========================================

enemy_name = match_info.get(“enemy”, “相手”) if match_info else “相手”
match_date = match_info.get(“date”, “—”) if match_info else “—”

st.markdown(f”# 🥍 試合データ分析”)
if match_info:
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1:
st.markdown(f”### 京大 vs **{enemy_name}**”)
with col_h2:
st.markdown(f”📅 {match_date}”)
with col_h3:
for t in loaded_tools:
icon, name = status_icons[t]
st.markdown(f’<span class="tool-tag">{icon} {name}</span>’, unsafe_allow_html=True)

if not uploaded_files:
st.info(“← サイドバーから各ツールのJSONをアップロードしてください”)
st.markdown(”””
**対応ツール（5種）:**
- 📊 スコアシート＋ターンオーバー → `game_data_tool.html`
- ⏱ ポゼッション計測 → `possession_tool.html`
- 🏃 GB・ファール → `gb_foul_tool.html`
- 🥍 ドローデータ → `draw_tool.html`
- 🥅 ゴーリーデータ → `goalie_tool.html`

```
各ツールの「出力」タブ → 「JSON出力」ボタンでファイルをダウンロードできます。
""")
st.stop()
```

st.markdown(”—”)

# ========================================

# 🏠 試合サマリー

# ========================================

if menu == “🏠 試合サマリー”:
st.markdown(’<div class="section-badge">MATCH SUMMARY</div>’, unsafe_allow_html=True)
st.subheader(“試合サマリー”)

```
cols = st.columns(4)

# スコア
if data["game"]:
    shots = data["game"].get("shots", [])
    kyoto_score = len([s for s in shots if s["team"] == "kyoto" and s["result"] == "goal"])
    enemy_score = len([s for s in shots if s["team"] == "enemy" and s["result"] == "goal"])
    with cols[0]:
        st.metric("京大 得点", kyoto_score)
    with cols[1]:
        st.metric(f"{enemy_name} 得点", enemy_score)
    kyoto_shots = [s for s in shots if s["team"] == "kyoto"]
    enemy_shots = [s for s in shots if s["team"] == "enemy"]
    ks_rate = f"{kyoto_score/len(kyoto_shots)*100:.0f}%" if kyoto_shots else "—"
    es_rate = f"{enemy_score/len(enemy_shots)*100:.0f}%" if enemy_shots else "—"
    with cols[2]:
        st.metric("京大 シュート率", ks_rate, delta=f"{len(kyoto_shots)}本")
    with cols[3]:
        st.metric(f"{enemy_name} シュート率", es_rate, delta=f"{len(enemy_shots)}本")

st.markdown("---")
col_s1, col_s2, col_s3 = st.columns(3)

# ポゼッション
if data["possession"]:
    with col_s1:
        st.markdown("**⏱ ポゼッション**")
        by_q = data["possession"].get("of_possession", {}).get("by_q", [])
        total_sec = sum(q.get("total_sec", 0) for q in by_q)
        goal_cnt  = sum(q.get("goal_count", 0) for q in by_q)
        avg_secs  = [q.get("avg_goal_sec") for q in by_q if q.get("avg_goal_sec")]
        avg_goal  = sec_to_mmss(int(np.mean(avg_secs))) if avg_secs else "—"
        st.metric("OFポゼ合計", sec_to_mmss(total_sec))
        st.metric("得点平均時間", avg_goal)

# GB
if data["gb_foul"]:
    with col_s2:
        st.markdown("**🏃 GBゲット率**")
        gb_sum = data["gb_foul"].get("gb", {}).get("summary", {})
        k_gb = gb_sum.get("kyoto_get", 0)
        e_gb = gb_sum.get("enemy_get", 0)
        pct  = gb_sum.get("kyoto_pct", None)
        st.metric("京大 GBゲット", k_gb, delta=f"vs {enemy_name}: {e_gb}")
        st.metric("GBゲット率", f"{pct}%" if pct is not None else "—")

# ゴーリー
if data["goalie"]:
    with col_s3:
        st.markdown("**🥅 ゴーリー セーブ率**")
        gsummary = data["goalie"].get("summary", {})
        for side, label in [("kyoto", "京大G"), ("enemy", f"{enemy_name}G")]:
            s = gsummary.get(side, {})
            rate = s.get("save_rate_pct")
            saves = s.get("saves", 0)
            total = s.get("total_shots", 0)
            st.metric(f"{label} セーブ率", f"{rate}%" if rate is not None else "—",
                      delta=f"{saves}セーブ/{total}本")

# Q別スコア推移
if data["game"]:
    st.markdown("---")
    st.subheader("Q別スコア推移")
    shots = data["game"].get("shots", [])
    q_count = match_info.get("qCount", 4)
    q_rows = []
    k_cum, e_cum = 0, 0
    for q in range(1, q_count + 1):
        k = len([s for s in shots if s["q"] == q and s["team"] == "kyoto" and s["result"] == "goal"])
        e = len([s for s in shots if s["q"] == q and s["team"] == "enemy" and s["result"] == "goal"])
        k_cum += k; e_cum += e
        q_rows.append({"Q": f"Q{q}", "京大（累計）": k_cum, f"{enemy_name}（累計）": e_cum, "京大Q得点": k, f"{enemy_name}Q得点": e})
    q_df = pd.DataFrame(q_rows)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=q_df["Q"], y=q_df["京大（累計）"], name="京大", line=dict(color="#3b82f6", width=3), mode="lines+markers+text",
                             text=q_df["京大（累計）"], textposition="top center"))
    fig.add_trace(go.Scatter(x=q_df["Q"], y=q_df[f"{enemy_name}（累計）"], name=enemy_name, line=dict(color="#ef4444", width=3), mode="lines+markers+text",
                             text=q_df[f"{enemy_name}（累計）"], textposition="bottom center"))
    fig.update_layout(height=300, margin=dict(t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#8ba3c7", legend=dict(orientation="h"))
    fig.update_xaxes(gridcolor="#1e2f4d"); fig.update_yaxes(gridcolor="#1e2f4d")
    st.plotly_chart(fig, use_container_width=True)
```

# ========================================

# 📊 スコア・ショット

# ========================================

elif menu == “📊 スコア・ショット”:
st.markdown(’<div class="section-badge">SCORE & SHOTS</div>’, unsafe_allow_html=True)
st.subheader(“スコア・ショット分析”)

```
if not data["game"]:
    st.warning("スコアシートのJSONをアップロードしてください")
else:
    shots = data["game"].get("shots", [])
    q_count = match_info.get("qCount", 4)

    # 全体指標
    for team, label, color in [("kyoto", "京大", "#3b82f6"), ("enemy", enemy_name, "#ef4444")]:
        ts = [s for s in shots if s["team"] == team]
        goals = len([s for s in ts if s["result"] == "goal"])
        saves = len([s for s in ts if s["result"] == "save"])
        miss  = len([s for s in ts if s["result"] == "miss"])
        rate  = f"{goals/len(ts)*100:.0f}%" if ts else "—"
        st.markdown(f"#### {'🔵' if team=='kyoto' else '🔴'} {label}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("総ショット", len(ts))
        c2.metric("得点", goals)
        c3.metric("シュート率", rate)
        c4.metric("枠内率", f"{(goals+saves)/len(ts)*100:.0f}%" if ts else "—")

    st.markdown("---")

    # Q別集計テーブル
    st.subheader("Q別ショット内訳")
    q_rows = []
    for q in range(1, q_count + 1):
        for team, label in [("kyoto", "京大"), ("enemy", enemy_name)]:
            ts = [s for s in shots if s["q"] == q and s["team"] == team]
            if not ts: continue
            goals = len([s for s in ts if s["result"] == "goal"])
            saves = len([s for s in ts if s["result"] == "save"])
            miss  = len([s for s in ts if s["result"] == "miss"])
            rate  = f"{goals/len(ts)*100:.0f}%" if ts else "—"
            q_rows.append({"Q": f"Q{q}", "チーム": label, "ショット": len(ts),
                            "得点": goals, "セーブ": saves, "枠外": miss, "シュート率": rate})
    if q_rows:
        st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 攻め方集計
    st.subheader("攻め方別集計（京大）")
    k_shots = [s for s in shots if s["team"] == "kyoto" and s.get("attack")]
    if k_shots:
        attack_df = pd.DataFrame(k_shots)
        attack_stats = attack_df.groupby("attack").agg(
            ショット数=("result", "count"),
            得点=("result", lambda x: (x == "goal").sum()),
        ).reset_index()
        attack_stats["決定率"] = (attack_stats["得点"] / attack_stats["ショット数"] * 100).round(1).astype(str) + "%"
        attack_stats = attack_stats.sort_values("ショット数", ascending=False)

        col_at1, col_at2 = st.columns([1, 1])
        with col_at1:
            st.dataframe(attack_stats, use_container_width=True, hide_index=True)
        with col_at2:
            fig = px.pie(attack_stats, values="ショット数", names="attack",
                         title="攻め方の分布", hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(height=320, margin=dict(t=40, b=0), paper_bgcolor="rgba(0,0,0,0)", font_color="#8ba3c7")
            st.plotly_chart(fig, use_container_width=True)

    # CL成功率
    cl = data["game"].get("clearance", {})
    if cl:
        st.markdown("---")
        st.subheader("クリア成功率（Q別）")
        cl_rows = []
        for q_str, v in cl.items():
            ok = v.get("ok", 0); ng = v.get("ng", 0)
            total = ok + ng
            cl_rows.append({"Q": f"Q{q_str}", "成功": ok, "失敗": ng,
                             "成功率": f"{ok/total*100:.0f}%" if total > 0 else "—"})
        if cl_rows:
            st.dataframe(pd.DataFrame(cl_rows), use_container_width=True, hide_index=True)
```

# ========================================

# 🔄 ターンオーバー

# ========================================

elif menu == “🔄 ターンオーバー”:
st.markdown(’<div class="section-badge">TURNOVER</div>’, unsafe_allow_html=True)
st.subheader(“ターンオーバー分析”)

```
if not data["game"]:
    st.warning("スコアシートのJSONをアップロードしてください")
else:
    tos = data["game"].get("turnovers", [])
    q_count = match_info.get("qCount", 4)

    if not tos:
        st.info("ターンオーバーデータがありません")
    else:
        kyoto_to = [t for t in tos if t["side"] == "kyoto"]
        enemy_to = [t for t in tos if t["side"] == "enemy"]

        c1, c2, c3 = st.columns(3)
        c1.metric("京大 奪われたTO", len(kyoto_to))
        c2.metric("京大 奪ったTO", len(enemy_to))
        c3.metric("TOバランス", f"{len(enemy_to) - len(kyoto_to):+d}", delta_color="normal")

        st.markdown("---")

        col_t1, col_t2 = st.columns(2)
        CAUSES = ['PC', 'キープ', 'ファール', 'インター', 'ショット', 'チェイス', 'その他']

        with col_t1:
            st.subheader("原因別（京大が奪われた）")
            if kyoto_to:
                cause_df = pd.DataFrame(kyoto_to)["cause"].value_counts().reset_index()
                cause_df.columns = ["原因", "回数"]
                fig = px.bar(cause_df, x="原因", y="回数", color="回数",
                             color_continuous_scale="Reds", title="京大 奪われたTO原因")
                fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#8ba3c7", showlegend=False, coloraxis_showscale=False)
                fig.update_xaxes(gridcolor="#1e2f4d"); fig.update_yaxes(gridcolor="#1e2f4d")
                st.plotly_chart(fig, use_container_width=True)

        with col_t2:
            st.subheader("原因別（京大が奪った）")
            if enemy_to:
                cause_df2 = pd.DataFrame(enemy_to)["cause"].value_counts().reset_index()
                cause_df2.columns = ["原因", "回数"]
                fig2 = px.bar(cause_df2, x="原因", y="回数", color="回数",
                              color_continuous_scale="Blues", title="京大 奪ったTO原因")
                fig2.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   font_color="#8ba3c7", showlegend=False, coloraxis_showscale=False)
                fig2.update_xaxes(gridcolor="#1e2f4d"); fig2.update_yaxes(gridcolor="#1e2f4d")
                st.plotly_chart(fig2, use_container_width=True)

        # Q別TO推移
        st.markdown("---")
        st.subheader("Q別TOバランス")
        q_rows = []
        for q in range(1, q_count + 1):
            k = len([t for t in kyoto_to if t["q"] == q])
            e = len([t for t in enemy_to if t["q"] == q])
            q_rows.append({"Q": f"Q{q}", "京大奪われ": k, "京大奪った": e, "差": e - k})
        q_df = pd.DataFrame(q_rows)
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=q_df["Q"], y=q_df["京大奪われ"], name="奪われ", marker_color="#ef4444"))
        fig3.add_trace(go.Bar(x=q_df["Q"], y=q_df["京大奪った"], name="奪った", marker_color="#3b82f6"))
        fig3.update_layout(barmode="group", height=300, paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)", font_color="#8ba3c7",
                            legend=dict(orientation="h"))
        fig3.update_xaxes(gridcolor="#1e2f4d"); fig3.update_yaxes(gridcolor="#1e2f4d")
        st.plotly_chart(fig3, use_container_width=True)
```

# ========================================

# ⏱ ポゼッション

# ========================================

elif menu == “⏱ ポゼッション”:
st.markdown(’<div class="section-badge">POSSESSION</div>’, unsafe_allow_html=True)
st.subheader(“ポゼッション分析”)

```
if not data["possession"]:
    st.warning("ポゼッションのJSONをアップロードしてください")
else:
    pd_data = data["possession"]
    q_count = match_info.get("qCount", 4)

    # OFポゼ
    st.subheader("⚔️ OFポゼッション")
    of_by_q = pd_data.get("of_possession", {}).get("by_q", [])
    if of_by_q:
        of_rows = []
        for q in of_by_q:
            if q["set_count"] == 0: continue
            of_rows.append({
                "Q": f"Q{q['q']}",
                "セット数": q["set_count"],
                "OF合計": sec_to_mmss(q["total_sec"]),
                "得点": q["goal_count"],
                "TO": q["to_count"],
                "得点平均時間": sec_to_mmss(q["avg_goal_sec"]) if q.get("avg_goal_sec") else "—",
            })
        st.dataframe(pd.DataFrame(of_rows), use_container_width=True, hide_index=True)

        # OFポゼ時間の棒グラフ
        fig_of = px.bar(
            pd.DataFrame(of_rows), x="Q", y=[row["OF合計"] for row in of_rows],
            title="Q別 OFポゼッション合計時間"
        )
        # 秒数で棒グラフ
        of_sec_rows = [{"Q": f"Q{q['q']}", "OFポゼ(秒)": q["total_sec"],
                         "得点": q["goal_count"], "TO": q["to_count"]}
                       for q in of_by_q if q["set_count"] > 0]
        fig_of2 = px.bar(pd.DataFrame(of_sec_rows), x="Q", y="OFポゼ(秒)",
                          color="得点", color_continuous_scale="Blues",
                          title="Q別 OFポゼ合計（秒）と得点数")
        fig_of2.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#8ba3c7", coloraxis_showscale=False)
        fig_of2.update_xaxes(gridcolor="#1e2f4d"); fig_of2.update_yaxes(gridcolor="#1e2f4d")
        st.plotly_chart(fig_of2, use_container_width=True)

    st.markdown("---")

    # CLRDポゼ
    st.subheader("🛡️ CLRDポゼッション（京大 vs 相手）")
    cl_by_q = pd_data.get("clrd_possession", {}).get("by_q", [])
    if cl_by_q:
        cl_rows = []
        for q in cl_by_q:
            cl_rows.append({
                "Q": f"Q{q['q']}",
                "京大(秒)": q["kyoto_sec"],
                f"{enemy_name}(秒)": q["enemy_sec"],
                "京大%": f"{q['kyoto_pct']}%",
            })
        cl_df = pd.DataFrame(cl_rows)
        st.dataframe(cl_df, use_container_width=True, hide_index=True)

        fig_cl = go.Figure()
        fig_cl.add_trace(go.Bar(x=cl_df["Q"], y=cl_df["京大(秒)"],   name="京大",       marker_color="#3b82f6"))
        fig_cl.add_trace(go.Bar(x=cl_df["Q"], y=cl_df[f"{enemy_name}(秒)"], name=enemy_name, marker_color="#ef4444"))
        fig_cl.update_layout(barmode="stack", height=300, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", font_color="#8ba3c7",
                              title="Q別 CLRDポゼッション（積み上げ）",
                              legend=dict(orientation="h"))
        fig_cl.update_xaxes(gridcolor="#1e2f4d"); fig_cl.update_yaxes(gridcolor="#1e2f4d")
        st.plotly_chart(fig_cl, use_container_width=True)
```

# ========================================

# 🏃 GB・ファール

# ========================================

elif menu == “🏃 GB・ファール”:
st.markdown(’<div class="section-badge">GB & FOUL</div>’, unsafe_allow_html=True)
st.subheader(“GB・ファール分析”)

```
if not data["gb_foul"]:
    st.warning("GB・ファールのJSONをアップロードしてください")
else:
    gb_data = data["gb_foul"]
    gb_records = gb_data.get("gb", {}).get("records", [])
    foul_records = gb_data.get("fouls", {}).get("records", [])
    gb_sum = gb_data.get("gb", {}).get("summary", {})

    # GB指標
    st.subheader("🏃 GBゲット率")
    c1, c2, c3 = st.columns(3)
    c1.metric("京大 GBゲット", gb_sum.get("kyoto_get", 0))
    c2.metric(f"{enemy_name} GBゲット", gb_sum.get("enemy_get", 0))
    c3.metric("京大 ゲット率", f"{gb_sum.get('kyoto_pct', '—')}%" if gb_sum.get("kyoto_pct") is not None else "—")

    if gb_records:
        # 場所別
        st.markdown("---")
        st.subheader("場所別 GBゲット")
        loc_data = gb_sum.get("by_location", [])
        if loc_data:
            loc_df = pd.DataFrame(loc_data)
            loc_df["場所"] = loc_df["loc"].map({"self": "自陣", "center": "センター", "enemy": "敵陣"})
            loc_df["合計"] = loc_df["kyoto"] + loc_df["enemy"]
            loc_df["京大率"] = (loc_df["kyoto"] / loc_df["合計"] * 100).round(1).astype(str) + "%"
            loc_df = loc_df.rename(columns={"kyoto": "京大", "enemy": enemy_name})
            st.dataframe(loc_df[["場所", "京大", enemy_name, "合計", "京大率"]], use_container_width=True, hide_index=True)

            fig_loc = go.Figure()
            fig_loc.add_trace(go.Bar(x=loc_df["場所"], y=loc_df["京大"],       name="京大",       marker_color="#3b82f6"))
            fig_loc.add_trace(go.Bar(x=loc_df["場所"], y=loc_df[enemy_name],   name=enemy_name,   marker_color="#ef4444"))
            fig_loc.update_layout(barmode="group", height=300, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", font_color="#8ba3c7",
                                  legend=dict(orientation="h"))
            fig_loc.update_xaxes(gridcolor="#1e2f4d"); fig_loc.update_yaxes(gridcolor="#1e2f4d")
            st.plotly_chart(fig_loc, use_container_width=True)

    # ファール
    if foul_records:
        st.markdown("---")
        st.subheader("🚩 ファール分析")
        foul_sum = gb_data.get("fouls", {}).get("summary", {})
        c1, c2 = st.columns(2)
        c1.metric("総ファール数", foul_sum.get("total", 0))
        c2.metric("ファール選手数", len(foul_sum.get("by_player", {})))

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown("**種別内訳**")
            by_type = foul_sum.get("by_type", {})
            if by_type:
                type_df = pd.DataFrame(list(by_type.items()), columns=["ファール名", "回数"]).sort_values("回数", ascending=False)
                fig_ft = px.bar(type_df, x="ファール名", y="回数", color="回数",
                                color_continuous_scale="YlOrRd")
                fig_ft.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                     font_color="#8ba3c7", coloraxis_showscale=False)
                fig_ft.update_xaxes(gridcolor="#1e2f4d"); fig_ft.update_yaxes(gridcolor="#1e2f4d")
                st.plotly_chart(fig_ft, use_container_width=True)

        with col_f2:
            st.markdown("**選手別ファール数**")
            by_player = foul_sum.get("by_player", {})
            if by_player:
                player_df = pd.DataFrame(list(by_player.items()), columns=["背番号", "回数"]).sort_values("回数", ascending=False)
                player_df["背番号"] = "#" + player_df["背番号"].astype(str)
                st.dataframe(player_df, use_container_width=True, hide_index=True)
```

# ========================================

# 🥍 ドローデータ

# ========================================

elif menu == “🥍 ドローデータ”:
st.markdown('<div class="section-badge">DRAW DATA</div>’, unsafe_allow_html=True)
st.subheader(“ドローデータ分析”)

```
if not data["draw"]:
    st.warning("ドローデータのJSONをアップロードしてください")
else:
    draws = data["draw"].get("draws", [])
    summary = data["draw"].get("summary", {})
    q_count = match_info.get("qCount", 4)

    if not draws:
        st.info("ドローデータがありません")
    else:
        # 全体指標
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("総ドロー数", summary.get("total", 0))
        c2.metric("京大ゲット", summary.get("got", 0))
        c3.metric("相手ゲット", summary.get("lost", 0))
        rate = summary.get("get_rate_pct")
        c4.metric("ゲット率", f"{rate}%" if rate is not None else "—")

        st.markdown("---")

        # Q別
        st.subheader("Q別ドローゲット率")
        q_rows = []
        for q in range(1, q_count + 1):
            qd = [d for d in draws if d["q"] == q]
            if not qd: continue
            got  = len([d for d in qd if d["result"] == "ok"])
            lost = len([d for d in qd if d["result"] == "ng"])
            foul = len([d for d in qd if d["result"] == "foul"])
            total = got + lost
            q_rows.append({"Q": f"Q{q}", "ドロー": len(qd), "京大○": got, "相手○": lost,
                            "ファール": foul, "ゲット率": f"{got/total*100:.0f}%" if total > 0 else "—"})
        if q_rows:
            st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

        # ドロワー別
        st.markdown("---")
        st.subheader("ドロワー別ゲット率")
        drawer_stats = {}
        for d in draws:
            key = d.get("drawer") or "不明"
            if key not in drawer_stats:
                drawer_stats[key] = {"ok": 0, "ng": 0, "foul": 0}
            drawer_stats[key][d["result"]] += 1

        dr_rows = []
        for num, cnt in sorted(drawer_stats.items(), key=lambda x: -(x[1]["ok"]+x[1]["ng"])):
            t = cnt["ok"] + cnt["ng"]
            rate = f"{cnt['ok']/t*100:.0f}%" if t > 0 else "—"
            dr_rows.append({"ドロワー": f"#{num}", "ドロー数": t + cnt["foul"],
                             "ゲット": cnt["ok"], "失敗": cnt["ng"],
                             "ファール": cnt["foul"], "ゲット率": rate})

        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            st.dataframe(pd.DataFrame(dr_rows), use_container_width=True, hide_index=True)
        with col_d2:
            if dr_rows:
                dr_df = pd.DataFrame(dr_rows)
                fig_dr = px.bar(dr_df, x="ドロワー", y=["ゲット", "失敗"],
                                barmode="stack", color_discrete_map={"ゲット": "#22c55e", "失敗": "#ef4444"},
                                title="ドロワー別ゲット/失敗")
                fig_dr.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                     font_color="#8ba3c7", legend=dict(orientation="h"))
                fig_dr.update_xaxes(gridcolor="#1e2f4d"); fig_dr.update_yaxes(gridcolor="#1e2f4d")
                st.plotly_chart(fig_dr, use_container_width=True)

        # 取り方
        st.markdown("---")
        st.subheader("取り方別集計")
        way_counts = {}
        for d in draws:
            w = d.get("getWay")
            if w: way_counts[w] = way_counts.get(w, 0) + 1
        if way_counts:
            way_df = pd.DataFrame(list(way_counts.items()), columns=["取り方", "回数"]).sort_values("回数", ascending=False)
            fig_way = px.pie(way_df, values="回数", names="取り方", hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Purples_r)
            fig_way.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", font_color="#8ba3c7")
            st.plotly_chart(fig_way, use_container_width=True)
```

# ========================================

# 🥅 ゴーリーデータ

# ========================================

elif menu == "🥅 ゴーリーデータ":
st.markdown('<div class="section-badge">GOALIE DATA</div>', unsafe_allow_html=True)
st.subheader("ゴーリーデータ分析")


if not data["goalie"]:
    st.warning("ゴーリーデータのJSONをアップロードしてください")
else:
    shots   = data["goalie"].get("shots", [])
    goalies = data["goalie"].get("goalies", {})
    summary = data["goalie"].get("summary", {})
    q_count = match_info.get("qCount", 4)

    if not shots:
        st.info("ゴーリーデータがありません")
    else:
        # 全体指標
        for side, label, color in [("kyoto", "🔵 京大G", "#3b82f6"), ("enemy", f"🔴 {enemy_name}G", "#ef4444")]:
            s = summary.get(side, {})
            c1, c2, c3, c4 = st.columns(4)
            st.markdown(f"#### {label}")
            c1.metric("被ショット", s.get("total_shots", 0))
            c2.metric("失点", s.get("goals", 0))
            c3.metric("セーブ", s.get("saves", 0))
            save_rate = s.get("save_rate_pct")
            c4.metric("セーブ率", f"{save_rate}%" if save_rate is not None else "—")

        st.markdown("---")

        # ヒートマップ
        st.subheader("コース別 セーブ率ヒートマップ")
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            fig_k = make_goalie_heatmap(shots, "kyoto", f"京大G — コース別セーブ率", enemy_name)
            st.plotly_chart(fig_k, use_container_width=True)
        with col_h2:
            fig_e = make_goalie_heatmap(shots, "enemy", f"{enemy_name}G — コース別セーブ率", enemy_name)
            st.plotly_chart(fig_e, use_container_width=True)

        st.markdown("---")

        # 被ショット分布
        st.subheader("被ショットコース分布")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig_ks = make_shot_course_heatmap(shots, "kyoto", title=f"京大G — 被ショット数")
            st.plotly_chart(fig_ks, use_container_width=True)
        with col_s2:
            fig_es = make_shot_course_heatmap(shots, "enemy", title=f"{enemy_name}G — 被ショット数")
            st.plotly_chart(fig_es, use_container_width=True)

        # Q別テーブル
        st.markdown("---")
        st.subheader("Q別セーブ率")
        q_rows = []
        for q in range(1, q_count + 1):
            for side, label in [("kyoto", "京大"), ("enemy", enemy_name)]:
                qs = [s for s in shots if s["q"] == q and s["side"] == side]
                if not qs: continue
                goal = len([s for s in qs if s["result"] == "goal"])
                save = len([s for s in qs if s["result"] == "save"])
                miss = len([s for s in qs if s["result"] == "miss"])
                total = goal + save
                rate = f"{save/total*100:.0f}%" if total > 0 else "—"
                q_rows.append({"Q": f"Q{q}", "G": label, "被ショット": len(qs),
                               "失点": goal, "セーブ": save, "枠外": miss, "セーブ率": rate})
        if q_rows:
            st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

        # ゴーリー別
        st.markdown("---")
        st.subheader("ゴーリー別集計")
        g_rows = []
        for side, label in [("kyoto", "京大"), ("enemy", enemy_name)]:
            for g in goalies.get(side, []):
                g_shots = [s for s in shots if s["side"] == side and s.get("goalieNum") == g["num"]]
                goal = len([s for s in g_shots if s["result"] == "goal"])
                save = len([s for s in g_shots if s["result"] == "save"])
                total = goal + save
                rate = f"{save/total*100:.0f}%" if total > 0 else "—"
                g_rows.append({"チーム": label, "背番号": f"#{g['num']}", "利き腕": g["hand"],
                               "出場Q": f"Q{g['fromQ']}〜", "被ショット": len(g_shots),
                               "失点": goal, "セーブ率": rate})
        if g_rows:
            st.dataframe(pd.DataFrame(g_rows), use_container_width=True, hide_index=True)
