
"""Small local authentication helpers for CogniGraph."""
from __future__ import annotations
import streamlit as st
from storage import authenticate, create_user, get_or_create_demo_course, init_db

def ensure_auth_state():
    init_db()
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("course_id", None)
    st.session_state.setdefault("conversation_id", None)

def login_screen():
    st.title("🧠 CogniGraph")
    st.caption("Don't Give Answers. Teach Thinking.")
    tab1, tab2 = st.tabs(["Login", "Create account"])
    with tab1:
        with st.form("login_form"):
            username=st.text_input("Username")
            password=st.text_input("Password",type="password")
            submitted=st.form_submit_button("Login",use_container_width=True)
        if submitted:
            user=authenticate(username,password)
            if user:
                st.session_state.authenticated=True
                st.session_state.user=user
                course=get_or_create_demo_course(user["id"])
                st.session_state.course_id=course["id"]
                st.session_state.conversation_id=None
                st.rerun()
            else: st.error("Invalid username or password.")
    with tab2:
        with st.form("signup_form"):
            username=st.text_input("Choose username")
            password=st.text_input("Password (6+ characters)",type="password")
            confirm=st.text_input("Confirm password",type="password")
            submitted=st.form_submit_button("Create account",use_container_width=True)
        if submitted:
            if password != confirm: st.error("Passwords do not match.")
            else:
                uid,error=create_user(username,password)
                if error: st.error(error)
                else:
                    user=authenticate(username,password)
                    course=get_or_create_demo_course(uid)
                    st.session_state.authenticated=True; st.session_state.user=user
                    st.session_state.course_id=course["id"]; st.session_state.conversation_id=None
                    st.rerun()
