import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="문제 관리", page_icon="📝")

CATEGORIES = {
    "Headache": "두통",
    "Stroke": "뇌졸중",
    "Sleep Disorders": "수면장애",
    "Movement Disorders": "이상운동",
    "Dementia": "치매",
    "Dizziness": "어지럼증",
    "Neuromuscular": "근골격계",
    "CNS Infection": "중추신경계감염",
    "Epilepsy": "뇌전증",
    "Neurocritical Care": "신경계 중환자"
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

def add_question(data):
    sheet = get_questions_sheet()
    question_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([
        question_id, data['category'], data['question'], data['choices'], data['answer'],
        data['feedback_1'], data['feedback_2'], data['feedback_3'], data['feedback_4'], data['feedback_5'],
        data['difficulty'], data['image_url'], data['video_url'], "윤지환", created_at
    ])
    return question_id

def get_all_questions():
    sheet = get_questions_sheet()
    return sheet.get_all_records()

def delete_question(question_id):
    sheet = get_questions_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(question_id):
            sheet.delete_rows(idx + 1)
            return True
    return False

def update_question(question_id, data):
    sheet = get_questions_sheet()
    all_data = sheet.get_all_values()
    for idx, row in enumerate(all_data):
        if str(row[0]) == str(question_id):
            sheet.update(f'B{idx+1}:M{idx+1}', [[
                data['category'], data['question'], data['choices'], data['answer'],
                data['feedback_1'], data['feedback_2'], data['feedback_3'], 
                data['feedback_4'], data['feedback_5'],
                data['difficulty'], data['image_url'], data['video_url']
            ]])
            return True
    return False

# ============ UI ============
st.title("📝 문제 관리")

# 인증
if 'quiz_admin_authorized' not in st.session_state:
    st.session_state.quiz_admin_authorized = False
if 'edit_question_id' not in st.session_state:
    st.session_state.edit_question_id = None

if not st.session_state.quiz_admin_authorized:
    st.subheader("🔐 관리자 인증")
    
    col1, col2 = st.columns(2)
    with col1:
        input_name = st.text_input("이름")
    with col2:
        input_code = st.text_input("인증코드", type="password")
    
    if st.button("인증", type="primary"):
        if input_name == "윤지환" and input_code == "8664":
            st.session_state.quiz_admin_authorized = True
            st.success("인증되었습니다!")
            st.rerun()
        else:
            st.error("인증 정보가 올바르지 않습니다.")
else:
    st.success("✅ 관리자 인증됨")
    
    tab1, tab2 = st.tabs(["➕ 문제 등록", "📋 문제 관리"])
    
    # 탭 1: 문제 등록
    with tab1:
        st.subheader("새 문제 등록")
        
        category = st.selectbox("분과 선택", options=list(CATEGORIES.keys()),
                               format_func=lambda x: f"{x} ({CATEGORIES[x]})")
        
        question = st.text_area("문제", height=100, placeholder="문제를 입력하세요...")
        
        st.markdown("**보기 입력** (쉼표로 구분)")
        choices = st.text_input("보기", placeholder="보기1, 보기2, 보기3, 보기4, 보기5")
        
        answer = st.text_input("정답", placeholder="정답 보기를 정확히 입력하세요")
        
        st.markdown("**보기별 피드백**")
        col1, col2 = st.columns(2)
        with col1:
            feedback_1 = st.text_area("보기 1 선택 시 피드백", height=80, key="fb1")
            feedback_3 = st.text_area("보기 3 선택 시 피드백", height=80, key="fb3")
            feedback_5 = st.text_area("보기 5 선택 시 피드백", height=80, key="fb5")
        with col2:
            feedback_2 = st.text_area("보기 2 선택 시 피드백", height=80, key="fb2")
            feedback_4 = st.text_area("보기 4 선택 시 피드백", height=80, key="fb4")
        
        difficulty = st.selectbox("난이도", options=[1, 2, 3, 4, 5], index=2)
        
        image_url = st.text_input("이미지 URL (선택)", placeholder="https://...")
        video_url = st.text_input("동영상 URL (선택)", placeholder="https://youtube.com/...")
        
        # 미리보기
        if image_url:
            try:
                st.image(image_url, caption="이미지 미리보기", width=300)
            except:
                st.warning("이미지를 불러올 수 없습니다.")
        
        if st.button("문제 등록", type="primary"):
            if question.strip() and choices.strip() and answer.strip():
                data = {
                    'category': category,
                    'question': question,
                    'choices': choices,
                    'answer': answer,
                    'feedback_1': feedback_1,
                    'feedback_2': feedback_2,
                    'feedback_3': feedback_3,
                    'feedback_4': feedback_4,
                    'feedback_5': feedback_5,
                    'difficulty': difficulty,
                    'image_url': image_url,
                    'video_url': video_url
                }
                question_id = add_question(data)
                st.success(f"문제가 등록되었습니다! (ID: {question_id})")
                st.balloons()
            else:
                st.warning("문제, 보기, 정답을 모두 입력해주세요.")
    
    # 탭 2: 문제 관리
    with tab2:
        st.subheader("등록된 문제 목록")
        
        # 분과 필터
        filter_cat = st.selectbox("분과 필터", options=["All"] + list(CATEGORIES.keys()),
                                  format_func=lambda x: "전체" if x == "All" else f"{x} ({CATEGORIES[x]})")
        
        questions = get_all_questions()
        
        if filter_cat != "All":
            questions = [q for q in questions if q.get('category') == filter_cat]
        
        if not questions:
            st.info("등록된 문제가 없습니다.")
        else:
            for q in questions:
                q_id = q['id']
                is_editing = st.session_state.edit_question_id == q_id
                
                with st.container():
                    if is_editing:
                        st.markdown("### ✏️ 문제 수정")
                        
                        edit_cat = st.selectbox("분과", options=list(CATEGORIES.keys()),
                                               index=list(CATEGORIES.keys()).index(q['category']) if q['category'] in CATEGORIES else 0,
                                               key=f"edit_cat_{q_id}")
                        edit_question = st.text_area("문제", value=q['question'], key=f"edit_q_{q_id}")
                        edit_choices = st.text_input("보기", value=q['choices'], key=f"edit_ch_{q_id}")
                        edit_answer = st.text_input("정답", value=q['answer'], key=f"edit_ans_{q_id}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{q_id}", type="primary"):
                                update_data = {
                                    'category': edit_cat,
                                    'question': edit_question,
                                    'choices': edit_choices,
                                    'answer': edit_answer,
                                    'feedback_1': q.get('feedback_1', ''),
                                    'feedback_2': q.get('feedback_2', ''),
                                    'feedback_3': q.get('feedback_3', ''),
                                    'feedback_4': q.get('feedback_4', ''),
                                    'feedback_5': q.get('feedback_5', ''),
                                    'difficulty': q.get('difficulty', 3),
                                    'image_url': q.get('image_url', ''),
                                    'video_url': q.get('video_url', '')
                                }
                                update_question(q_id, update_data)
                                st.session_state.edit_question_id = None
                                st.success("수정되었습니다!")
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{q_id}"):
                                st.session_state.edit_question_id = None
                                st.rerun()
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            st.markdown(f"**[{CATEGORIES.get(q['category'], q['category'])}]** {q['question'][:50]}...")
                            st.caption(f"정답: {q['answer']} | 난이도: {q.get('difficulty', '-')}")
                        with col2:
                            if st.button("✏️", key=f"edit_{q_id}"):
                                st.session_state.edit_question_id = q_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️", key=f"del_{q_id}"):
                                st.session_state[f"confirm_del_{q_id}"] = True
                        
                        if st.session_state.get(f"confirm_del_{q_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ 예", key=f"yes_{q_id}"):
                                    delete_question(q_id)
                                    st.session_state[f"confirm_del_{q_id}"] = False
                                    st.rerun()
                            with c2:
                                if st.button("❌ 아니오", key=f"no_{q_id}"):
                                    st.session_state[f"confirm_del_{q_id}"] = False
                                    st.rerun()
                    
                    st.divider()
    
    st.divider()
    if st.button("로그아웃"):
        st.session_state.quiz_admin_authorized = False
        st.rerun()
