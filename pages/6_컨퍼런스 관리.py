import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="새글 작성", page_icon="✍️")

# 로그인 체크
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
st.title("✍️ 새글 작성")
st.write("Morning Conference에 새 글을 등록합니다.")

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
        
        # 이미지 URL 입력
        image_url = st.text_input(
            "이미지 URL (선택)",
            placeholder="https://... 형식의 이미지 주소를 입력하세요",
            key="new_image_url"
        )
        
        # 이미지 미리보기
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
                add_comment("윤지환", content_above, content_below, image_url)
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
                        
                        edit_url = st.text_input(
                            "이미지 URL",
                            value=post.get('image_url') or post.get('image_name', ''),
                            key=f"edit_url_{post_id}"
                        )
                        
                        if edit_url:
                            try:
                                st.image(edit_url, caption="미리보기", use_container_width=True)
                            except:
                                pass
                        
                        edit_below = st.text_area(
                            "이미지 아래 내용",
                            value=post.get('content_below', ''),
                            height=100,
                            key=f"edit_below_{post_id}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{post_id}", type="primary"):
                                update_post(post_id, edit_above, edit_below, edit_url)
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
                            st.markdown(f"**{content[:50]}{'...' if len(content) > 50 else ''}**")
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

