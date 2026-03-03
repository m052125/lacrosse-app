import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import boto3
from io import StringIO

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="🐬 練習データ分析ダッシュボード",
    layout="wide",
    page_icon="🐬"
)

# ==========================================
# ★ AWS S3 設定（ご自身のものに書き換えてください）
# ==========================================
S3_BUCKET   = "your-bucket-name"
S3_KEY_FS   = "practice/freeshot.csv"   # フリシューCSV
S3_KEY_1on1 = "practice/1on1.csv"       # 1on1 CSV
S3_KEY_6on6_SHOT = "practice/6on6_shot.csv"
S3_KEY_6on6_TO   = "practice/6on6_to.csv"
S3_KEY_6on6_GB   = "practice/6on6_gb.csv"
S3_KEY_6on6_MISS = "practice/6on6_miss.csv"

AWS_REGION = "ap-northeast-1"

# ==========================================
# S3読み込み共通関数
# ==========================================
@st.cache_data(ttl=30)
def load_csv_from_s3(bucket: str, key: str) -> pd.DataFrame:
    try:
        s3  = boto3.client("s3", region_name=AWS_REGION)
        obj = s3.get_object(Bucket=bucket, Key=key)
        df  = pd.read_csv(StringIO(obj["Body"].read().decode("utf-8")))
        return df
    except s3.exceptions.NoSuchKey:
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ {key} の読み込みに失敗しました: {e}")
        return pd.DataFrame()

# timestamp→date変換共通
def prep_timestamp(df: pd.DataFrame, col: str = "timestamp") -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df["日付"] = df[col].dt.date
    return df

# ==========================================
# 期間フィルター共通
# ==========================================
def date_filter(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    if ts_col not in df.columns or df.empty:
        return df
    df = prep_timestamp(df, ts_col)
    valid = df.dropna(subset=[ts_col])
    if valid.empty:
        return df
    mn = valid[ts_col].min().date()
    mx = valid[ts_col].max().date()
    rng = st.sidebar.date_input("📅 期間フィルター", value=(mn, mx), min_value=mn, max_value=mx)
    if isinstance(rng, tuple) and len(rng) == 2:
        s = pd.to_datetime(rng[0]); e = pd.to_datetime(rng[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df = df[(df[ts_col] >= s) & (df[ts_col] <= e)].copy()
    return df

# ==========================================
# ヒートマップ関数群（フリシュー・1on1共通）
# ==========================================

def heatmap_area_freeshot(df, mode="shooter", title=""):
    """2×5 エリアヒートマップ（フリシュー用）"""
    area_map = {
        '1':(0,0),'2':(0,1),'3':(0,2),'4':(0,3),'5':(0,4),
        '6':(1,0),'7':(1,1),'8':(1,2),'9':(1,3),'10':(1,4)
    }
    z = np.zeros((2,5)); text = np.full((2,5),"",dtype=object)
    df = df.copy()
    df["area_c"] = pd.to_numeric(df.get("area", pd.Series(dtype=str)), errors="coerce").fillna(0).astype(int).astype(str)
    for an,(r,c) in area_map.items():
        ad = df[df["area_c"]==an]; tot=len(ad)
        if tot>0:
            if mode=="shooter":
                suc=ad["result"].eq("ゴール").sum(); rt=suc/tot*100
                text[r][c]=f"[{an}]<br>{suc}/{tot}<br>({rt:.1f}%)"
            else:
                ot=ad[ad["result"].isin(["ゴール","セーブ"])]; rt=(ot["result"].eq("セーブ").sum()/len(ot)*100) if len(ot)>0 else 0
                text[r][c]=f"[{an}]<br>{ot['result'].eq('セーブ').sum()}/{len(ot)}<br>({rt:.1f}%)"
            z[r][c]=rt
        else:
            text[r][c]=f"[{an}]<br>0/0<br>(0.0%)"
    fig=px.imshow(z,x=["左2","左1","中央","右1","右2"],y=["上段","下段"],text_auto=False,
                  color_continuous_scale="Reds" if mode=="shooter" else "Blues",title=title)
    fig.update_traces(text=text,texttemplate="%{text}")
    fig.update_layout(width=700,height=320)
    return fig

def heatmap_course_3x3(df, result_col="result", target_val="ゴール", base_filter=None,
                       cscale="Reds", clabel="決定率(%)", title=""):
    """3×3 コースヒートマップ"""
    mapping={"1":(0,0),"2":(0,1),"3":(0,2),"4":(1,0),"5":(1,1),"6":(1,2),"7":(2,0),"8":(2,1),"9":(2,2)}
    gc=np.zeros((3,3)); gt=np.empty((3,3),dtype=object)
    df=df.copy()
    if base_filter:
        df=df[base_filter(df)]
    df["course_c"]=pd.to_numeric(df.get("course",pd.Series(dtype=str)),errors="coerce").fillna(0).astype(int).astype(str)
    for cn,(r,c) in mapping.items():
        cd=df[df["course_c"]==cn]; tot=len(cd)
        if tot>0:
            suc=cd[result_col].eq(target_val).sum(); rt=suc/tot*100
            gc[r,c]=rt; gt[r,c]=f"{suc}/{tot}<br>({rt:.1f}%)"
        else:
            gc[r,c]=0; gt[r,c]="0/0<br>(0.0%)"
    fig=px.imshow(gc,x=["左","中","右"],y=["上","中","下"],color_continuous_scale=cscale,
                  labels=dict(x="左右",y="位置",color=clabel),title=title)
    fig.update_traces(text=gt,texttemplate="%{text}")
    fig.update_layout(width=430,height=430)
    return fig

def heatmap_shot_pos_1on1(df, mode="AT", title=""):
    """2×5 ショット位置ヒートマップ（1on1用）"""
    mapping={"1":(0,0),"2":(0,1),"3":(0,2),"4":(0,3),"5":(0,4),"6":(1,0),"7":(1,1),"8":(1,2),"9":(1,3),"10":(1,4)}
    gc=np.zeros((2,5)); gt=np.empty((2,5),dtype=object)
    shot_df=df[df.get("endType","")=="ショット"].copy() if "endType" in df.columns else df.copy()
    shot_df["sp_c"]=pd.to_numeric(shot_df.get("shotPos",pd.Series(dtype=str)),errors="coerce").fillna(0).astype(int).astype(str)
    cscale="Reds" if mode in("AT","DF") else "Blues"; clabel="決定率(%)" if mode=="AT" else ("失点率(%)" if mode=="DF" else "セーブ率(%)")
    for ln,(r,c) in mapping.items():
        ld=shot_df[shot_df["sp_c"]==ln]; tot=len(ld)
        if tot>0:
            suc=ld["result"].eq("ゴール").sum() if mode in("AT","DF") else ld["result"].eq("セーブ").sum()
            rt=suc/tot*100; gc[r,c]=rt; gt[r,c]=f"[{ln}]<br>{suc}/{tot}<br>({rt:.1f}%)"
        else:
            gc[r,c]=0; gt[r,c]=f"[{ln}]<br>0/0<br>(0.0%)"
    fig=px.imshow(gc,x=["1","2","3","4","5"],y=["上段","下段"],color_continuous_scale=cscale,
                  labels=dict(x="左右",y="段",color=clabel),title=title)
    fig.update_traces(text=gt,texttemplate="%{text}")
    fig.update_layout(width=700,height=320)
    return fig

def heatmap_origin_ratio(df, mode="AT", title=""):
    """起点別 被ショット率/セーブ率マップ（1on1 DF/G用）"""
    mapping={"左上":(0,0),"センター":(0,1),"右上":(0,2),"左横":(1,0),"右横":(1,2),"左裏":(2,0),"右裏":(2,2)}
    gc=np.full((3,3),np.nan); gt=np.full((3,3),"",dtype=object)
    df=df.copy(); df["origin_c"]=df.get("origin",pd.Series(dtype=str)).astype(str).str.strip()
    shot_df=df[df.get("endType","")=="ショット"] if "endType" in df.columns else df
    for orig,(r,c) in mapping.items():
        od=df[df["origin_c"]==orig]; tot=len(od)
        if tot>0:
            if mode=="DF":
                suc=len(od[od.get("endType","")=="ショット"]) if "endType" in od.columns else 0
            else:
                sd=shot_df[shot_df["origin_c"]==orig]; suc=sd["result"].eq("セーブ").sum(); tot=len(sd)
            rt=suc/tot*100 if tot>0 else 0; gc[r,c]=rt; gt[r,c]=f"{suc}/{tot}<br>({rt:.1f}%)"
        else:
            gc[r,c]=0; gt[r,c]="0/0<br>(0.0%)"
    cscale="Reds" if mode=="DF" else "Blues"
    fig=px.imshow(gc,x=["左","中","右"],y=["上","横","裏"],color_continuous_scale=cscale,
                  title=title)
    fig.update_traces(text=gt,texttemplate="%{text}")
    fig.update_layout(width=430,height=430)
    return fig

# ==========================================
# メインナビゲーション
# ==========================================
st.sidebar.markdown("## 🐬 練習分析")
practice_mode = st.sidebar.radio("練習種目", ["🥍 フリーシュー", "⚔️ 1on1", "🏟️ 6on6"])
st.sidebar.markdown("---")

# ==========================================
# ① フリーシュー分析
# ==========================================
if practice_mode == "🥍 フリーシュー":
    st.title("🥍 フリーシュー 練習分析")

    raw_df = load_csv_from_s3(S3_BUCKET, S3_KEY_FS)
    if raw_df.empty:
        st.warning("データがまだありません。フリシュー記録ツールからデータを送信してください。")
        st.stop()

    # 列名整合（Lambda送信JSON → CSVの列名に合わせる）
    col_rename = {"pos":"打つ位置","area":"シュートエリア","target":"コース","result":"結果","shooter":"背番号","goalie":"ゴーリー"}
    raw_df = raw_df.rename(columns={k:v for k,v in col_rename.items() if k in raw_df.columns})
    if "背番号" in raw_df.columns:
        raw_df["背番号"] = raw_df["背番号"].astype(str).apply(lambda x: x if x.startswith("#") else "#"+x)
    raw_df["ゴール"] = (raw_df.get("結果","")=="ゴール").astype(int)
    raw_df["セーブ"] = (raw_df.get("結果","")=="セーブ").astype(int)
    raw_df["枠内"]   = raw_df.get("結果","").isin(["ゴール","セーブ"]).astype(int)

    df = date_filter(raw_df, "timestamp")

    # ── 分析モード切替 ──
    st.sidebar.header("🔍 フリシュー分析モード")
    mode = st.sidebar.radio("表示モード",["🏢 チーム全体","🔴 シューター分析","🔵 ゴーリー分析","📊 全データ"])

    if mode == "🏢 チーム全体":
        st.header("🏢 チーム全体の成績")
        c1,c2,c3 = st.columns(3)
        tot=len(df); goals=df["ゴール"].sum(); rate=(goals/tot*100) if tot>0 else 0
        on_t=df["枠内"].sum(); sv=df["セーブ"].sum(); sr=(sv/on_t*100) if on_t>0 else 0
        c1.metric("総シュート数",f"{tot} 本"); c2.metric("ゴール(決定率)",f"{goals} 本 ({rate:.1f}%)"); c3.metric("チーム全体セーブ率",f"{sr:.1f}%")
        st.divider()
        st.subheader("📍 チーム得点傾向")
        ca,cb=st.columns([3,2])
        with ca: st.plotly_chart(heatmap_area_freeshot(df,"shooter","エリア別 決定率"),use_container_width=True)
        with cb: st.plotly_chart(heatmap_course_3x3(df,title="コース別 決定率"),use_container_width=True)

    elif mode == "🔴 シューター分析":
        s_list=["全体"]+sorted(df.get("背番号",pd.Series()).dropna().unique().tolist())
        sel=st.sidebar.selectbox("シューターを選択",s_list)
        s_df=df.copy() if sel=="全体" else df[df["背番号"]==sel].copy()
        st.header(f"👤 シューター: {sel} の分析結果")
        c1,c2,c3=st.columns(3)
        tot=len(s_df); g=s_df["ゴール"].sum(); r=(g/tot*100) if tot>0 else 0
        c1.metric("総シュート数",tot); c2.metric("ゴール数",g); c3.metric("決定率",f"{r:.1f}%")
        st.divider()
        ca,cb=st.columns([3,2])
        with ca:
            st.subheader("📈 決定率の推移")
            if "日付" in s_df.columns:
                trend=s_df.groupby("日付").agg(率=("ゴール","mean")).reset_index()
                fig=px.line(trend,x="日付",y="率",markers=True,title="日別の決定率変化")
                fig.update_layout(yaxis=dict(tickformat=".0%",range=[-0.1,1.1]))
                st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.subheader("📊 結果の内訳")
            if "結果" in s_df.columns:
                st.plotly_chart(px.pie(s_df,names="結果",hole=0.4,title="シュート結果"),use_container_width=True)
        st.divider()
        st.subheader("📍 エリア・コース別 決定率")
        ca2,cb2=st.columns([3,2])
        with ca2: st.plotly_chart(heatmap_area_freeshot(s_df,"shooter",f"{sel} エリア別決定率"),use_container_width=True)
        with cb2: st.plotly_chart(heatmap_course_3x3(s_df,title=f"{sel} コース別決定率"),use_container_width=True)
        st.divider()
        st.subheader("🏆 苦手なゴーリーランキング")
        if "ゴーリー" in s_df.columns:
            gs=s_df[s_df["枠内"]==1].groupby("ゴーリー").agg(枠内シュート数=("枠内","count"),セーブされた数=("セーブ","sum")).reset_index()
            gs["阻止された割合(%)"]=( gs["セーブされた数"]/gs["枠内シュート数"]*100).round(1)
            gs=gs.sort_values(["阻止された割合(%)","枠内シュート数"],ascending=[False,False]).reset_index(drop=True)
            gs.index+=1; st.dataframe(gs,use_container_width=True)

    elif mode == "🔵 ゴーリー分析":
        if "ゴーリー" not in df.columns:
            st.info("ゴーリー列がありません。"); st.stop()
        g_list=["全体"]+sorted(df["ゴーリー"].dropna().unique().tolist())
        sel=st.sidebar.selectbox("ゴーリーを選択",g_list)
        g_df=df.copy() if sel=="全体" else df[df["ゴーリー"]==sel].copy()
        st.header(f"🧤 ゴーリー: {sel} の分析結果")
        on_t=g_df[g_df["枠内"]==1].copy(); sv=on_t["セーブ"].sum(); tot=len(on_t)
        sr=(sv/tot*100) if tot>0 else 0
        c1,c2,c3=st.columns(3)
        c1.metric("被枠内シュート数",tot); c2.metric("セーブ数",sv); c3.metric("セーブ率",f"{sr:.1f}%")
        st.divider()
        ca,cb=st.columns([3,2])
        with ca:
            if "日付" in on_t.columns:
                trend=on_t.groupby("日付").agg(率=("セーブ","mean")).reset_index()
                fig=px.line(trend,x="日付",y="率",markers=True,title="日別のセーブ率変化")
                fig.update_layout(yaxis=dict(tickformat=".0%",range=[-0.1,1.1]))
                st.plotly_chart(fig,use_container_width=True)
        with cb:
            if "背番号" in g_df.columns:
                st.plotly_chart(px.pie(g_df,names="背番号",hole=0.3,title="対戦シューター分布"),use_container_width=True)
        st.divider()
        ca2,cb2=st.columns([3,2])
        with ca2: st.plotly_chart(heatmap_area_freeshot(g_df,"goalie",f"{sel} エリア別セーブ率"),use_container_width=True)
        with cb2:
            st.plotly_chart(heatmap_course_3x3(g_df,target_val="セーブ",
                base_filter=lambda d: d["枠内"]==1, cscale="Blues", clabel="セーブ率(%)",
                title=f"{sel} コース別セーブ率"),use_container_width=True)
        st.divider()
        st.subheader("⚠️ 苦手なシューターランキング")
        if "背番号" in g_df.columns:
            ss=on_t.groupby("背番号").agg(被枠内=("枠内","count"),失点=("ゴール","sum")).reset_index()
            ss["失点率(%)"]=( ss["失点"]/ss["被枠内"]*100).round(1)
            ss=ss.sort_values(["失点率(%)","被枠内"],ascending=[False,False]).reset_index(drop=True)
            ss.index+=1; st.dataframe(ss,use_container_width=True)

    else:
        st.header("📊 全データ一覧")
        st.dataframe(df.sort_values("timestamp",ascending=False) if "timestamp" in df.columns else df, use_container_width=True)

# ==========================================
# ② 1on1 分析
# ==========================================
elif practice_mode == "⚔️ 1on1":
    st.title("⚔️ 1on1 練習分析")

    raw_df = load_csv_from_s3(S3_BUCKET, S3_KEY_1on1)
    if raw_df.empty:
        st.warning("データがまだありません。1on1記録ツールからデータを送信してください。")
        st.stop()

    df = date_filter(raw_df, "timestamp")

    st.sidebar.header("🔍 1on1 分析モード")
    mode = st.sidebar.radio("表示モード",["🔴 AT分析","🔵 DF分析","🟡 ゴーリー分析","📊 全データ"])

    if mode == "🔴 AT分析":
        at_list=["全体"]+sorted(df.get("at",pd.Series()).dropna().unique().tolist())
        sel=st.sidebar.selectbox("ATを選択",at_list)
        at_df=df.copy() if sel=="全体" else df[df["at"]==sel].copy()
        st.header(f"👤 AT: {sel} の分析結果")
        c1,c2,c3=st.columns(3)
        shot_df=at_df[at_df.get("endType","")=="ショット"] if "endType" in at_df.columns else at_df
        tot=len(shot_df); g=shot_df["result"].eq("ゴール").sum() if "result" in shot_df.columns else 0
        sr=(g/tot*100) if tot>0 else 0
        c1.metric("対戦DF数",at_df.get("df",pd.Series()).nunique())
        c2.metric("対戦ゴーリー数",at_df.get("goalie",pd.Series()).nunique())
        c3.metric("ショット決定率",f"{sr:.1f}%")
        st.divider()
        cg1,cg2,cg3=st.columns(3)
        with cg1:
            st.subheader("📊 終わり方の傾向")
            if "endType" in at_df.columns: st.plotly_chart(px.pie(at_df,names="endType",hole=0.4),use_container_width=True)
        with cg2:
            st.subheader("🔄 抜き方の傾向")
            if "dodge" in at_df.columns:
                dd=at_df[at_df["dodge"]!="NULL"]
                st.plotly_chart(px.pie(dd,names="dodge",hole=0.4),use_container_width=True)
        with cg3:
            st.subheader("✋ ショットを打った手")
            if "hand" in at_df.columns:
                hd=at_df[at_df["hand"].isin(["右手","左手"])]
                if not hd.empty: st.plotly_chart(px.pie(hd,names="hand",hole=0.4),use_container_width=True)
        st.divider()
        st.subheader("📍 打った位置別 決定率")
        if "shotPos" in at_df.columns: st.plotly_chart(heatmap_shot_pos_1on1(at_df,"AT","エリア別 決定率"),use_container_width=True)
        st.divider()
        st.subheader("🎯 コース別 決定率（3×3）")
        if "course" in at_df.columns:
            st.plotly_chart(heatmap_course_3x3(at_df,base_filter=lambda d: d.get("endType","")=="ショット",title="コース別 決定率"),use_container_width=True)
        st.divider()
        st.subheader(f"⚠️ {sel} の苦手DFランキング")
        if "df" in at_df.columns and "endType" in at_df.columns:
            ds=at_df.groupby("df").agg(対戦数=("endType","count"),ショット数=("endType",lambda x:(x=="ショット").sum())).reset_index()
            ds["阻止率(%)"]=((ds["対戦数"]-ds["ショット数"])/ds["対戦数"]*100).round(1)
            ds=ds.sort_values(["阻止率(%)","対戦数"],ascending=[False,False]).reset_index(drop=True); ds.index+=1
            st.dataframe(ds,use_container_width=True)

    elif mode == "🔵 DF分析":
        df_list=["全体"]+sorted(df.get("df",pd.Series()).dropna().unique().tolist())
        sel=st.sidebar.selectbox("DFを選択",df_list)
        tdf=df.copy() if sel=="全体" else df[df["df"]==sel].copy()
        st.header(f"🛡️ DF: {sel} の分析結果")
        c1,c2,c3=st.columns(3)
        tot=len(tdf); g=tdf["result"].eq("ゴール").sum() if "result" in tdf.columns else 0
        sr=((tot-g)/tot*100) if tot>0 else 0
        c1.metric("総対戦数",tot); c2.metric("トータル阻止率",f"{sr:.1f}%"); c3.metric("対戦AT数",tdf.get("at",pd.Series()).nunique())
        st.divider()
        st.subheader("📍 打たれた位置の失点率")
        if "shotPos" in tdf.columns: st.plotly_chart(heatmap_shot_pos_1on1(tdf,"DF","エリア別 失点率"),use_container_width=True)
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.subheader("📊 起点別 被ショット率")
            if "origin" in tdf.columns: st.plotly_chart(heatmap_origin_ratio(tdf,"DF","起点別 被ショット率"),use_container_width=True)
        with cb:
            st.subheader("📋 起点×抜き方")
            if "origin" in tdf.columns and "endType" in tdf.columns:
                tdf["抜かれた"]=tdf["endType"].eq("ショット").astype(int)
                pv=tdf.groupby(["origin","dodge"])["抜かれた"].sum().unstack(fill_value=0) if "dodge" in tdf.columns else None
                if pv is not None: st.table(pv)
        st.divider()
        st.subheader(f"⚠️ {sel} の苦手ATランキング")
        if "at" in tdf.columns and "endType" in tdf.columns:
            ats=tdf.groupby("at").agg(対戦数=("endType","count"),抜かれた=("endType",lambda x:(x=="ショット").sum())).reset_index()
            ats["抜かれた割合(%)"]=( ats["抜かれた"]/ats["対戦数"]*100).round(1)
            ats=ats.sort_values(["抜かれた割合(%)","対戦数"],ascending=[False,False]).reset_index(drop=True); ats.index+=1
            st.dataframe(ats,use_container_width=True)

    elif mode == "🟡 ゴーリー分析":
        g_list=["全体"]+sorted(df.get("goalie",pd.Series()).dropna().unique().tolist())
        sel_g=st.sidebar.selectbox("ゴーリーを選択",g_list)
        g_full=df.copy() if sel_g=="全体" else df[df["goalie"]==sel_g].copy()
        at_opts=["全体"]+sorted(g_full.get("at",pd.Series()).dropna().unique().tolist())
        sel_at=st.sidebar.selectbox("AT（シューター）を絞り込む",at_opts)
        g_df=g_full.copy() if sel_at=="全体" else g_full[g_full["at"]==sel_at].copy()
        st.header(f"🧤 ゴーリー: {sel_g}（対 {sel_at}）の分析結果")
        st.subheader("📍 打たれた位置別 セーブ率")
        if "shotPos" in g_df.columns: st.plotly_chart(heatmap_shot_pos_1on1(g_df,"G","エリア別 セーブ率"),use_container_width=True)
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.subheader("起点別 セーブ率（2×2）")
            if "origin" in g_df.columns:
                shot_df=g_df[g_df.get("endType","")=="ショット"] if "endType" in g_df.columns else g_df
                gc=np.zeros((2,2)); gt=np.empty((2,2),dtype=object)
                mp2={"左上":(0,0),"右上":(0,1),"左裏":(1,0),"右裏":(1,1)}
                shot_df["oc"]=shot_df["origin"].astype(str).str.strip()
                for orig,(r,c) in mp2.items():
                    od=shot_df[shot_df["oc"]==orig]; tot=len(od)
                    sv=od["result"].eq("セーブ").sum() if "result" in od.columns else 0
                    rt=sv/tot*100 if tot>0 else 0; gc[r,c]=rt; gt[r,c]=f"{sv}/{tot}<br>({rt:.1f}%)"
                fig=px.imshow(gc,x=["左","右"],y=["上","裏"],color_continuous_scale="Blues",title="起点別セーブ率 (2×2)")
                fig.update_traces(text=gt,texttemplate="%{text}"); fig.update_layout(width=350,height=350)
                st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.subheader("コース別 セーブ率（3×3）")
            if "course" in g_df.columns:
                st.plotly_chart(heatmap_course_3x3(g_df,target_val="セーブ",
                    base_filter=lambda d: d.get("endType","")=="ショット" if "endType" in d.columns else [True]*len(d),
                    cscale="Blues",clabel="セーブ率(%)",title="コース別セーブ率"),use_container_width=True)
        st.divider()
        st.subheader("⚠️ 苦手ATランキング")
        shot_full=g_full[g_full.get("endType","")=="ショット"] if "endType" in g_full.columns else g_full
        if "at" in shot_full.columns and "result" in shot_full.columns:
            gs=shot_full.groupby("at").agg(被ショット=("result","count"),セーブ=("result",lambda x:x.eq("セーブ").sum())).reset_index()
            gs["セーブ率(%)"]=( gs["セーブ"]/gs["被ショット"]*100).round(1)
            gs=gs.sort_values(["セーブ率(%)","被ショット"],ascending=[True,False]).reset_index(drop=True); gs.index+=1
            st.dataframe(gs,use_container_width=True)

    else:
        st.header("📊 全データ一覧")
        st.dataframe(df.sort_values("timestamp",ascending=False) if "timestamp" in df.columns else df,use_container_width=True)

# ==========================================
# ③ 6on6 分析
# ==========================================
elif practice_mode == "🏟️ 6on6":
    st.title("🏟️ 6on6 練習分析")

    # 各CSVを読み込む
    df_shot = load_csv_from_s3(S3_BUCKET, S3_KEY_6on6_SHOT)
    df_to   = load_csv_from_s3(S3_BUCKET, S3_KEY_6on6_TO)
    df_gb   = load_csv_from_s3(S3_BUCKET, S3_KEY_6on6_GB)
    df_miss = load_csv_from_s3(S3_BUCKET, S3_KEY_6on6_MISS)

    all_empty = df_shot.empty and df_to.empty and df_gb.empty and df_miss.empty
    if all_empty:
        st.warning("データがまだありません。6on6記録ツールからデータを送信してください。")
        st.stop()

    # 期間フィルター（ショットデータを基準）
    base_df = df_shot if not df_shot.empty else df_to
    if not base_df.empty:
        base_df = prep_timestamp(base_df)
        valid = base_df.dropna(subset=["timestamp"]) if "timestamp" in base_df.columns else base_df
        if not valid.empty:
            mn=valid["timestamp"].min().date(); mx=valid["timestamp"].max().date()
            rng=st.sidebar.date_input("📅 期間フィルター",value=(mn,mx),min_value=mn,max_value=mx)
            def apply_filter(df, col="timestamp"):
                if df.empty or col not in df.columns: return df
                df=prep_timestamp(df, col)
                if isinstance(rng,tuple) and len(rng)==2:
                    s=pd.to_datetime(rng[0]); e=pd.to_datetime(rng[1])+pd.Timedelta(days=1)-pd.Timedelta(seconds=1)
                    return df[(df[col]>=s)&(df[col]<=e)].copy()
                return df
            df_shot=apply_filter(df_shot); df_to=apply_filter(df_to); df_gb=apply_filter(df_gb); df_miss=apply_filter(df_miss)

    st.sidebar.header("🔍 6on6 分析モード")
    mode = st.sidebar.radio("表示モード",["🥍 ショット分析","🔄 TO分析","⬆️ GB分析","⚠️ 個人ミス分析","📊 全データ"])

    # ── ショット分析 ──
    if mode == "🥍 ショット分析":
        st.header("🥍 6on6 ショット分析")
        if df_shot.empty:
            st.info("ショットデータがまだありません。"); st.stop()

        # サマリーKPI
        tot=len(df_shot); g=df_shot["result"].eq("ゴール").sum() if "result" in df_shot.columns else 0
        sv=df_shot["result"].eq("セーブ").sum() if "result" in df_shot.columns else 0
        dr=(g/tot*100) if tot>0 else 0; on_t=g+sv; sr=(sv/on_t*100) if on_t>0 else 0
        c1,c2,c3,c4=st.columns(4)
        c1.metric("総ショット数",tot); c2.metric("ゴール",g); c3.metric("決定率",f"{dr:.1f}%"); c4.metric("ゴーリーセーブ率",f"{sr:.1f}%")

        st.divider()
        # シューター絞り込み
        if "shooter" in df_shot.columns:
            sh_list=["全体"]+sorted(df_shot["shooter"].dropna().unique().tolist())
            sel=st.sidebar.selectbox("シューターを絞り込む",sh_list)
            s_df=df_shot.copy() if sel=="全体" else df_shot[df_shot["shooter"]==sel].copy()
        else:
            s_df=df_shot.copy(); sel="全体"

        ca,cb=st.columns([3,2])
        with ca:
            st.subheader(f"📍 {sel} エリア別 決定率")
            if "area" in s_df.columns:
                st.plotly_chart(heatmap_area_freeshot(s_df.rename(columns={"result":"result"}),"shooter","エリア別 決定率"),use_container_width=True)
        with cb:
            st.subheader(f"🎯 {sel} コース別 決定率")
            if "course" in s_df.columns:
                st.plotly_chart(heatmap_course_3x3(s_df,title="コース別 決定率"),use_container_width=True)

        st.divider()
        ca2,cb2=st.columns(2)
        with ca2:
            st.subheader("起点別 ショット分布")
            if "origin" in df_shot.columns:
                oc=df_shot["origin"].value_counts().reset_index(); oc.columns=["起点","本数"]
                st.plotly_chart(px.bar(oc,x="起点",y="本数",color="本数",color_continuous_scale="Oranges"),use_container_width=True)
        with cb2:
            st.subheader("攻め方別 ショット数")
            if "atkStyle" in df_shot.columns:
                ac=df_shot[df_shot["atkStyle"]!="NULL"]["atkStyle"].value_counts().reset_index(); ac.columns=["攻め方","本数"]
                st.plotly_chart(px.bar(ac,x="攻め方",y="本数",color="本数",color_continuous_scale="Reds"),use_container_width=True)

        st.divider()
        st.subheader("🏆 シューター別 成績ランキング")
        if "shooter" in df_shot.columns and "result" in df_shot.columns:
            sh=df_shot.groupby(["side","shooter"]).agg(ショット=("result","count"),ゴール=("result",lambda x:x.eq("ゴール").sum())).reset_index()
            sh["決定率(%)"]=( sh["ゴール"]/sh["ショット"]*100).round(1)
            sh=sh.sort_values(["決定率(%)","ショット"],ascending=[False,False]).reset_index(drop=True); sh.index+=1
            st.dataframe(sh,use_container_width=True)

    # ── TO分析 ──
    elif mode == "🔄 TO分析":
        st.header("🔄 6on6 TO分析")
        if df_to.empty:
            st.info("TOデータがまだありません。"); st.stop()
        tot=len(df_to)
        c1,c2=st.columns(2)
        c1.metric("総TO数",tot)
        if "side" in df_to.columns:
            c2.metric("AT由来 / DF由来",f"AT:{df_to['side'].eq('AT').sum()} / DF:{df_to['side'].eq('DF').sum()}")
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.subheader("📊 原因別 TO数")
            if "cause" in df_to.columns:
                cc=df_to["cause"].value_counts().reset_index(); cc.columns=["原因","件数"]
                st.plotly_chart(px.pie(cc,names="原因",values="件数",hole=0.4),use_container_width=True)
        with cb:
            st.subheader("📋 セット別 TO数")
            if "set" in df_to.columns:
                sc=df_to["set"].value_counts().sort_index().reset_index(); sc.columns=["セット","件数"]
                st.plotly_chart(px.bar(sc,x="セット",y="件数",color="件数",color_continuous_scale="Reds"),use_container_width=True)
        st.divider()
        st.subheader("⚠️ 選手別 TO数ランキング")
        if "player1" in df_to.columns:
            p1=df_to.groupby("player1").size().reset_index(name="TO数").sort_values("TO数",ascending=False).reset_index(drop=True); p1.index+=1
            st.dataframe(p1,use_container_width=True)

    # ── GB分析 ──
    elif mode == "⬆️ GB分析":
        st.header("⬆️ 6on6 GB分析")
        if df_gb.empty:
            st.info("GBデータがまだありません。"); st.stop()
        tot=len(df_gb)
        c1,c2=st.columns(2)
        c1.metric("総GB数",tot)
        if "side" in df_gb.columns:
            at_gb=df_gb["side"].eq("AT").sum(); df_gb_cnt=df_gb["side"].eq("DF").sum()
            c2.metric("AT取得 / DF取得",f"{at_gb} / {df_gb_cnt}")
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.subheader("📊 取得者のポジション別 GB数")
            if "side" in df_gb.columns:
                sc=df_gb["side"].value_counts().reset_index(); sc.columns=["ポジション","件数"]
                st.plotly_chart(px.pie(sc,names="ポジション",values="件数",hole=0.4,
                    color_discrete_map={"AT":"#FF7000","DF":"#4FC3F7"}),use_container_width=True)
        with cb:
            st.subheader("📊 セット別 GB数")
            if "set" in df_gb.columns:
                sc=df_gb["set"].value_counts().sort_index().reset_index(); sc.columns=["セット","件数"]
                st.plotly_chart(px.bar(sc,x="セット",y="件数",color="件数",color_continuous_scale="Blues"),use_container_width=True)
        st.divider()
        st.subheader("🏆 選手別 GB取得数ランキング")
        if "player" in df_gb.columns:
            pr=df_gb.groupby(["side","player"]).size().reset_index(name="GB取得数").sort_values("GB取得数",ascending=False).reset_index(drop=True); pr.index+=1
            st.dataframe(pr,use_container_width=True)

    # ── 個人ミス分析 ──
    elif mode == "⚠️ 個人ミス分析":
        st.header("⚠️ 6on6 個人ミス分析")
        if df_miss.empty:
            st.info("個人ミスデータがまだありません。"); st.stop()
        tot=len(df_miss)
        rec=df_miss["recover"].eq("リカバーあり").sum() if "recover" in df_miss.columns else 0
        rr=(rec/tot*100) if tot>0 else 0
        c1,c2,c3=st.columns(3); c1.metric("総ミス数",tot); c2.metric("リカバーあり",rec); c3.metric("リカバー率",f"{rr:.1f}%")
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.subheader("📊 ミス種別")
            if "missType" in df_miss.columns:
                mc=df_miss["missType"].value_counts().reset_index(); mc.columns=["種別","件数"]
                st.plotly_chart(px.pie(mc,names="種別",values="件数",hole=0.4),use_container_width=True)
        with cb:
            st.subheader("📊 リカバー有無")
            if "recover" in df_miss.columns:
                rc=df_miss["recover"].value_counts().reset_index(); rc.columns=["リカバー","件数"]
                st.plotly_chart(px.bar(rc,x="リカバー",y="件数",color="リカバー",
                    color_discrete_map={"リカバーあり":"#43A047","リカバーなし":"#e53935"}),use_container_width=True)
        st.divider()
        st.subheader("⚠️ 選手別 ミス数ランキング（リカバーなし優先）")
        if "player" in df_miss.columns and "recover" in df_miss.columns:
            pm=df_miss.groupby(["side","player"]).agg(
                ミス数=("missType","count"),
                リカバーなし=("recover",lambda x:x.eq("リカバーなし").sum())
            ).reset_index().sort_values(["リカバーなし","ミス数"],ascending=[False,False]).reset_index(drop=True); pm.index+=1
            st.dataframe(pm,use_container_width=True)

    # ── 全データ ──
    else:
        st.header("📊 全データ一覧")
        tab1,tab2,tab3,tab4=st.tabs(["🥍 ショット","🔄 TO","⬆️ GB","⚠️ 個人ミス"])
        with tab1: st.dataframe(df_shot,use_container_width=True)
        with tab2: st.dataframe(df_to,use_container_width=True)
        with tab3: st.dataframe(df_gb,use_container_width=True)
        with tab4: st.dataframe(df_miss,use_container_width=True)
