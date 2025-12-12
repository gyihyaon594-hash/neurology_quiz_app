import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

st.set_page_config(page_title="Morning Conference", page_icon="🏥", layout="wide")

# 로그인 체크
def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.rerun()

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

def get_conference_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("conference")
    except:
        worksheet = spreadsheet.add_worksheet(title="conference", rows=1000, cols=6)
        worksheet.append_row(["id", "author", "content", "created_at", "image_urls", "video_url"])
        return worksheet

def get_replies_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("replies")
    except:
        worksheet = spreadsheet.add_worksheet(title="replies", rows=1000, cols=5)
        worksheet.append_row(["reply_id", "post_id", "author", "content", "created_at"])
        return worksheet

@st.cache_data(ttl=300)
def get_all_posts():
    sheet = get_conference_sheet()
    data = sheet.get_all_records()
    return data

def get_replies(post_id):
    sheet = get_replies_sheet()
    data = sheet.get_all_records()
    return [r for r in data if str(r['post_id']) == str(post_id)]

def add_reply(post_id, author, content):
    sheet = get_replies_sheet()
    reply_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([reply_id, post_id, author, content, created_at])

def is_valid_url(url):
    if not url:
        return False
    url = str(url).strip()
    if url in ['', 'nan', 'None']:
        return False
    return url.startswith('http://') or url.startswith('https://')

def parse_image_urls(image_urls_str):
    if not image_urls_str:
        return []
    urls = str(image_urls_str).split(',')
    return [url.strip() for url in urls if is_valid_url(url.strip())]

# ⭐ LLM 설정
llm_api_key = st.secrets["OPENAI_API_KEY"]

tutor_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=llm_api_key,
    model_kwargs={"frequency_penalty": 0, "presence_penalty": 0.9},
)

TUTOR_SYSTEM = """당신은 신경과 전문의이자 의학 교육 전문가입니다.
현재 학습자가 보고 있는 Morning Conference 케이스에 대해 친절하고 명확하게 답변해주세요.

현재 케이스 정보:
{case_content}

학습자의 질문에 대해:
1. 케이스 내용과 관련지어 설명해주세요
2. 임상적 의의와 감별진단을 포함해주세요
3. 필요시 추가 검사나 치료 방향을 제안해주세요
4. 한국어로 답변해주세요
5. 의학적으로 정확한 정보를 제공해주세요"""

tutor_prompt = ChatPromptTemplate.from_messages([
    ("system", TUTOR_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])

tutor_chain = tutor_prompt | tutor_model

# 세션별 대화 기록 관리
if "conference_history_store" not in st.session_state:
    st.session_state.conference_history_store = {}

def get_conference_history(session_id: str) -> ChatMessageHistory:
    store = st.session_state.conference_history_store
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

tutor_with_history = RunnableWithMessageHistory(
    tutor_chain,
    get_conference_history,
    input_messages_key="question",
    history_messages_key="history",
)

# 채팅 관련 함수
def get_chat_messages(post_id):
    """특정 글의 AI 채팅 메시지 가져오기"""
    key = f"conference_chat_{post_id}"
    if key not in st.session_state:
        st.session_state[key] = []
    return st.session_state[key]

def add_chat_message(post_id, message, role):
    """AI 채팅 메시지 추가"""
    key = f"conference_chat_{post_id}"
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key].append({"message": message, "role": role})

def clear_chat_messages(post_id):
    """AI 채팅 메시지 초기화"""
    key = f"conference_chat_{post_id}"
    st.session_state[key] = []
    # 히스토리 스토어도 초기화
    session_id = f"{st.session_state.user_id}_conference_{post_id}"
    if session_id in st.session_state.conference_history_store:
        st.session_state.conference_history_store[session_id] = ChatMessageHistory()

def ask_ai(question, post_id, case_content):
    """AI에게 질문"""
    try:
        session_id = f"{st.session_state.user_id}_conference_{post_id}"
        
        response = tutor_with_history.invoke(
            {
                "case_content": case_content[:3000],  # 토큰 제한
                "question": question
            },
            config={"configurable": {"session_id": session_id}}
        )
        
        return response.content
    except Exception as e:
        return f"오류가 발생했습니다: {e}"

# ============ UI ============
st.title("🏥 Morning Conference")

# 새로고침 버튼
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# 글 목록
posts = get_all_posts()

if not posts:
    st.info("아직 등록된 글이 없습니다.")
else:
    posts = sorted(posts, key=lambda x: x['id'], reverse=True)
    
    for post in posts:
        with st.container():
            post_id = post['id']
            
            st.caption(f"{post.get('author', '')} · {post.get('created_at', '')}")
            
            content = post.get('content', '') or post.get('content_above', '') or ''
            if content:
                st.markdown(f"## {content}")
            
            # 이미지 표시
            image_urls_str = str(post.get('image_urls', '') or post.get('image_url', '') or post.get('image_name', '') or '')
            image_urls = parse_image_urls(image_urls_str)
            
            if image_urls:
                if len(image_urls) == 1:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        try:
                            st.image(image_urls[0], use_container_width=True)
                        except:
                            st.warning("이미지를 불러올 수 없습니다.")
                else:
                    num_cols = min(len(image_urls), 2)
                    outer_col1, outer_col2, outer_col3 = st.columns([1, 4, 1])
                    with outer_col2:
                        for i in range(0, len(image_urls), num_cols):
                            cols = st.columns(num_cols)
                            for j in range(num_cols):
                                if i + j < len(image_urls):
                                    with cols[j]:
                                        try:
                                            st.image(image_urls[i + j], use_container_width=True)
                                            st.caption(f"이미지 {i + j + 1}/{len(image_urls)}")
                                        except:
                                            st.warning(f"이미지 {i + j + 1} 로드 실패")
            
            # 동영상 표시
            video_url = str(post.get('video_url', '') or '').strip()
            if is_valid_url(video_url):
                col1, col2, col3 = st.columns([1, 3, 1])
                with col2:
                    try:
                        st.video(video_url)
                    except:
                        st.warning("동영상을 불러올 수 없습니다.")
            
            content_below = post.get('content_below', '')
            if content_below:
                st.markdown(f"**{content_below}**")
            
            # ⭐ AI 질문 & 의견 탭
            st.markdown("---")
            
            tab1, tab2 = st.tabs(["🤖 AI에게 질문", "💬 의견"])
            
            # 탭 1: AI 질문
            with tab1:
                st.markdown("##### 이 케이스에 대해 궁금한 점을 물어보세요")
                
                # 기존 대화 표시
                chat_messages = get_chat_messages(post_id)
                for msg in chat_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["message"])
                
                # 질문 입력
                question = st.chat_input("질문을 입력하세요...", key=f"ai_question_{post_id}")
                if question:
                    # 사용자 메시지 추가
                    add_chat_message(post_id, question, "human")
                    with st.chat_message("human"):
                        st.markdown(question)
                    
                    # AI 응답
                    with st.chat_message("ai"):
                        with st.spinner("생각 중..."):
                            answer = ask_ai(question, post_id, content)
                        st.markdown(answer)
                        add_chat_message(post_id, answer, "ai")
                
                # 대화 초기화 버튼
                if chat_messages:
                    if st.button("🗑️ 대화 초기화", key=f"clear_chat_{post_id}"):
                        clear_chat_messages(post_id)
                        st.rerun()
            
            # 탭 2: 의견 (기존 댓글)
            with tab2:
                st.markdown("##### 다른 학습자들과 의견을 나눠보세요")
                
                # 기존 댓글 표시
                replies = get_replies(post_id)
                if replies:
                    for reply in replies:
                        st.markdown(f"**{reply['author']}** · {reply['created_at']}")
                        st.markdown(f"{reply['content']}")
                        st.markdown("")
                else:
                    st.info("아직 의견이 없습니다. 첫 번째 의견을 남겨보세요!")
                
                # 새 댓글 입력
                col1, col2 = st.columns([5, 1])
                with col1:
                    new_reply = st.text_input(
                        "의견 입력",
                        placeholder="의견을 입력하세요...",
                        key=f"reply_{post_id}",
                        label_visibility="collapsed"
                    )
                with col2:
                    if st.button("등록", key=f"btn_{post_id}"):
                        if new_reply.strip():
                            add_reply(post_id, st.session_state.user_id, new_reply)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning("내용을 입력해주세요.")
            
            st.divider()
