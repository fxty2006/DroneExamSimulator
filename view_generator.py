import streamlit as st
import pandas as pd
import os
import generator_logic
import ui_parts  # 共通部品

def render(locked):
    st.header("📝 AI問題作成")
    
    # PDFチェック
    ui_parts.check_pdf_exists()
    
    if st.session_state.gen_success:
        st.success("✅ 全ての生成が完了しました！"); st.balloons(); st.session_state.gen_success = False
    if st.session_state.gen_error:
        st.error(f"エラー: {st.session_state.gen_error}"); st.session_state.gen_error = None

    api_key = ""
    # main_ui側でBASE_DIRなどを定義していないため、ここで再度パス解決するか、引数で受け取る
    # 簡易化のためここでパス解決
    base = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(base, "apikey.txt")
    
    if os.path.exists(key_file):
        with open(key_file, 'r', encoding='utf-8-sig') as f: api_key = f.read().strip()
    user_key = st.text_input("API Key", value=api_key, type="password", disabled=locked)
    
    if st.button("モデルリスト取得 (推奨モデルのみ)", disabled=locked):
        with st.spinner("取得中..."):
            st.session_state.models = generator_logic.get_models(user_key)
    
    models = st.session_state.get("models", [])
    if models:
        st.info("💡 **ヒント**: 精度重視なら **Pro**、速度重視なら **Flash** がおすすめです。")
        def fmt(m):
            if "pro" in m.lower(): return f"🤖 {m} (推奨:高精度/1日約2セット)"
            if "flash" in m.lower(): return f"⚡ {m} (高速/1日50セット以上)"
            return m
        target_model = st.radio("モデル選択", models, format_func=fmt, disabled=locked)
        st.divider()
        c1, c2 = st.columns(2)
        with c1: level_mode = st.radio("作成レベル", ["二等 (基礎)", "一等 (応用)", "両方 (二等+一等)"], disabled=locked)
        with c2: sets = st.number_input("作成セット数", 1, 5, 1, disabled=locked)
        
        if not locked and st.button("🚀 生成開始", type="primary"):
            st.session_state.is_generating = True
            st.rerun()
    
    if locked:
        st.markdown("---")
        st.warning("⚠️ **生成中です。操作しないでください**\n\n中断する場合はブラウザの更新、またはタブを閉じてください。")
        
        st.subheader("🚀 全体の進捗")
        total_bar = st.progress(0)
        total_metrics_ph = st.empty()
        
        st.divider()
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📋 タスク一覧")
            table_ph = st.empty()
            
        with col_right:
            st.subheader("🔄 現在の章")
            chapter_status_ph = st.empty()
            chapter_bar = st.progress(0)
            chapter_metrics_ph = st.empty()

        if "両方" in level_mode: target_levels = ["二等", "一等"]
        elif "一等" in level_mode: target_levels = ["一等"]
        else: target_levels = ["二等"]
        
        def ui_updater(tasks_data, time_info, progress_dict):
            total_bar.progress(progress_dict.get('total', 0.0))
            chapter_bar.progress(progress_dict.get('chapter', 0.0))
            if isinstance(time_info, dict):
                with total_metrics_ph.container():
                    c_t1, c_t2 = st.columns(2)
                    c_t1.metric("⏳ 全体経過", time_info.get('elapsed_total', '--'))
                    c_t2.metric("🏁 完了目安", time_info.get('eta_total', '--'))
                with chapter_status_ph.container():
                    st.info(f"**{time_info.get('status', '準備中...')}**")
                with chapter_metrics_ph.container():
                    c_c1, c_c2 = st.columns(2)
                    c_c1.metric("⏱️ 章経過", time_info.get('elapsed_chapter', '--'))
                    c_c2.metric("🏁 章目安", time_info.get('eta_chapter', '--'))
            if tasks_data:
                df = pd.DataFrame(tasks_data)
                df_show = df[["name", "status", "progress_text"]]
                df_show.columns = ["タスク名", "状態", "進捗"]
                table_ph.table(df_show)

        err = generator_logic.run_generation(user_key, target_model, target_levels, sets, ui_updater)
        st.session_state.is_generating = False
        if err: st.session_state.gen_error = err
        else: st.session_state.gen_success = True
        st.rerun()