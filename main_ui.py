# -*- coding: utf-8 -*-
import streamlit as st
import os
import time
import json
import ui_parts
import view_exam
import view_generator
import view_manager

st.set_page_config(page_title="ドローン試験システム", layout="wide")

# CSS注入
ui_parts.inject_custom_css()

# セッション初期化
defaults = {
    "exam_state": "MENU", "questions": [], "score": 0, "current_index": 0,
    "user_answers": [], "start_time": 0.0, "total_consumed": 0.0, "time_limit": 0,
    "is_explaining": False, "mode_real": False, "is_generating": False,
    "gen_success": False, "gen_error": None, "db_errors": None, "maintenance_msg": None
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# DBエラー状態の初期ロード
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(BASE_DIR, "data", "db_status.json")
if st.session_state.db_errors is None:
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                st.session_state.db_errors = json.load(f)
        except: st.session_state.db_errors = []
    else: st.session_state.db_errors = []

# ロック状態の判定: 生成中 または 試験中(EXAM)の場合は操作をロック
locked = st.session_state.is_generating or (st.session_state.exam_state == "EXAM")

with st.sidebar:
    st.title("🚁 メニュー")
    # lockedがTrueの場合、ラジオボタンが無効化され移動できなくなる
    mode = st.radio("機能を選択", ["📚 模擬試験", "📝 問題作成", "📊 データ管理・保守"], disabled=locked)
    
    if st.session_state.db_errors:
        st.warning(f"⚠️ データ不備: {len(st.session_state.db_errors)}件")

    st.divider()
    if st.button("🚪 アプリを終了", type="primary", disabled=locked):
        st.warning("終了します。ブラウザを閉じてください...")
        time.sleep(1)
        os._exit(0)

# 機能ルーティング
if mode == "📚 模擬試験":
    view_exam.render()
elif mode == "📝 問題作成":
    view_generator.render(locked)
elif mode == "📊 データ管理・保守":
    view_manager.render(locked)