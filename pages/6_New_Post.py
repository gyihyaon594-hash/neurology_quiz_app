import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

st.set_page_config(page_title="컨퍼런스 관리", page_icon="✍️")

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

# ⭐ imgBB에 이미지 업로드
def upload_image_to_imgbb(image_file):
    """imgBB에 이미지 업로드하고 URL 반환"""
    try:
        api_key = st.secrets.get("imgbb", {}).get("api_key", "")
        
        if not api_key:
            st.error("imgBB API 키가 설정되지 않았습니다.")
            return None
        
        # 파일 포인터를 처음으로 되돌림
        image_file.seek(0)
        
        # 이미지를 base64로 인코딩
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # imgBB API 호출
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": api_key,
                "image": image_data,
                "name": image_file.name
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['data']['url']
            else:
                st.error(f"업로드 실패: {result.get('error', {}).get('message', '알 수 없는 오류')}")
                return None
        else:
            st.error(f"HTTP 오류: {response.status_code}")
            return None
            
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
        worksheet.append_row(["id", "author", "content", "created_at", "image_url", "video_url"])
        return worksheet

def add_post(author, content, image_url="", video_url=""):
    """글 추가"""
    sheet = get_conference_sheet()
    post_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 컬럼 순서: id, author, content, created_at, image_url, video_url
    sheet.append_row([post_id, author, content, created_at, image_url, video_url])
    return post_id

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

def update_post(post_id, content, image_url="", video_url=""):
    """글 수정"""
    sheet = get_conference_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(post_id):
            sheet.update_cell(idx + 1, 3, content)      # C열: content
            sheet.update_cell(idx + 1, 5, image_url)    # E열: image_url
            sheet.update_cell(idx + 1, 6, video_url)    # F열: video_url
            return True
    return False

def is_valid_url(url):
    """유효한 URL인지 확인"""
    if not url:
        return False
    url = str(url).strip()
    if url in ['', 'nan', 'None']:
        return False
    if url.startswith('http://') or url.startswith('https://'):
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
        
        content = st.text_area(
            "내용",
            placeholder="컨퍼런스 내용을 입력하세요...",
            height=150,
            key="new_content"
        )
        
        # ⭐ 이미지 업로드 섹션
        st.markdown("---")
        st.markdown("### 🖼️ 이미지 첨부")
        
        image_option = st.radio(
            "이미지 추가 방법",
            ["없음", "파일 업로드 (imgBB 저장)", "URL 직접 입력"],
            horizontal=True,
            key="new_img_option"
        )
        
        image_url = ""
        uploaded_image = None
        
        if image_option == "파일 업로드 (imgBB 저장)":
            uploaded_image = st.file_uploader(
                "이미지 파일 선택", 
                type=['png', 'jpg', 'jpeg', 'gif'],
                key="new_img_upload"
            )
            if uploaded_image:
                st.image(uploaded_image, caption="미리보기", use_container_width=True)
                st.info("💡 '등록' 버튼을 누르면 imgBB에 이미지가 업로드됩니다.")
                
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
        
        # ⭐ 동영상 URL 입력
        st.markdown("---")
        st.markdown("### 🎬 동영상 첨부")
        video_url = st.text_input("YouTube URL (선택)", placeholder="https://youtube.com/watch?v=...", key="new_video")
        if video_url:
            try:
                st.video(video_url)
            except:
                st.warning("동영상을 불러올 수 없습니다.")
        
        st.markdown("---")
        
        if st.button("등록", type="primary"):
            if content.strip():
                final_image_url = image_url
                
                # 파일 업로드 처리
                if image_option == "파일 업로드 (imgBB 저장)" and uploaded_image:
                    with st.spinner("이미지를 imgBB에 업로드 중..."):
                        uploaded_url = upload_image_to_imgbb(uploaded_image)
                        if uploaded_url:
                            final_image_url = uploaded_url
                            st.success(f"이미지 업로드 완료!")
                        else:
                            st.warning("이미지 업로드 실패. 글은 이미지 없이 등록됩니다.")
                
                post_id = add_post("윤지환", content, final_image_url, video_url)
                st.success(f"등록되었습니다! (ID: {post_id})")
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.warning("내용을 입력해주세요.")
    
    # 탭 2: 글 관리
    with tab2:
        st.divider()
        
        if st.button("🔄 새로고침"):
            st.cache_data.clear()
            st.rerun()
        
        posts = get_all_posts()
        
        if not posts:
            st.info("등록된 글이 없습니다.")
        else:
            posts = sorted(posts, key=lambda x: x['id'], reverse=True)
            
            st.markdown(f"**총 {len(posts)}개의 글**")
            
            for post in posts:
                post_id = post['id']
                content = post.get('content', '') or post.get('content_above', '')
                is_editing = st.session_state.edit_post_id == post_id
                
                with st.container():
                    if is_editing:
                        st.markdown("### ✏️ 글 수정")
                        
                        edit_content = st.text_area(
                            "내용",
                            value=content,
                            height=150,
                            key=f"edit_content_{post_id}"
                        )
                        
                        # ⭐ 이미지 수정 섹션
                        st.markdown("---")
                        st.markdown("### 🖼️ 이미지 수정")
                        
                        current_img = str(post.get('image_url', '') or post.get('image_name', '') or '').strip()
                        
                        # 현재 이미지 표시 (URL 유효성 검사)
                        if is_valid_url(current_img):
                            st.markdown("**현재 등록된 이미지:**")
                            try:
                                st.image(current_img, use_container_width=True)
                            except:
                                st.warning("현재 이미지를 불러올 수 없습니다.")
                                st.caption(f"URL: {current_img}")
                        else:
                            st.info("현재 등록된 이미지가 없습니다.")
                        
                        edit_img_option = st.radio(
                            "이미지 변경",
                            ["유지", "파일 업로드 (imgBB 저장)", "URL 변경", "삭제"],
                            horizontal=True,
                            key=f"edit_img_opt_{post_id}"
                        )
                        
                        edit_image_url = current_img if is_valid_url(current_img) else ""
                        new_image_file = None
                        
                        if edit_img_option == "파일 업로드 (imgBB 저장)":
                            new_image_file = st.file_uploader(
                                "새 이미지 선택",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                key=f"edit_img_file_{post_id}"
                            )
                            if new_image_file:
                                st.markdown("**새로 업로드할 이미지:**")
                                st.image(new_image_file, caption="새 이미지 미리보기", use_container_width=True)
                                st.info("💡 '저장' 버튼을 누르면 imgBB에 이미지가 업로드됩니다.")
                        
                        elif edit_img_option == "URL 변경":
                            edit_image_url = st.text_input(
                                "이미지 URL",
                                value=current_img if is_valid_url(current_img) else "",
                                key=f"edit_url_{post_id}"
                            )
                            if edit_image_url and edit_image_url != current_img:
                                st.markdown("**새 URL 이미지 미리보기:**")
                                try:
                                    st.image(edit_image_url, caption="미리보기", use_container_width=True)
                                except:
                                    st.warning("이미지를 불러올 수 없습니다.")
                        
                        elif edit_img_option == "삭제":
                            edit_image_url = ""
                            st.warning("⚠️ 저장 시 이미지가 삭제됩니다.")
                        
                        # ⭐ 동영상 수정 섹션
                        st.markdown("---")
                        st.markdown("### 🎬 동영상 수정")
                        
                        current_video = str(post.get('video_url', '') or '').strip()
                        
                        # 현재 동영상 표시
                        if is_valid_url(current_video):
                            st.markdown("**현재 등록된 동영상:**")
                            try:
                                st.video(current_video)
                            except:
                                st.warning("현재 동영상을 불러올 수 없습니다.")
                                st.caption(f"URL: {current_video}")
                        else:
                            st.info("현재 등록된 동영상이 없습니다.")
                        
                        edit_video_url = st.text_input(
                            "YouTube URL", 
                            value=current_video if is_valid_url(current_video) else "",
                            key=f"edit_video_{post_id}"
                        )
                        if edit_video_url and edit_video_url != current_video and is_valid_url(edit_video_url):
                            st.markdown("**새 동영상 미리보기:**")
                            try:
                                st.video(edit_video_url)
                            except:
                                st.warning("동영상을 불러올 수 없습니다.")
                        
                        st.markdown("---")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{post_id}", type="primary"):
                                final_image_url = edit_image_url
                                
                                # 새 이미지 업로드 처리
                                if edit_img_option == "파일 업로드 (imgBB 저장)" and new_image_file:
                                    with st.spinner("이미지를 imgBB에 업로드 중..."):
                                        uploaded_url = upload_image_to_imgbb(new_image_file)
                                        if uploaded_url:
                                            final_image_url = uploaded_url
                                            st.success("이미지 업로드 완료!")
                                        else:
                                            st.warning("이미지 업로드 실패. 기존 이미지 유지.")
                                            final_image_url = current_img if is_valid_url(current_img) else ""
                                
                                update_post(post_id, edit_content, final_image_url, edit_video_url)
                                st.session_state.edit_post_id = None
                                st.success("수정되었습니다!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{post_id}"):
                                st.session_state.edit_post_id = None
                                st.rerun()
                    
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            # 이미지/동영상 아이콘 표시
                            media_icons = []
                            if is_valid_url(post.get('image_url', '') or post.get('image_name', '')):
                                media_icons.append("🖼️")
                            if is_valid_url(post.get('video_url', '')):
                                media_icons.append("🎬")
                            media_str = " ".join(media_icons)
                            
                            st.markdown(f"**{content[:50]}{'...' if len(content) > 50 else ''}** {media_str}")
                            st.caption(f"{post['author']} · {post['created_at']}")
                        with col2:
                            if st.button("✏️", key=f"edit_{post_id}"):
                                st.session_state.edit_post_id = post_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️", key=f"del_{post_id}"):
                                st.session_state[f"confirm_delete_{post_id}"] = True
                        
                        if st.session_state.get(f"confirm_delete_{post_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 예", key=f"yes_{post_id}"):
                                    delete_post(post_id)
                                    st.session_state[f"confirm_delete_{post_id}"] = False
                                    st.success("삭제되었습니다.")
                                    st.cache_data.clear()
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
