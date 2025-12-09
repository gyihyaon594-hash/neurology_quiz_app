import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


from database_utils import get_user_logs, to_df


st.set_page_config(page_title="학생 요약 대시보드", page_icon="📊", layout="wide")


QUESTIONS_XLSX = os.getenv("QUESTIONS_XLSX", "questions.xlsx")  # ← 변경: questions.xlsx 사용


def load_questions(path: str) -> pd.DataFrame:
    """
    기대 컬럼: "Question", "Choices", "Answer", "difficulty" (값: low/medium/high)
    question_id는 엑셀의 행 순서를 문제 번호로 사용(0-index면 +1 보정)
    """
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_excel(path)
    return df
# ─────────────────────────────────────────
# 세션 확인 (개인 뷰)
# ─────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.warning("홈에서 학습자 등록 후에 접근해 주세요.")
    st.stop()


user_id = st.session_state.user_id
st.title(f"📊 학습 요약 대시보드 — {user_id}")


# ─────────────────────────────────────────
# 영어 문제 데이터 가져오기
# ─────────────────────────────────────────
qmeta = load_questions(QUESTIONS_XLSX)


cur = get_user_logs(user_id, sort_asc=True)
df = to_df(cur)

# 데이터 없으면 종료
if df.empty or "question_id" not in df.columns:
    st.info("아직 학습 기록이 없습니다. 먼저 Quiz를 풀어보세요!")
    st.stop()

# 타입 정리
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
if "question_id" in df.columns:
    df["question_id"] = pd.to_numeric(df["question_id"], errors="coerce")


df = df.dropna(subset=["question_id"]).copy()
df["question_id"] = df["question_id"].astype(int)


# ─────────────────────────────────────────
# 문항 단위 요약 만들기
# ─────────────────────────────────────────


def summarize_per_question(g: pd.DataFrame) -> pd.Series:
    g = g.sort_values("timestamp")


    # 제출 레코드
    submit = g[g["action"] == "submit_answer"].sort_values("timestamp")
    solving_time = submit["solving_time"].iloc[0] if not submit.empty else np.nan
    correct = submit["correct"].iloc[0] if not submit.empty else np.nan


    # submit 이전 select_answer 개수
    if not submit.empty:
        t_submit = submit["timestamp"].iloc[0]
        select_cnt = len(g[(g["action"] == "select_answer") & (g["timestamp"] <= t_submit)])
    else:
        select_cnt = len(g[g["action"] == "select_answer"])


    # 추가 질문 여부
    has_fu_q = (g["action"] == "follow_up_question").any()


    # 학습 피드백 텍스트 (가장 최근)
    learn_fb = g[g["action"] == "learning_feedback"].sort_values("timestamp")
    learn_fb_text = learn_fb["content"].iloc[-1] if not learn_fb.empty else ""


    # 추가 질문/답변 페어(간단 매칭: 질문 이후 가장 가까운 답변 하나)
    fu_q_list, fu_a_list = [], []
    for _, r in g[g["action"] == "follow_up_question"].iterrows():
        fu_q_list.append(r.get("content"))
        ans = g[(g["action"] == "follow_up_answer") & (g["timestamp"] >= r["timestamp"])].sort_values("timestamp")
        fu_a_list.append(ans["content"].iloc[0] if not ans.empty else "")


    return pd.Series({
        "풀이시간(초)": solving_time,
        "정답": correct,
        "선택변경횟수": select_cnt,
        "추가질문여부": has_fu_q,
        "학습피드백": learn_fb_text,
        "추가질문목록": fu_q_list,
        "추가답변목록": fu_a_list,
    })


qsum = df.groupby("question_id", as_index=False).apply(summarize_per_question).reset_index(drop=True)


# 문항 텍스트 및 난이도 조인
if not qmeta.empty:
    qmeta = qmeta.reset_index().rename(columns={"index": "question_id"})
    # index가 0부터이기 때문에 +1 보정
    if qmeta["question_id"].min() == 0:
        qmeta["question_id"] = qmeta["question_id"] + 1
    cols = [c for c in ["question_id", "Question", "difficulty"] if c in qmeta.columns]
    qmeta_small = qmeta[cols].copy()
    qsum = qsum.merge(qmeta_small, on="question_id", how="left")
else:
    qsum["difficulty"] = "미지정"




k1, k2, k3 = st.columns(3)
with k1:
    st.metric("전체 평균 풀이시간(초)", f"{np.nanmean(qsum['풀이시간(초)']):.1f}" if not qsum.empty else "-")
with k2:
    if "정답" in qsum and not qsum["정답"].isna().all():
        st.metric("전체 정답률", f"{np.nanmean(qsum['정답'])*100:.0f}%")
    else:
        st.metric("전체 정답률", "-")
with k3:
    if not qsum.empty:
        st.metric("전체 추가 질문 비율", f"{qsum['추가질문여부'].mean()*100:.0f}%")
    else:
        st.metric("전체 추가 질문 비율", "-")


# ─────────────────────────────────────────
# (1)~(3) 지표를 가로(col)로 배치
# ─────────────────────────────────────────
col_a, col_b, col_c = st.columns(3)


# (1) 난이도별 평균 문제 풀이 시간
with col_a:
    st.subheader("⏱️ 평균 문제 풀이 시간")
    time_df = qsum.groupby("difficulty", as_index=False)["풀이시간(초)"].mean() # 열로 남기기 위해 as_index = False 아니면 difficulty 가  index로 넘어감
    fig = px.bar(time_df, x="difficulty", y="풀이시간(초)", text="풀이시간(초)") # plotly.express로 시각화를 하는 부분
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), xaxis_title="난이도")
    st.plotly_chart(fig, use_container_width=True)


# (2) 난이도별 정답률
with col_b:
    st.subheader("✅ 정답률")
    acc_df = qsum.assign(정답값=lambda d: d["정답"].fillna(0).astype(int)) \
        .groupby("difficulty", as_index=False)["정답값"].mean() \
        .rename(columns={"정답값": "정답률"})
    fig = px.bar(acc_df, x="difficulty", y="정답률", text="정답률", range_y=[0, 1])
    fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), xaxis_title="난이도", yaxis_tickformat=",.0%")
    st.plotly_chart(fig, use_container_width=True)


# (3) 난이도별 추가 질문 비율
with col_c:
    st.subheader("💬 추가 질문 비율")
    fu_df = qsum.groupby("difficulty", as_index=False)["추가질문여부"].mean().rename(columns={"추가질문여부": "추가질문비율"})
    if fu_df.empty:
        st.info("추가 질문 여부를 계산할 수 있는 데이터가 없습니다.")
    else:
        fig = px.bar(fu_df, x="difficulty", y="추가질문비율", text="추가질문비율", range_y=[0, 1])
        fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), xaxis_title="난이도", yaxis_tickformat=",.0%")
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────
# (4) 오답 문항 + 학습 피드백 내용
# ─────────────────────────────────────────
st.subheader("❌ 오답 문항과 학습 피드백")
wrong_tbl = qsum[(qsum["정답"] == False)][["question_id", "difficulty", "Question", "학습피드백"]].copy()
wrong_tbl = wrong_tbl.rename(columns={"question_id": "문항 번호", "difficulty": "난이도", "Question": "문항"})
if wrong_tbl.empty:
    st.info("오답 문항이 없습니다.")
else:
    st.dataframe(wrong_tbl, use_container_width=True)


# ─────────────────────────────────────────
# (5) 정답이지만 선택 변경(헷갈림) 문항 + 학습 피드백
# ─────────────────────────────────────────
st.subheader("🤔 정답이지만 선택을 여러 번 바꾼 문항과 학습 피드백")
confused_tbl = qsum[(qsum["정답"] == True) & (qsum["선택변경횟수"] > 1)][["question_id", "difficulty", "Question", "선택변경횟수", "학습피드백"]].copy()
confused_tbl = confused_tbl.rename(columns={"question_id": "문항 번호", "difficulty": "난이도", "Question": "문항"})
if confused_tbl.empty:
    st.info("해당되는 문항이 없습니다.")
else:
    st.dataframe(confused_tbl, use_container_width=True)


# ─────────────────────────────────────────
# (6) 추가 질문과 그에 대한 답변 내용
# ─────────────────────────────────────────
st.subheader("🧾 추가 질문과 답변 기록")
pairs_rows = []
for _, r in qsum.iterrows():
    qid = r["question_id"]
    for qtxt, atxt in zip(r["추가질문목록"], r["추가답변목록"]):
        pairs_rows.append({"question_id": qid, "difficulty": r["difficulty"], "질문": qtxt, "답변": atxt})
pairs_df = pd.DataFrame(pairs_rows)
if pairs_df.empty:
    st.info("추가 질문/답변 기록이 없습니다.")
else:
    pairs_df = pairs_df.rename(columns={"question_id": "문항 번호", "difficulty": "난이도"})
    st.dataframe(pairs_df[["문항 번호", "난이도", "질문", "답변"]], use_container_width=True)
