import streamlit as st
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

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
        
        st.markdown("---")
        st.markdown("**미디어 (선택사항)**")
        
        image_url = st.text_input("이미지 URL", placeholder="https://...")
        video_url = st.text_input("동영상 URL", placeholder="https://youtube.com/...")
        
        # 미리보기
        if image_url:
            try:
                st.image(image_url, caption="이미지 미리보기", width=400)
            except:
                st.warning("이미지를 불러올 수 없습니다.")
        
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
                data = {
                    'category': category,
                    'title': title,
                    'content': content,
                    'image_url': image_url,
                    'video_url': video_url,
                    'order': order,
                    'type': material_type
                }
                material_id = add_material(data)
                st.success(f"자료가 등록되었습니다! (ID: {material_id})")
                st.balloons()
                # 캐시 클리어
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
                        edit_image = st.text_input("이미지 URL", value=m.get('image_url', ''), key=f"edit_img_{m_id}")
                        edit_video = st.text_input("동영상 URL", value=m.get('video_url', ''), key=f"edit_vid_{m_id}")
                        edit_order = st.number_input("정렬 순서", value=int(m.get('order', 1)), min_value=1, key=f"edit_ord_{m_id}")
                        edit_type = st.selectbox(
                            "자료 유형",
                            options=["lecture", "case", "reference", "video"],
                            index=["lecture", "case", "reference", "video"].index(m.get('type', 'lecture')) if m.get('type') in ["lecture", "case", "reference", "video"] else 0,
                            key=f"edit_type_{m_id}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 저장", key=f"save_{m_id}", type="primary"):
                                update_data = {
                                    'category': edit_cat,
                                    'title': edit_title,
                                    'content': edit_content,
                                    'image_url': edit_image,
                                    'video_url': edit_video,
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
                            st.markdown(f"**[{cat_name}]** {type_emoji} {m['title'][:50]}{'...' if len(m['title']) > 50 else ''}")
                            st.caption(f"순서: {m.get('order', '-')} | 등록: {m.get('created_at', '-')}")
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
