import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

st.set_page_config(page_title="문제 관리", page_icon="📝")

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

# Google API 연결
def get_google_credentials():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return credentials

def get_sheets_client():
    credentials = get_google_credentials()
    return gspread.authorize(credentials)

# Google Drive에 이미지 업로드
def upload_image_to_drive(image_file):
    """Google Drive에 이미지 업로드하고 URL 반환"""
    try:
        credentials = get_google_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # 파일 메타데이터
        file_metadata = {
            'name': f"quiz_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.name}",
            'mimeType': image_file.type
        }
        
        # 파일 업로드
        media = MediaIoBaseUpload(
            io.BytesIO(image_file.read()),
            mimetype=image_file.type,
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # 파일을 공개로 설정
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # 직접 접근 가능한 URL 반환
        image_url = f"https://drive.google.com/uc?id={file_id}"
        
        return image_url
    
    except Exception as e:
        st.error(f"이미지 업로드 오류: {e}")
        return None

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
                               format_func=lambda x: f"{CATEGORIES[x]} ({x})")
        
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
        
        # 이미지 업로드 섹션
        st.markdown("---")
        st.markdown("### 🖼️ 이미지 첨부")
        
        image_option = st.radio(
            "이미지 추가 방법",
            ["없음", "파일 업로드 (Google Drive 저장)", "URL 직접 입력"],
            horizontal=True,
            key="img_option"
        )
        
        image_url = ""
        uploaded_image = None
        
        if image_option == "파일 업로드 (Google Drive 저장)":
            uploaded_image = st.file_uploader(
                "이미지 파일 선택", 
                type=['png', 'jpg', 'jpeg', 'gif'],
                key="new_img_upload"
            )
            if uploaded_image:
                st.image(uploaded_image, caption="미리보기", width=300)
                st.info("💡 '문제 등록' 버튼을 누르면 Google Drive에 이미지가 업로드됩니다.")
                
        elif image_option == "URL 직접 입력":
            image_url = st.text_input("이미지 URL", placeholder="https://...", key="new_img_url")
            if image_url:
                try:
                    st.image(image_url, caption="미리보기", width=300)
                except:
                    st.warning("이미지를 불러올 수 없습니다.")
        
        # 동영상 URL 입력
        st.markdown("### 🎬 동영상 첨부")
        video_url = st.text_input("YouTube URL (선택)", placeholder="https://youtube.com/watch?v=...", key="new_video")
        if video_url:
            try:
                st.video(video_url)
            except:
                st.warning("동영상을 불러올 수 없습니다.")
        
        st.markdown("---")
        
        if st.button("문제 등록", type="primary"):
            if question.strip() and choices.strip() and answer.strip():
                final_image_url = image_url
                
                # 파일 업로드 처리
                if image_option == "파일 업로드 (Google Drive 저장)" and uploaded_image:
                    with st.spinner("이미지를 Google Drive에 업로드 중..."):
                        uploaded_url = upload_image_to_drive(uploaded_image)
                        if uploaded_url:
                            final_image_url = uploaded_url
                            st.success("이미지 업로드 완료!")
                        else:
                            st.warning("이미지 업로드 실패. 문제는 이미지 없이 등록됩니다.")
                
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
                    'image_url': final_image_url,
                    'video_url': video_url
                }
                question_id = add_question(data)
                st.success(f"문제가 등록되었습니다! (ID: {question_id})")
                st.balloons()
                st.cache_data.clear()
            else:
                st.warning("문제, 보기, 정답을 모두 입력해주세요.")
    
    # 탭 2: 문제 관리
    with tab2:
        st.subheader("등록된 문제 목록")
        
        filter_cat = st.selectbox("분과 필터", options=["All"] + list(CATEGORIES.keys()),
                                  format_func=lambda x: "전체" if x == "All" else f"{CATEGORIES[x]} ({x})")
        
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
                        edit_difficulty = st.selectbox("난이도", options=[1, 2, 3, 4, 5], 
                                                       index=int(q.get('difficulty', 3)) - 1,
                                                       key=f"edit_diff_{q_id}")
                        
                        st.markdown("**보기별 피드백**")
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_fb1 = st.text_area("보기 1 피드백", value=q.get('feedback_1', ''), height=60, key=f"edit_fb1_{q_id}")
                            edit_fb3 = st.text_area("보기 3 피드백", value=q.get('feedback_3', ''), height=60, key=f"edit_fb3_{q_id}")
                            edit_fb5 = st.text_area("보기 5 피드백", value=q.get('feedback_5', ''), height=60, key=f"edit_fb5_{q_id}")
                        with col2:
                            edit_fb2 = st.text_area("보기 2 피드백", value=q.get('feedback_2', ''), height=60, key=f"edit_fb2_{q_id}")
                            edit_fb4 = st.text_area("보기 4 피드백", value=q.get('feedback_4', ''), height=60, key=f"edit_fb4_{q_id}")
                        
                        # 이미지 수정
                        st.markdown("---")
                        st.markdown("### 🖼️ 이미지 수정")
                        
                        current_img = str(q.get('image_url', '') or '')
                        
                        # 현재 이미지 표시 (항상 보이도록)
                        if current_img:
                            st.markdown("**현재 등록된 이미지:**")
                            try:
                                st.image(current_img, width=400)
                            except:
                                st.warning("현재 이미지를 불러올 수 없습니다.")
                                st.caption(f"URL: {current_img}")
                        else:
                            st.info("현재 등록된 이미지가 없습니다.")
                        
                        edit_img_option = st.radio(
                            "이미지 변경",
                            ["유지", "파일 업로드 (Google Drive 저장)", "URL 변경", "삭제"],
                            horizontal=True,
                            key=f"edit_img_opt_{q_id}"
                        )
                        
                        edit_image_url = current_img
                        new_image_file = None
                        
                        if edit_img_option == "파일 업로드 (Google Drive 저장)":
                            new_image_file = st.file_uploader(
                                "새 이미지 선택",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                key=f"edit_img_file_{q_id}"
                            )
                            if new_image_file:
                                st.markdown("**새로 업로드할 이미지:**")
                                st.image(new_image_file, caption="새 이미지 미리보기", width=400)
                                st.info("💡 '저장' 버튼을 누르면 Google Drive에 이미지가 업로드됩니다.")
                        
                        elif edit_img_option == "URL 변경":
                            edit_image_url = st.text_input("이미지 URL", value=current_img, key=f"edit_img_url_{q_id}")
                            if edit_image_url and edit_image_url != current_img:
                                st.markdown("**새 URL 이미지 미리보기:**")
                                try:
                                    st.image(edit_image_url, caption="미리보기", width=400)
                                except:
                                    st.warning("이미지를 불러올 수 없습니다.")
                        
                        elif edit_img_option == "삭제":
                            edit_image_url = ""
                            st.warning("⚠️ 저장 시 이미지가 삭제됩니다.")
                        
                        # 동영상 수정
                        st.markdown("---")
                        st.markdown("### 🎬 동영상 수정")
                        current_video = str(q.get('video_url', '') or '')
                        
                        if current_video:
                            st.markdown("**현재 등록된 동영상:**")
                            try:
                                st.video(current_video)
                            except:
                                st.warning("현재 동영상을 불러올 수 없습니다.")
                        
                        edit_video_url = st.text_input("YouTube URL", value=current_video, key=f"edit_video_{q_id}")
                        if edit_video_url and edit_video_url != current_video:
                            st.markdown("**새 동영상 미리보기:**")
                            try:
                                st.video(edit_video_url)
                            except:
                                st.warning("동영상을 불러올 수 없습니다.")
                        
                        st.markdown("---")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{q_id}", type="primary"):
                                final_image_url = edit_image_url
                                
                                if edit_img_option == "파일 업로드 (Google Drive 저장)" and new_image_file:
                                    with st.spinner("이미지를 Google Drive에 업로드 중..."):
                                        uploaded_url = upload_image_to_drive(new_image_file)
                                        if uploaded_url:
                                            final_image_url = uploaded_url
                                            st.success("이미지 업로드 완료!")
                                        else:
                                            st.warning("이미지 업로드 실패. 기존 이미지 유지.")
                                            final_image_url = current_img
                                
                                update_data = {
                                    'category': edit_cat,
                                    'question': edit_question,
                                    'choices': edit_choices,
                                    'answer': edit_answer,
                                    'feedback_1': edit_fb1,
                                    'feedback_2': edit_fb2,
                                    'feedback_3': edit_fb3,
                                    'feedback_4': edit_fb4,
                                    'feedback_5': edit_fb5,
                                    'difficulty': edit_difficulty,
                                    'image_url': final_image_url,
                                    'video_url': edit_video_url
                                }
                                update_question(q_id, update_data)
                                st.session_state.edit_question_id = None
                                st.success("수정되었습니다!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{q_id}"):
                                st.session_state.edit_question_id = None
                                st.rerun()
                    
                    # ⭐ 목록 표시 (수정 모드가 아닐 때)
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            cat_name = CATEGORIES.get(q['category'], q['category'])
                            st.markdown(f"**[{cat_name}]** {q['question'][:50]}...")
                            media_info = []
                            if q.get('image_url'):
                                media_info.append("🖼️")
                            if q.get('video_url'):
                                media_info.append("🎬")
                            media_str = " ".join(media_info) if media_info else ""
                            st.caption(f"정답: {q['answer']} | 난이도: {q.get('difficulty', '-')} {media_str}")
                        with col2:
                            if st.button("✏️", key=f"edit_{q_id}"):
                                st.session_state.edit_question_id = q_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️", key=f"del_{q_id}"):
                                st.session_state[f"confirm_del_{q_id}"] = True
                        
                        # 삭제 확인
                        if st.session_state.get(f"confirm_del_{q_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ 예", key=f"yes_{q_id}"):
                                    delete_question(q_id)
                                    st.session_state[f"confirm_del_{q_id}"] = False
                                    st.cache_data.clear()
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
