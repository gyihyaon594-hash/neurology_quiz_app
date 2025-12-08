from datetime import datetime, timezone
import streamlit as st
import pandas as pd

# MongoDB 대신 세션 기반 저장 (Streamlit Cloud용)

def register_user(user_id, phone):
    """사용자 등록 (세션에 저장)"""
    if "registrations" not in st.session_state:
        st.session_state.registrations = []
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "phone": phone
    }
    st.session_state.registrations.append(log_entry)
    print(f"User registered: {user_id}")

def log_user_action(action, user_id, question_id=None, selected_choice=None, correct=None,
                    solving_time=None, content=None):
    """사용자 행동 로그 (세션에 저장)"""
    if "user_logs" not in st.session_state:
        st.session_state.user_logs = []
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "question_id": question_id,
        "action": action
    }
    
    if selected_choice is not None:
        log_entry["selected_choice"] = selected_choice
    if correct is not None:
        log_entry["correct"] = correct
    if solving_time is not None:
        log_entry["solving_time"] = solving_time
    if content is not None:
        log_entry["content"] = content
    
    st.session_state.user_logs.append(log_entry)
    print(f"Action: {action}, User: {user_id}, Question: {question_id}")

def get_user_logs(user_id, sort_asc=True):
    """특정 user_id의 로그 반환"""
    if "user_logs" not in st.session_state:
        return []
    
    logs = [log for log in st.session_state.user_logs if log["user_id"] == user_id]
    logs.sort(key=lambda x: x["timestamp"], reverse=not sort_asc)
    return logs

def to_df(logs):
    return pd.DataFrame(list(logs))

