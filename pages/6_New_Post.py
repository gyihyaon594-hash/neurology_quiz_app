import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

st.set_page_config(page_title="컨퍼런스 관리", page_icon="✍️")

# 로그인 체크
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

# ⭐ Google Drive에 이미지 업로드
def upload_image_to_drive(image_file):
    """Google Drive에 이미지 업로드하고 URL 반환"""
    try:
        credentials = get_google_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # 파일 메타데이터
        file_metadata = {
            'name': f"conference_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.name}",
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

def get_conference_sheet():
    client = get_sheets_client()
    sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        return spreadsheet.worksheet("conference")
    except:
        worksheet = spreadsheet.add_worksheet(title="conference", rows=1000, cols=6)
        worksheet.append_row(["id", "author", "content_above", "content_below", "created_at", "image_url"])
        return worksheet

def add_comment(author, content_above, content_below, image_url=""):
    """글 추가"""
    sheet = get_conference_sheet()
    comment_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([comment_id, author, content_above, content_below, created_at, image_url])

def get_all_posts():
    """모든 글 가져오기"""
    sheet = get_conference_sheet()
    data = sheet.get_all_records()
    return data

def delete_post(post_id):
    """글 삭제"""
    sheet = get_conference_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(post_id):
            sheet.delete_rows(idx + 1)
            return True
    return False

def update_post(post_id, content_above, content_below, image_url=""):
    """글 수정"""
    sheet = get_conference_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(post_id):
            sheet.update_cell(idx + 1, 3, content_above)
            sheet.update_cell(idx + 1, 4, content_below)
            sheet.update_cell(idx + 1, 6, image_url)
            return True
    return False

# ============ UI ============
st.title("✍️ 컨퍼런스 관리")
st.write("Morning Conference에 새 컨퍼런스 내용을 등록합니다.")

st.divider()

# 인증 상태 확인
if 'write_authorized' not in st.session_state:
    st.session_state.write_authorized = False
if 'edit_post_id' not in st.session_state:
    st.session_state.edit_post_id = None

# 인증되지 않은 경우
if not st.session_state.write_authorized:
    st.subheader("🔐 인증")
    st.write("글 작성 권한이 필요합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        input_name = st.text_input("이름", placeholder="이름을 입력하세요")
    with col2:
        input_code = st.text_input("인증코드", type="password", placeholder="인증코드 입력")
    
    if st.button("인증", type="primary"):
        if input_name == "윤지환" and input_code == "8664":
            st.session_state.write_authorized = True
            st.success("인증되었습니다!")
            st.rerun()
        else:
            st.error("인증 정보가 올바르지 않습니다.")

# 인증된 경우
else:
    st.success("✅ 인증됨: 윤지환")
    
    tab1, tab2 = st.tabs(["✍️ 새글 작성", "📝 글 관리"])
    
    # 탭 1: 새글 작성
    with tab1:
        st.divider()
        
        content_above = st.text_area(
            "이미지 위 내용",
            placeholder="이미지 위에 표시할 내용을 입력하세요...",
            height=100,
            key="new_content_above"
        )
        
        # ⭐ 이미지 업로드 섹션
        st.markdown("### 🖼️ 이미지 첨부")
        
        image_option = st.radio(
            "이미지 추가 방법",
            ["없음", "파일 업로드 (Google Drive 저장)", "URL 직접 입력"],
            horizontal=True,
            key="new_img_option"
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
                st.image(uploaded_image, caption="미리보기", use_container_width=True)
                st.info("💡 '등록' 버튼을 누르면 Google Drive에 이미지가 업로드됩니다.")
                
        elif image_option == "URL 직접 입력":
            image_url = st.text_input(
                "이미지 URL",
                placeholder="https://... 형식의 이미지 주소를 입력하세요",
                key="new_image_url"
            )
            if image_url:
                try:
                    st.image(image_url, caption="미리보기", use_container_width=True)
                except:
                    st.warning("이미지를 불러올 수 없습니다. URL을 확인해주세요.")
        
        content_below = st.text_area(
            "이미지 아래 내용 (선택)",
            placeholder="이미지 아래에 표시할 내용을 입력하세요...",
            height=100,
            key="new_content_below"
        )
        
        if st.button("등록", type="primary"):
            if content_above.strip() or content_below.strip():
                final_image_url = image_url
                
                # 파일 업로드 처리
                if image_option == "파일 업로드 (Google Drive 저장)" and uploaded_image:
                    with st.spinner("이미지를 Google Drive에 업로드 중..."):
                        uploaded_url = upload_image_to_drive(uploaded_image)
                        if uploaded_url:
                            final_image_url = uploaded_url
                            st.success("이미지 업로드 완료!")
                        else:
                            st.warning("이미지 업로드 실패. 글은 이미지 없이 등록됩니다.")
                
                add_comment("윤지환", content_above, content_below, final_image_url)
                st.success("등록되었습니다!")
                time.sleep(1)
                st.switch_page("pages/3_Morning Conference.py")
            else:
                st.warning("내용을 입력해주세요.")
    
    # 탭 2: 글 관리
    with tab2:
        st.divider()
        
        posts = get_all_posts()
        
        if not posts:
            st.info("등록된 글이 없습니다.")
        else:
            posts = sorted(posts, key=lambda x: x['id'], reverse=True)
            
            for post in posts:
                post_id = post['id']
                content = post.get('content_above') or post.get('content', '')
                is_editing = st.session_state.edit_post_id == post_id
                
                with st.container():
                    if is_editing:
                        st.markdown("### ✏️ 글 수정")
                        
                        edit_above = st.text_area(
                            "이미지 위 내용",
                            value=post.get('content_above', ''),
                            height=100,
                            key=f"edit_above_{post_id}"
                        )
                        
                        # ⭐ 이미지 수정 섹션
                        st.markdown("### 🖼️ 이미지 수정")
                        
                        current_img = str(post.get('image_url') or post.get('image_name', '') or '')
                        if current_img:
                            st.markdown("**현재 이미지:**")
                            try:
                                st.image(current_img, use_container_width=True)
                            except:
                                st.warning("현재 이미지를 불러올 수 없습니다.")
                        
                        edit_img_option = st.radio(
                            "이미지 변경",
                            ["유지", "새 파일 업로드", "URL 변경", "삭제"],
                            horizontal=True,
                            key=f"edit_img_opt_{post_id}"
                        )
                        
                        edit_image_url = current_img
                        new_image_file = None
                        
                        if edit_img_option == "새 파일 업로드":
                            new_image_file = st.file_uploader(
                                "새 이미지 선택",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                key=f"edit_img_file_{post_id}"
                            )
                            if new_image_file:
                                st.image(new_image_file, caption="새 이미지 미리보기", use_container_width=True)
                        
                        elif edit_img_option == "URL 변경":
                            edit_image_url = st.text_input(
                                "이미지 URL",
                                value=current_img,
                                key=f"edit_url_{post_id}"
                            )
                            if edit_image_url:
                                try:
                                    st.image(edit_image_url, caption="미리보기", use_container_width=True)
                                except:
                                    pass
                        
                        elif edit_img_option == "삭제":
                            edit_image_url = ""
                            st.info("저장 시 이미지가 삭제됩니다.")
                        
                        edit_below = st.text_area(
                            "이미지 아래 내용",
                            value=post.get('content_below', ''),
                            height=100,
                            key=f"edit_below_{post_id}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{post_id}", type="primary"):
                                final_image_url = edit_image_url
                                
                                # 새 이미지 업로드 처리
                                if edit_img_option == "새 파일 업로드" and new_image_file:
                                    with st.spinner("이미지를 Google Drive에 업로드 중..."):
                                        uploaded_url = upload_image_to_drive(new_image_file)
                                        if uploaded_url:
                                            final_image_url = uploaded_url
                                            st.success("이미지 업로드 완료!")
                                        else:
                                            st.warning("이미지 업로드 실패. 기존 이미지 유지.")
                                            final_image_url = current_img
                                
                                update_post(post_id, edit_above, edit_below, final_image_url)
                                st.session_state.edit_post_id = None
                                st.success("수정되었습니다!")
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{post_id}"):
                                st.session_state.edit_post_id = None
                                st.rerun()
                    
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            # 이미지 아이콘 표시
                            has_image = post.get('image_url') or post.get('image_name', '')
                            image_icon = " 🖼️" if has_image else ""
                            st.markdown(f"**{content[:50]}{'...' if len(content) > 50 else ''}**{image_icon}")
                            st.caption(f"{post['author']} · {post['created_at']}")
                        with col2:
                            if st.button("✏️ 수정", key=f"edit_{post_id}"):
                                st.session_state.edit_post_id = post_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️ 삭제", key=f"del_{post_id}"):
                                st.session_state[f"confirm_delete_{post_id}"] = True
                        
                        if st.session_state.get(f"confirm_delete_{post_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 예", key=f"yes_{post_id}"):
                                    delete_post(post_id)
                                    st.session_state[f"confirm_delete_{post_id}"] = False
                                    st.success("삭제되었습니다.")
                                    time.sleep(1)
                                    st.rerun()
                            with col2:
                                if st.button("❌ 아니오", key=f"no_{post_id}"):
                                    st.session_state[f"confirm_delete_{post_id}"] = False
                                    st.rerun()
                    
                    st.divider()
    
    st.divider()
    if st.button("로그아웃"):
        st.session_state.write_authorized = False
        st.session_state.edit_post_id = None
        st.rerun()
