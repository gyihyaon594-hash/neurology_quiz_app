import streamlit as st
import pandas as pd
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

st.set_page_config(page_title="임상신경생리검사 및 SNSB", page_icon="🧠")

# 검사 카테고리 정의
NEURO_TESTS = {
    "NCS": "1. 신경전도검사",
    "EMG": "2. 침근전도검사",
    "EP": "3. 유발전위검사",
    "ANS": "4. 자율신경계기능검사",
    "EEG": "5. 뇌파",
    "TCD": "6. 뇌혈류초음파",
    "Carotid": "7. 경동맥초음파",
    "VOG_VNG": "8. VOG & VNG",
    "SNSB": "9. SNSB",
    "Gait": "10. 보행검사"
}

def require_login():
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.warning("등록이 필요합니다")
        time.sleep(3)
        st.switch_page("app.py")

require_login()

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

def get_neurotest_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("neurotest")
    except:
        worksheet = spreadsheet.add_worksheet(title="neurotest", rows=1000, cols=10)
        worksheet.append_row([
            "id", "category", "title", "content", "image_url", 
            "video_url", "author", "created_at", "order", "type"
        ])
        return worksheet

# ⭐ 댓글 시트 함수
def get_neurotest_comments_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("neurotest_comments")
    except:
        worksheet = spreadsheet.add_worksheet(title="neurotest_comments", rows=1000, cols=6)
        worksheet.append_row(["id", "material_id", "author", "content", "created_at", "parent_id"])
        return worksheet

def add_comment(material_id, author, content, parent_id=""):
    """댓글 추가"""
    sheet = get_neurotest_comments_sheet()
    comment_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([comment_id, str(material_id), author, content, created_at, parent_id])
    return comment_id

def get_comments_by_material(material_id):
    """특정 자료의 댓글 가져오기"""
    sheet = get_neurotest_comments_sheet()
    data = sheet.get_all_records()
    comments = [c for c in data if str(c.get('material_id', '')) == str(material_id)]
    return sorted(comments, key=lambda x: x.get('created_at', ''), reverse=True)

def delete_comment(comment_id):
    """댓글 삭제"""
    sheet = get_neurotest_comments_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(comment_id):
            sheet.delete_rows(idx + 1)
            return True
    return False

@st.cache_data(ttl=300)
def load_all_materials():
    try:
        sheet = get_neurotest_sheet()
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_materials_by_category(df, category):
    if df.empty:
        return pd.DataFrame()
    filtered = df[df['category'] == category]
    if 'order' in filtered.columns:
        filtered = filtered.sort_values('order')
    return filtered.reset_index(drop=True)

def get_category_counts(df):
    if df.empty:
        return {cat: 0 for cat in NEURO_TESTS.keys()}
    counts = df['category'].value_counts().to_dict()
    return {cat: counts.get(cat, 0) for cat in NEURO_TESTS.keys()}

# ⭐ LLM 설정
llm_api_key = st.secrets["OPENAI_API_KEY"]

tutor_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=llm_api_key,
    model_kwargs={"frequency_penalty": 0, "presence_penalty": 0.9},
)

TUTOR_SYSTEM = """당신은 신경과 전문의이자 임상신경생리학 전문가입니다. 
현재 학습자가 보고 있는 자료에 대해 친절하고 명확하게 답변해주세요.

현재 학습 자료 정보:
- 검사 종류: {category}
- 제목: {title}
- 내용: {content}

학습자의 질문에 대해:
1. 자료 내용과 관련지어 설명해주세요
2. 임상적 의의를 포함해주세요
3. 필요시 추가 학습 포인트를 제안해주세요
4. 한국어로 답변해주세요"""

tutor_prompt = ChatPromptTemplate.from_messages([
    ("system", TUTOR_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])

tutor_chain = tutor_prompt | tutor_model

# 세션별 대화 기록 관리
if "neurotest_history_store" not in st.session_state:
    st.session_state.neurotest_history_store = {}

def get_neurotest_history(session_id: str) -> ChatMessageHistory:
    store = st.session_state.neurotest_history_store
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

tutor_with_history = RunnableWithMessageHistory(
    tutor_chain,
    get_neurotest_history,
    input_messages_key="question",
    history_messages_key="history",
)

# 채팅 관련 함수
def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)

def save_message(message, role):
    st.session_state["neurotest_messages"].append({"message": message, "role": role})

def paint_history():
    for message in st.session_state["neurotest_messages"]:
        send_message(message["message"], message["role"], save=False)

def ask_tutor(question, item):
    """AI 튜터에게 질문"""
    send_message(question, "human", save=True)
    
    try:
        session_id = f"{st.session_state.user_id}_{item.get('id', 'unknown')}"
        
        response = tutor_with_history.invoke(
            {
                "category": NEURO_TESTS.get(item.get('category', ''), item.get('category', '')),
                "title": item.get('title', ''),
                "content": item.get('content', '')[:2000],  # 토큰 제한
                "question": question
            },
            config={"configurable": {"session_id": session_id}}
        )
        
        answer = response.content
        
        with st.chat_message("ai"):
            st.markdown(answer)
            save_message(answer, "ai")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# 세션 상태 초기화
if "selected_neurotest" not in st.session_state:
    st.session_state.selected_neurotest = None
if "neurotest_item_idx" not in st.session_state:
    st.session_state.neurotest_item_idx = 0
if "neurotest_messages" not in st.session_state:
    st.session_state.neurotest_messages = []
if "show_comments" not in st.session_state:
    st.session_state.show_comments = False

# ============ UI ============
st.title("🧠 임상신경생리검사 및 SNSB")

all_materials_df = load_all_materials()

# 카테고리 미선택 시
if st.session_state.selected_neurotest is None:
    st.subheader("📋 검사 종류를 선택하세요")
    
    category_counts = get_category_counts(all_materials_df)
    
    items = list(NEURO_TESTS.items())
    
    for i in range(0, len(items), 2):
        col1, col2 = st.columns(2)
        
        cat_en, cat_kr = items[i]
        with col1:
            count = category_counts.get(cat_en, 0)
            if st.button(
                f"📖 {cat_kr} 자료 {count}개", 
                key=f"neuro_{cat_en}",
                use_container_width=True
            ):
                st.session_state.selected_neurotest = cat_en
                st.session_state.neurotest_item_idx = 0
                st.session_state.neurotest_messages = []
                st.rerun()
        
        if i + 1 < len(items):
            cat_en, cat_kr = items[i + 1]
            with col2:
                count = category_counts.get(cat_en, 0)
                if st.button(
                    f"📖 {cat_kr} 자료 {count}개", 
                    key=f"neuro_{cat_en}",
                    use_container_width=True
                ):
                    st.session_state.selected_neurotest = cat_en
                    st.session_state.neurotest_item_idx = 0
                    st.session_state.neurotest_messages = []
                    st.rerun()
    
    st.divider()
    if st.button("🔄 자료 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 카테고리 선택됨
else:
    category = st.session_state.selected_neurotest
    df = get_materials_by_category(all_materials_df, category)
    
    with st.sidebar:
        st.markdown(f"**현재 검사:** {NEURO_TESTS.get(category, category)}")
        if st.button("🔙 검사 목록으로"):
            st.session_state.selected_neurotest = None
            st.session_state.neurotest_item_idx = 0
            st.session_state.neurotest_messages = []
            st.rerun()
    
    st.subheader(f"📁 {NEURO_TESTS.get(category, category)}")
    
    if df.empty:
        st.info("아직 등록된 자료가 없습니다.")
        
        st.markdown("---")
        st.markdown(f"### {NEURO_TESTS.get(category, category)} 학습 자료")
        st.markdown("""
        이 섹션에서는 다음 내용을 학습할 수 있습니다:
        - 검사 원리 및 방법
        - 정상 소견
        - 이상 소견 해석
        - 임상 적용
        
        *자료는 '검사자료 관리' 페이지에서 등록할 수 있습니다.*
        """)
    else:
        total_items = len(df)
        current_idx = st.session_state.neurotest_item_idx
        
        if current_idx >= total_items:
            st.session_state.neurotest_item_idx = 0
            current_idx = 0
        
        item = df.iloc[current_idx]
        material_id = item.get('id', '')
        
        st.caption(f"자료 {current_idx + 1} / {total_items}")
        st.markdown(f"## {item.get('title', '제목 없음')}")
        
        # 이미지 표시
        image_url = str(item.get('image_url', '') or '').strip()
        if image_url and image_url != 'nan' and image_url != '':
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                try:
                    st.image(image_url, use_container_width=True)
                except Exception as e:
                    st.warning(f"이미지 로드 실패: {e}")
        
        # 동영상 표시
        video_url = str(item.get('video_url', '') or '').strip()
        if video_url and video_url != 'nan' and video_url != '':
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                try:
                    st.video(video_url)
                except Exception as e:
                    st.warning(f"동영상 로드 실패: {e}")
        
        # 내용 표시
        content = item.get('content', '')
        if content:
            st.markdown(content)
        
        st.divider()
        
        # 네비게이션
        if total_items > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if current_idx > 0:
                    if st.button("◀ 이전"):
                        st.session_state.neurotest_item_idx -= 1
                        st.session_state.neurotest_messages = []
                        st.rerun()
            with col2:
                titles = [f"{i+1}. {df.iloc[i].get('title', '제목 없음')[:20]}" for i in range(total_items)]
                selected_title = st.selectbox(
                    "자료 선택",
                    options=titles,
                    index=current_idx,
                    label_visibility="collapsed"
                )
                new_idx = titles.index(selected_title)
                if new_idx != current_idx:
                    st.session_state.neurotest_item_idx = new_idx
                    st.session_state.neurotest_messages = []
                    st.rerun()
            with col3:
                if current_idx < total_items - 1:
                    if st.button("다음 ▶"):
                        st.session_state.neurotest_item_idx += 1
                        st.session_state.neurotest_messages = []
                        st.rerun()
        
        # ⭐ AI 질문 & 댓글 탭
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🤖 AI에게 질문", "💬 댓글"])
        
        # 탭 1: AI 질문
        with tab1:
            st.markdown("##### 이 자료에 대해 궁금한 점을 물어보세요")
            
            # 대화 기록 표시
            paint_history()
            
            # 질문 입력
            question = st.chat_input("질문을 입력하세요...", key="neurotest_question")
            if question:
                ask_tutor(question, item)
            
            # 대화 초기화 버튼
            if st.session_state.neurotest_messages:
                if st.button("🗑️ 대화 초기화"):
                    st.session_state.neurotest_messages = []
                    # 히스토리 스토어도 초기화
                    session_id = f"{st.session_state.user_id}_{material_id}"
                    if session_id in st.session_state.neurotest_history_store:
                        st.session_state.neurotest_history_store[session_id] = ChatMessageHistory()
                    st.rerun()
        
        # 탭 2: 댓글
        with tab2:
            st.markdown("##### 다른 학습자들과 의견을 나눠보세요")
            
            # 댓글 작성
            new_comment = st.text_area(
                "댓글 작성",
                placeholder="질문이나 의견을 남겨주세요...",
                height=80,
                key=f"comment_input_{material_id}",
                label_visibility="collapsed"
            )
            
            if st.button("💬 댓글 등록", key=f"submit_comment_{material_id}"):
                if new_comment.strip():
                    add_comment(material_id, st.session_state.user_id, new_comment.strip())
                    st.success("댓글이 등록되었습니다!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("댓글 내용을 입력해주세요.")
            
            st.markdown("---")
            
            # 댓글 목록
            comments = get_comments_by_material(material_id)
            
            if not comments:
                st.info("아직 댓글이 없습니다. 첫 번째 댓글을 남겨보세요!")
            else:
                st.markdown(f"**댓글 {len(comments)}개**")
                
                for comment in comments:
                    with st.container():
                        col1, col2 = st.columns([6, 1])
                        
                        with col1:
                            st.markdown(f"**{comment['author']}** · {comment['created_at']}")
                            st.markdown(comment['content'])
                        
                        with col2:
                            # 본인 댓글만 삭제 가능
                            if comment['author'] == st.session_state.user_id:
                                if st.button("🗑️", key=f"del_comment_{comment['id']}"):
                                    st.session_state[f"confirm_del_comment_{comment['id']}"] = True
                        
                        # 삭제 확인
                        if st.session_state.get(f"confirm_del_comment_{comment['id']}", False):
                            st.warning("댓글을 삭제하시겠습니까?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("예", key=f"yes_del_{comment['id']}"):
                                    delete_comment(comment['id'])
                                    st.session_state[f"confirm_del_comment_{comment['id']}"] = False
                                    st.rerun()
                            with c2:
                                if st.button("아니오", key=f"no_del_{comment['id']}"):
                                    st.session_state[f"confirm_del_comment_{comment['id']}"] = False
                                    st.rerun()
                        
                        st.markdown("---")
