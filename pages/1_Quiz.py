import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime
from database_utils import log_user_action
import gspread
from google.oauth2.service_account import Credentials

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

st.set_page_config(page_title="신경학 Quiz", page_icon="🧠")

# 분과 목록 정의
CATEGORIES = {
    "Approach": "1. 신경계질환의 접근",
    "Critical Care": "2. 의식장애와 중환자관리",
    "Stroke": "3. 뇌혈관질환",
    "Movement": "4. 이상운동",
    "Neuromuscular": "5. 신경근육",
    "Demyelinating": "6. 탈수초성",
    "CNS Infection": "7. 뇌감염질환",
    "Seizure": "8. 경련",
    "Dementia": "9. 치매",
    "Headache": "10. 두통"
}

def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.switch_page("app.py")

require_login()

# Google Sheets 연결
def get_sheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

def get_questions_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("questions")
    except:
        worksheet = spreadsheet.add_worksheet(title="questions", rows=1000, cols=15)
        worksheet.append_row([
            "id", "category", "question", "choices", "answer", 
            "feedback_1", "feedback_2", "feedback_3", "feedback_4", "feedback_5",
            "difficulty", "image_url", "video_url", "author", "created_at"
        ])
        return worksheet

def get_progress_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("progress")
    except:
        return None

@st.cache_data(ttl=300)
def load_all_questions():
    try:
        sheet = get_questions_sheet()
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_questions_by_category(df, category):
    if df.empty:
        return pd.DataFrame()
    if category == "All":
        return df.reset_index(drop=True)
    return df[df['category'] == category].reset_index(drop=True)

def get_category_counts(df):
    if df.empty:
        return {cat: 0 for cat in CATEGORIES.keys()}
    counts = df['category'].value_counts().to_dict()
    return {cat: counts.get(cat, 0) for cat in CATEGORIES.keys()}

def save_progress(user_id, qid, category):
    sheet = get_progress_sheet()
    if sheet is None:
        return
    try:
        cell = sheet.find(user_id)
        sheet.update_cell(cell.row, 2, qid)
        sheet.update_cell(cell.row, 3, category)
        sheet.update_cell(cell.row, 4, datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
    except:
        sheet.append_row([user_id, qid, category, datetime.utcnow().strftime("%Y-%m-%d %H:%M")])

# LLM 설정
llm_api_key = st.secrets["OPENAI_API_KEY"]

empathy_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.9,
    api_key=llm_api_key,
    model_kwargs={"frequency_penalty": 0, "presence_penalty": 0.6},
)

feedback_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=llm_api_key,
    model_kwargs={"frequency_penalty": 0, "presence_penalty": 0.9},
)

EMPATHY_SYSTEM = (
    "당신은 신경과 전문의입니다. 학습자의 답변을 보고 한국어로 공감하는 말을 두 문장으로 표현해주세요.\n"
    "정답인 경우: 성취감을 높일 수 있는 공감을 제공해요.\n"
    "오답인 경우: 격려와 함께 공감을 제공해요."
)

FEEDBACK_SYSTEM = (
    "당신은 신경과 전문의입니다. 학생의 추가 질문에 대해 친절하게 답변해주세요.\n"
    "가장 최근에 푼 문제에 대해서만 답변해요."
)

empathy_prompt = ChatPromptTemplate.from_messages([
    ("system", EMPATHY_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{learning_context}"),
])

feedback_prompt = ChatPromptTemplate.from_messages([
    ("system", FEEDBACK_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{follow_up_question}"),
])

empathy_chain = empathy_prompt | empathy_model
feedback_chain = feedback_prompt | feedback_model

if "shared_history_store" not in st.session_state:
    st.session_state.shared_history_store = {}

def get_shared_history(session_id: str) -> ChatMessageHistory:
    store = st.session_state.shared_history_store
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

empathy_with_history = RunnableWithMessageHistory(
    empathy_chain,
    get_shared_history,
    input_messages_key="learning_context",
    history_messages_key="history",
)

feedback_with_history = RunnableWithMessageHistory(
    feedback_chain,
    get_shared_history,
    input_messages_key="follow_up_question",
    history_messages_key="history",
)

def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)

def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})

def paint_history():
    for message in st.session_state["messages"]:
        send_message(message["message"], message["role"], save=False)

def render_feedback(selected: str, qrow):
    if st.session_state.feedback_given:
        return
    
    answer = str(qrow.get('answer', '')).strip()
    is_correct = (str(selected).strip() == answer)
    st.session_state.is_correct = is_correct
    
    choices = [c.strip() for c in str(qrow['choices']).split(',')]
    
    if is_correct:
        corrective_feedback = "정답입니다! 잘했어요."
        st.session_state.learning_history.append("correct")
    else:
        corrective_feedback = "오답입니다. 다시 확인해볼까요?"
        st.session_state.learning_history.append("wrong")
    
    try:
        choice_idx = choices.index(selected)
        feedback_key = f"feedback_{choice_idx + 1}"
        learning_feedback = qrow.get(feedback_key, '')
    except:
        learning_feedback = ""
    
    with st.chat_message("ai"):
        st.write(corrective_feedback)
        log_user_action(action="corrective_feedback", user_id=st.session_state.user_id, 
                       question_id=st.session_state.qid, content=corrective_feedback)
    
    if learning_feedback:
        with st.chat_message("ai"):
            st.write(learning_feedback)
            log_user_action(action="learning_feedback", user_id=st.session_state.user_id,
                           question_id=st.session_state.qid, content=learning_feedback)
    
    st.session_state.feedback_given = True
    save_message(corrective_feedback, "ai")
    if learning_feedback:
        save_message(learning_feedback, "ai")
    
    learning_context = f"Question: {qrow['question']}, Correct Answer: {answer}, Student Answer: {selected}"
    
    try:
        e_response = empathy_with_history.invoke(
            {"learning_context": learning_context},
            config={"configurable": {"session_id": st.session_state.user_id}}
        )
        empathy_response = e_response.content
        
        with st.chat_message("ai"):
            st.write(empathy_response)
            save_message(empathy_response, "ai")
    except:
        pass

def follow_up(follow_up_question):
    send_message(follow_up_question, "human", save=True)
    
    try:
        f_response = feedback_with_history.invoke(
            {"follow_up_question": follow_up_question},
            config={"configurable": {"session_id": st.session_state.user_id}}
        )
        feedback_response = f_response.content
        
        with st.chat_message("ai"):
            st.write(feedback_response)
            save_message(feedback_response, "ai")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

def on_choice_change():
    choice = st.session_state.current_radio
    log_user_action(
        action="select_answer",
        user_id=st.session_state.user_id,
        question_id=st.session_state.qid,
        selected_choice=choice,
    )

# 세션 상태 초기화
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "qid" not in st.session_state:
    st.session_state.qid = 1
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "selected" not in st.session_state:
    st.session_state.selected = None
if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.now()
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False
if "learning_history" not in st.session_state:
    st.session_state.learning_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_correct" not in st.session_state:
    st.session_state.is_correct = None

# ============ UI ============
st.title("🧠 신경학 Quiz")

st.markdown("""
<style>
    div[role="radiogroup"] label {
        font-size: 18px !important;
        padding: 8px 0 !important;
    }
    div[role="radiogroup"] label > div:first-child {
        transform: scale(1.2);
    }
</style>
""", unsafe_allow_html=True)

all_questions_df = load_all_questions()

# 분과 선택 (카테고리 미선택 시)
if st.session_state.selected_category is None:
    st.subheader("📚 학습 분과를 선택하세요")
    
    category_counts = get_category_counts(all_questions_df)
    
    # ⭐ 수정된 부분: 2개씩 묶어서 순서대로 표시
    items = list(CATEGORIES.items())
    
    for i in range(0, len(items), 2):
        col1, col2 = st.columns(2)
        
        # 왼쪽 버튼
        cat_en, cat_kr = items[i]
        with col1:
            count = category_counts.get(cat_en, 0)
            if st.button(
                f"📖 {cat_kr} 문제 {count}개", 
                key=f"cat_{cat_en}",
                use_container_width=True,
                disabled=(count == 0)
            ):
                st.session_state.selected_category = cat_en
                st.session_state.qid = 1
                st.session_state.submitted = False
                st.session_state.selected = None
                st.session_state.feedback_given = False
                st.session_state.messages = []
                st.session_state.learning_history = []
                st.rerun()
        
        # 오른쪽 버튼
        if i + 1 < len(items):
            cat_en, cat_kr = items[i + 1]
            with col2:
                count = category_counts.get(cat_en, 0)
                if st.button(
                    f"📖 {cat_kr} 문제 {count}개", 
                    key=f"cat_{cat_en}",
                    use_container_width=True,
                    disabled=(count == 0)
                ):
                    st.session_state.selected_category = cat_en
                    st.session_state.qid = 1
                    st.session_state.submitted = False
                    st.session_state.selected = None
                    st.session_state.feedback_given = False
                    st.session_state.messages = []
                    st.session_state.learning_history = []
                    st.rerun()
    
    st.divider()
    if st.button("🔄 문제 목록 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 퀴즈 진행
else:
    category = st.session_state.selected_category
    df = get_questions_by_category(all_questions_df, category)
    
    with st.sidebar:
        st.markdown(f"**현재 분과:** {CATEGORIES.get(category, category)}")
        if st.button("🔄 분과 변경"):
            st.session_state.selected_category = None
            st.session_state.qid = 1
            st.session_state.submitted = False
            st.rerun()
    
    if df.empty:
        st.warning("등록된 문제가 없습니다.")
        if st.button("분과 선택으로 돌아가기"):
            st.session_state.selected_category = None
            st.rerun()
    else:
        save_progress(st.session_state.user_id, st.session_state.qid, category)
        
        if st.session_state.qid > len(df):
            st.session_state.qid = 1
        
        row = df.iloc[st.session_state.qid - 1]
        
        st.caption(f"📁 {CATEGORIES.get(category, category)} | 문제 {st.session_state.qid}/{len(df)}")
        st.markdown("**가장 적절한 답을 고르시오.**")
        st.markdown(f"{st.session_state.qid}. {row['question']}")
        
image_url = str(row.get('image_url', '') or '').strip()
if image_url and image_url != 'nan' and image_url != '':
    # http 체크 제거 (Google Drive 등 다양한 URL 지원)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        try:
            st.image(image_url, use_container_width=True)
        except Exception as e:
            st.warning(f"이미지 로드 실패: {e}")

video_url = str(row.get('video_url', '') or '').strip()
if video_url and video_url != 'nan' and video_url != '':
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        try:
            st.video(video_url)
        except Exception as e:
            st.warning(f"동영상 로드 실패: {e}")
        
        choices = [c.strip() for c in str(row['choices']).split(',')]
        
        if st.session_state.submitted and st.session_state.selected in choices:
            radio_index = choices.index(st.session_state.selected)
        else:
            radio_index = None
        
        selected = st.radio(
            "선택하세요",
            options=choices,
            index=radio_index,
            label_visibility="collapsed",
            disabled=st.session_state.submitted,
            key="current_radio",
            on_change=on_choice_change
        )
        
        if not st.session_state.submitted:
            if st.button("정답 제출", type="primary"):
                if selected is None:
                    st.warning("👉 답을 선택해주세요.")
                else:
                    st.session_state.selected = selected
                    st.session_state.submitted = True
                    solving_time = (datetime.now() - st.session_state.start_time).total_seconds()
                    is_correct = (str(selected).strip() == str(row.get('answer', '')).strip())
                    log_user_action(
                        action="submit_answer",
                        user_id=st.session_state.user_id,
                        question_id=st.session_state.qid,
                        selected_choice=selected,
                        correct=is_correct,
                        solving_time=solving_time
                    )
                    st.rerun()
        else:
            render_feedback(st.session_state.selected, row)
            
            if st.session_state.is_correct == False:
                if st.button("🔄 이 문제 다시 풀기"):
                    st.session_state.submitted = False
                    st.session_state.selected = None
                    st.session_state.start_time = datetime.now()
                    st.session_state.feedback_given = False
                    st.session_state.is_correct = None
                    st.session_state.messages = []
                    st.rerun()
            
            follow_up_question = st.chat_input("궁금한 점을 입력하세요...")
            if follow_up_question:
                paint_history()
                follow_up(follow_up_question)
            
            if st.session_state.qid == len(df):
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.session_state.qid > 1:
                        if st.button("◀ 이전 문제"):
                            st.session_state.qid -= 1
                            st.session_state.submitted = False
                            st.session_state.selected = None
                            st.session_state.feedback_given = False
                            st.session_state.is_correct = None
                            st.session_state.messages = []
                            st.rerun()
                with col2:
                    if st.button("✅ 완료"):
                        st.success("모든 문제를 완료했습니다! 🎉")
                        st.session_state.selected_category = None
                with col3:
                    if st.button("🔄 다시풀기"):
                        st.session_state.qid = 1
                        st.session_state.submitted = False
                        st.session_state.selected = None
                        st.session_state.feedback_given = False
                        st.session_state.is_correct = None
                        st.session_state.messages = []
                        st.session_state.learning_history = []
                        st.rerun()
            else:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.session_state.qid > 1:
                        if st.button("◀ 이전 문제"):
                            st.session_state.qid -= 1
                            st.session_state.submitted = False
                            st.session_state.selected = None
                            st.session_state.feedback_given = False
                            st.session_state.is_correct = None
                            st.session_state.messages = []
                            st.rerun()
                with col2:
                    if st.button("다음 문제 ▶"):
                        st.session_state.qid += 1
                        st.session_state.submitted = False
                        st.session_state.selected = None
                        st.session_state.feedback_given = False
                        st.session_state.is_correct = None
                        st.session_state.messages = []
                        st.rerun()
