import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database_utils import log_user_action
import gspread
from google.oauth2.service_account import Credentials

#11주차
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

st.set_page_config(page_title="신경학 Quiz", page_icon="🤖")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    return df


def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.switch_page("app.py")


require_login()      

# Google Sheets 연결 (진행 상태 저장용)
def get_progress_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("progress")
    except:
        return None

def save_progress(user_id, qid):
    sheet = get_progress_sheet()
    if sheet is None:
        st.error("progress 시트 연결 실패")
        return
    try:
        cell = sheet.find(user_id)
        sheet.update_cell(cell.row, 2, qid)
        sheet.update_cell(cell.row, 3, datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
    except:
        sheet.append_row([user_id, qid, datetime.utcnow().strftime("%Y-%m-%d %H:%M")])

def render_feedback(selected: str, qrow: pd.Series):
    if st.session_state.feedback_given is True:
        return
    is_correct = (str(selected).strip() == str(qrow["Answer"]).strip())
    choices = qrow['Choices'].split(', ')


    # corrective feedback
    if is_correct:
        corrective_feedback = "정답입니다! 잘했어요."
        st.session_state.learning_history.append("correct")  # 11 주차 추가
    else:
        corrective_feedback = "오답입니다. 다시 확인해볼까요?"
        st.session_state.learning_history.append("wrong") # 11 주차 추가


    # learning feedback 가져오기
    choice_idx = choices.index(selected)
    choice_num = choice_idx + 1  
    learning_feedback = qrow[choice_num]


    with st.chat_message("ai"):
        st.write(corrective_feedback)
        log_user_action(action="corrective_feedback", user_id=st.session_state.user_id, question_id=st.session_state.qid, content=corrective_feedback)


    with st.chat_message("ai"):
        st.write(learning_feedback)
        log_user_action(action="learning_feedback", user_id=st.session_state.user_id, question_id=st.session_state.qid, content=learning_feedback)
    st.session_state.feedback_given = True


    #11주차 내용
    save_message(corrective_feedback, "ai")
    save_message(learning_feedback, "ai")


    learning_context = f"Question: {qrow['Question']}, Choices: {qrow['Choices']}, Correct Answer: {qrow['Answer']}, Student Answer: {selected}, Learning History: {st.session_state.learning_history}"
   
    e_response = empathy_with_history.invoke(
        {"learning_context": learning_context},
        config={"configurable": {"session_id": st.session_state.user_id}}
    )

    empathy_response = e_response.content

    with st.chat_message("ai"):
        st.write(empathy_response)
        save_message(empathy_response, "ai")
        log_user_action(action="empathetic_feedback", user_id=st.session_state.user_id, question_id=st.session_state.qid, content=empathy_response)

    # history = get_shared_history(st.session_state.user_id)
    # st.write(history.messages)


#11주차 내용
def follow_up(follow_up_question):
    send_message(follow_up_question, "human", save=True)
    log_user_action(action="follow_up_question", user_id=st.session_state.user_id, question_id=st.session_state.qid, content=follow_up_question)
   
    f_response = feedback_with_history.invoke(
        {"follow_up_question": follow_up_question},
        config={"configurable": {"session_id": st.session_state.user_id}}
    )


    feedback_response = f_response.content
   
    with st.chat_message("ai"):
        st.write(feedback_response)
        save_message(feedback_response, "ai")
        log_user_action(action="follow_up_answer", user_id=st.session_state.user_id, question_id=st.session_state.qid, content=feedback_response)
   


def on_choice_change():
    choice = st.session_state.current_radio  # 라디오의 현재 값
    log_user_action(
        action="select_answer",
        user_id=st.session_state.user_id,
        question_id=st.session_state.qid,  
        selected_choice=choice,
    )


# 11주차 내용
# 메시지 전송 함수
def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)


# 메시지 저장 함수
def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})


def paint_history():
    for message in st.session_state["messages"]:
        send_message(
            message["message"],
            message["role"],
            save=False,
        )


llm_api_key = llm_api_key = st.secrets["OPENAI_API_KEY"]


# 11주차 내용 llm 설정


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
    "당신은 학습자의 감정과 상황을 깊이 이해할 수 있는 공감 능력을 가진 한국의 중학교 영어문법 선생님이에요.\n"
    "제공되는 맥락 정보를 참고하여 학습자가 영어 문법 문제에서 정답을 맞췄는지 파악하고,\n"
    "한국어로 공감하는 말을 두 문장으로 표현해줘요.\n"
    "정답인 경우: 학습자의 문제 특성을 고려하여 성취감을 높일 수 있는 공감을 제공해요.\n"
    "오답인 경우: 학습자가 문제를 풀 때 겪은 어려움을 고려하여 공감을 제공해요."
)


FEEDBACK_SYSTEM = (
    "당신은 중학교 영어문법 선생님입니다. 대화 내역을 보고, 추가 질문에 대해 성심성의껏 답변해요.\n"
    "학생의 질문에 대한 답은 가장 최근에 푼 문제에 대해서만 제공해요."
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


# 과거 기록이 붙은 chain 만들기
empathy_with_history = RunnableWithMessageHistory(
    empathy_chain,
    get_shared_history,
    input_messages_key="learning_context",
    history_messages_key="history", # get_shared_history에서 가져온 대화 이력(ChatMessageHistory.messages)을 MessagesPlaceholder("history") 자리에 넣기”
)


feedback_with_history = RunnableWithMessageHistory(
    feedback_chain,
    get_shared_history,
    input_messages_key="follow_up_question",
    history_messages_key="history",
)


if "qid" not in st.session_state:
    st.session_state.qid = 1

# 다른 세션 변수들은 항상 초기화 확인
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "selected" not in st.session_state:
    st.session_state.selected = None
if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.now()
if "learning_feedback" not in st.session_state:
    st.session_state.learning_feedback = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False
if "learning_history" not in st.session_state:
    st.session_state.learning_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# 진행 상태 저장 (추가)
save_progress(st.session_state.user_id, st.session_state.qid)

DF_PATH = "questions.xlsx"
df = load_data(DF_PATH)

# 파일 상단에 경로 설정================================
IMAGE_FOLDER = "image/"

# 문제 표시 부분 (기존 코드 아래에 추가)
row = df.iloc[st.session_state.qid - 1]
st.write("**가장 적절한 답을 고르시오.**")
st.write(f"{st.session_state.qid}. {row['Question']}")

# 이미지 표시 추가
if 'Image' in row.index and pd.notna(row.get('Image')) and str(row['Image']).strip():
    image_path = IMAGE_FOLDER + str(row['Image']).strip()
    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_path, caption="영상 소견", width=350)
    except:
        st.warning(f"이미지를 불러올 수 없습니다: {row['Image']}")

        
# 보기 구성==========================================
choices = [c.strip() for c in str(row["Choices"]).split(",")]

# 제출 전/후 라디오 인덱스
if st.session_state.submitted and st.session_state.selected in choices:
    radio_index = choices.index(st.session_state.selected)
else:
    radio_index = None

# 라디오 (제출 후엔 비활성화)
selected = st.radio(
    "선택하세요",
    options=choices,
    index=radio_index,
    label_visibility="collapsed",
    disabled=st.session_state.submitted,
    key="current_radio",
    on_change=on_choice_change )

# 제출 & 다음
if not st.session_state.submitted:
    if st.button("정답 제출", type="primary"):
        if selected is None:
            st.warning("👉 답을 선택해주세요.")
        else:
            st.session_state.selected = selected
            st.session_state.submitted = True
            solving_time = (datetime.now() - st.session_state.start_time).total_seconds()
            is_correct = (str(selected).strip() == str(row["Answer"]).strip())
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
   
    #11주차 내용
    follow_up_question = st.chat_input("궁금한 점을 입력하세요...")
    if follow_up_question:
        paint_history()
        follow_up(follow_up_question)

    if st.session_state.qid == len(df):
        if st.button("✅ 완료"):
            log_user_action(
                action="end",
                user_id=st.session_state.user_id,
                question_id=st.session_state.qid
            )
            st.success("모든 문제를 완료했습니다. 수고하셨어요! 🎉")
            st.switch_page("pages/2_대쉬보드.py")
    else:
        if st.button("다음 문제 ▶"):
            st.session_state.qid += 1
            save_progress(st.session_state.user_id, st.session_state.qid)
            st.session_state.submitted = False
            st.session_state.selected = None
            st.session_state.start_time = datetime.now()
            st.session_state.learning_feedback = None
            st.session_state.feedback_given = False
            st.session_state.messages = []
            log_user_action(
                action="start_question",
                user_id=st.session_state.user_id,
                question_id=st.session_state.qid
            )
            st.rerun()
