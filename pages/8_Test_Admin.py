import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

st.set_page_config(page_title="검사자료 관리", page_icon="🔬")

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

def add_material(data):
    sheet = get_neurotest_sheet()
    material_id = datetime.now().strftime('%Y%m%d%H%M%S')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([
        material_id, data['category'], data['title'], data['content'], data['image_url'],
        data['video_url'], "윤지환", created_at, data['order'], data['type']
    ])
    return material_id

def get_all_materials():
    sheet = get_neurotest_sheet()
    return sheet.get_all_records()

def delete_material(material_id):
    sheet = get_neurotest_sheet()
    data = sheet.get_all_values()
    for idx, row in enumerate(data):
        if str(row[0]) == str(material_id):
            sheet.delete_rows(idx + 1)
            return True
    return False

def update_material(material_id, data):
    sheet = get_neurotest_sheet()
    all_data = sheet.get_all_values()
    for idx, row in enumerate(all_data):
        if str(row[0]) == str(material_id):
            sheet.update(f'B{idx+1}:J{idx+1}', [[
                data['category'], data['title'], data['content'], data['image_url'],
                data['video_url'], row[6], row[7], data['order'], data['type']
            ]])
            return True
    return False

# ============ UI ============
st.title("🔬 검사자료 관리")
st.write("임상신경생리검사 및 SNSB 학습 자료를 등록합니다.")

# 인증
if 'neurotest_admin_authorized' not in st.session_state:
    st.session_state.neurotest_admin_authorized = False
if 'edit_material_id' not in st.session_state:
    st.session_state.edit_material_id = None

if not st.session_state.neurotest_admin_authorized:
    st.subheader("🔐 관리자 인증")
    
    col1, col2 = st.columns(2)
    with col1:
        input_name = st.text_input("이름")
    with col2:
        input_code = st.text_input("인증코드", type="password")
    
    if st.button("인증", type="primary"):
        if input_name == "윤지환" and input_code == "8664":
            st.session_state.neurotest_admin_authorized = True
            st.success("인증되었습니다!")
            st.rerun()
        else:
            st.error("인증 정보가 올바르지 않습니다.")
else:
    st.success("✅ 관리자 인증됨")
    
    tab1, tab2 = st.tabs(["➕ 자료 등록", "📋 자료 관리"])
    
    # 탭 1: 자료 등록
    with tab1:
        st.subheader("새 자료 등록")
        
        category = st.selectbox(
            "검사 종류 선택", 
            options=list(NEURO_TESTS.keys()),
            format_func=lambda x: f"{NEURO_TESTS[x]} ({x})"
        )
        
        title = st.text_input("제목", placeholder="자료 제목을 입력하세요...")
        
        content = st.text_area(
            "내용 (마크다운 지원)", 
            height=200, 
            placeholder="학습 내용을 입력하세요...\n\n마크다운 문법 사용 가능:\n- **굵게**, *기울임*\n- ## 제목\n- - 목록"
        )
        
        material_type = st.selectbox(
            "자료 유형",
            options=["lecture", "case", "reference", "video"],
            format_func=lambda x: {
                "lecture": "📚 강의자료",
                "case": "🏥 증례",
                "reference": "📖 참고자료",
                "video": "🎬 동영상"
            }.get(x, x)
        )
        
        order = st.number_input("정렬 순서", min_value=1, value=1, help="숫자가 작을수록 먼저 표시됩니다")
        
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
                st.image(uploaded_image, caption="미리보기", width=400)
                st.info("💡 '자료 등록' 버튼을 누르면 imgBB에 이미지가 업로드됩니다.")
                
        elif image_option == "URL 직접 입력":
            image_url = st.text_input("이미지 URL", placeholder="https://...", key="new_img_url")
            if image_url:
                try:
                    st.image(image_url, caption="이미지 미리보기", width=400)
                except:
                    st.warning("이미지를 불러올 수 없습니다.")
        
        # ⭐ 동영상 URL 입력
        st.markdown("---")
        st.markdown("### 🎬 동영상 첨부")
        video_url = st.text_input("YouTube URL (선택)", placeholder="https://youtube.com/watch?v=...", key="new_video")
        if video_url:
            try:
                st.video(video_url)
            except:
                st.warning("동영상을 불러올 수 없습니다.")
        
        # 내용 미리보기
        if content:
            with st.expander("📄 내용 미리보기"):
                st.markdown(content)
        
        st.markdown("---")
        
        if st.button("자료 등록", type="primary"):
            if title.strip() and content.strip():
                final_image_url = image_url
                
                # 파일 업로드 처리
                if image_option == "파일 업로드 (imgBB 저장)" and uploaded_image:
                    with st.spinner("이미지를 imgBB에 업로드 중..."):
                        uploaded_url = upload_image_to_imgbb(uploaded_image)
                        if uploaded_url:
                            final_image_url = uploaded_url
                            st.success("이미지 업로드 완료!")
                        else:
                            st.warning("이미지 업로드 실패. 자료는 이미지 없이 등록됩니다.")
                
                data = {
                    'category': category,
                    'title': title,
                    'content': content,
                    'image_url': final_image_url,
                    'video_url': video_url,
                    'order': order,
                    'type': material_type
                }
                material_id = add_material(data)
                st.success(f"자료가 등록되었습니다! (ID: {material_id})")
                st.balloons()
                st.cache_data.clear()
            else:
                st.warning("제목과 내용을 모두 입력해주세요.")
    
    # 탭 2: 자료 관리
    with tab2:
        st.subheader("등록된 자료 목록")
        
        # 검사 필터
        filter_cat = st.selectbox(
            "검사 필터", 
            options=["All"] + list(NEURO_TESTS.keys()),
            format_func=lambda x: "전체" if x == "All" else f"{NEURO_TESTS[x]} ({x})"
        )
        
        materials = get_all_materials()
        
        if filter_cat != "All":
            materials = [m for m in materials if m.get('category') == filter_cat]
        
        if not materials:
            st.info("등록된 자료가 없습니다.")
        else:
            # 정렬
            materials = sorted(materials, key=lambda x: (x.get('category', ''), x.get('order', 999)))
            
            for m in materials:
                m_id = m['id']
                is_editing = st.session_state.edit_material_id == m_id
                
                with st.container():
                    if is_editing:
                        st.markdown("### ✏️ 자료 수정")
                        
                        edit_cat = st.selectbox(
                            "검사 종류", 
                            options=list(NEURO_TESTS.keys()),
                            index=list(NEURO_TESTS.keys()).index(m['category']) if m['category'] in NEURO_TESTS else 0,
                            key=f"edit_cat_{m_id}"
                        )
                        edit_title = st.text_input("제목", value=m['title'], key=f"edit_title_{m_id}")
                        edit_content = st.text_area("내용", value=m['content'], height=150, key=f"edit_content_{m_id}")
                        edit_order = st.number_input("정렬 순서", value=int(m.get('order', 1)), min_value=1, key=f"edit_ord_{m_id}")
                        edit_type = st.selectbox(
                            "자료 유형",
                            options=["lecture", "case", "reference", "video"],
                            index=["lecture", "case", "reference", "video"].index(m.get('type', 'lecture')) if m.get('type') in ["lecture", "case", "reference", "video"] else 0,
                            key=f"edit_type_{m_id}"
                        )
                        
                        # ⭐ 이미지 수정 섹션
                        st.markdown("---")
                        st.markdown("### 🖼️ 이미지 수정")
                        
                        current_img = str(m.get('image_url', '') or '')
                        
                        # 현재 이미지 항상 표시
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
                            ["유지", "파일 업로드 (imgBB 저장)", "URL 변경", "삭제"],
                            horizontal=True,
                            key=f"edit_img_opt_{m_id}"
                        )
                        
                        edit_image_url = current_img
                        new_image_file = None
                        
                        if edit_img_option == "파일 업로드 (imgBB 저장)":
                            new_image_file = st.file_uploader(
                                "새 이미지 선택",
                                type=['png', 'jpg', 'jpeg', 'gif'],
                                key=f"edit_img_file_{m_id}"
                            )
                            if new_image_file:
                                st.markdown("**새로 업로드할 이미지:**")
                                st.image(new_image_file, caption="새 이미지 미리보기", width=400)
                                st.info("💡 '저장' 버튼을 누르면 imgBB에 이미지가 업로드됩니다.")
                        
                        elif edit_img_option == "URL 변경":
                            edit_image_url = st.text_input("이미지 URL", value=current_img, key=f"edit_img_url_{m_id}")
                            if edit_image_url and edit_image_url != current_img:
                                st.markdown("**새 URL 이미지 미리보기:**")
                                try:
                                    st.image(edit_image_url, caption="미리보기", width=400)
                                except:
                                    st.warning("이미지를 불러올 수 없습니다.")
                        
                        elif edit_img_option == "삭제":
                            edit_image_url = ""
                            st.warning("⚠️ 저장 시 이미지가 삭제됩니다.")
                        
                        # ⭐ 동영상 수정 섹션
                        st.markdown("---")
                        st.markdown("### 🎬 동영상 수정")
                        
                        current_video = str(m.get('video_url', '') or '')
                        
                        # 현재 동영상 항상 표시
                        if current_video:
                            st.markdown("**현재 등록된 동영상:**")
                            try:
                                st.video(current_video)
                            except:
                                st.warning("현재 동영상을 불러올 수 없습니다.")
                                st.caption(f"URL: {current_video}")
                        else:
                            st.info("현재 등록된 동영상이 없습니다.")
                        
                        edit_video_url = st.text_input("YouTube URL", value=current_video, key=f"edit_video_{m_id}")
                        if edit_video_url and edit_video_url != current_video:
                            st.markdown("**새 동영상 미리보기:**")
                            try:
                                st.video(edit_video_url)
                            except:
                                st.warning("동영상을 불러올 수 없습니다.")
                        
                        st.markdown("---")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{m_id}", type="primary"):
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
                                            final_image_url = current_img
                                
                                update_data = {
                                    'category': edit_cat,
                                    'title': edit_title,
                                    'content': edit_content,
                                    'image_url': final_image_url,
                                    'video_url': edit_video_url,
                                    'order': edit_order,
                                    'type': edit_type
                                }
                                update_material(m_id, update_data)
                                st.session_state.edit_material_id = None
                                st.cache_data.clear()
                                st.success("수정되었습니다!")
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{m_id}"):
                                st.session_state.edit_material_id = None
                                st.rerun()
                    
                    else:
                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            cat_name = NEURO_TESTS.get(m['category'], m['category'])
                            type_emoji = {"lecture": "📚", "case": "🏥", "reference": "📖", "video": "🎬"}.get(m.get('type', ''), "📄")
                            # 이미지/동영상 아이콘 추가
                            media_icons = []
                            if m.get('image_url'):
                                media_icons.append("🖼️")
                            if m.get('video_url'):
                                media_icons.append("🎬")
                            media_str = " ".join(media_icons)
                            
                            st.markdown(f"**[{cat_name}]** {type_emoji} {m['title'][:50]}{'...' if len(m['title']) > 50 else ''}")
                            st.caption(f"순서: {m.get('order', '-')} | 등록: {m.get('created_at', '-')} {media_str}")
                        with col2:
                            if st.button("✏️", key=f"edit_{m_id}"):
                                st.session_state.edit_material_id = m_id
                                st.rerun()
                        with col3:
                            if st.button("🗑️", key=f"del_{m_id}"):
                                st.session_state[f"confirm_del_{m_id}"] = True
                        
                        if st.session_state.get(f"confirm_del_{m_id}", False):
                            st.warning("정말 삭제하시겠습니까?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ 예", key=f"yes_{m_id}"):
                                    delete_material(m_id)
                                    st.session_state[f"confirm_del_{m_id}"] = False
                                    st.cache_data.clear()
                                    st.rerun()
                            with c2:
                                if st.button("❌ 아니오", key=f"no_{m_id}"):
                                    st.session_state[f"confirm_del_{m_id}"] = False
                                    st.rerun()
                    
                    st.divider()
    
    st.divider()
    if st.button("로그아웃"):
        st.session_state.neurotest_admin_authorized = False
        st.rerun()
