import streamlit as st
import time
from collections import defaultdict
import quiz_logic
import ui_parts  # 共通部品読み込み

def render():
    # MENU: 試験設定画面
    if st.session_state.exam_state == "MENU":
        st.header("📚 模擬試験メニュー")
        stock_info = quiz_logic.get_available_models_info()
        
        if not stock_info:
            st.warning("問題データがありません。「問題作成」で生成してください。")
        else:
            st.subheader("1. 出題ソース選択")
            model_opts = list(stock_info.keys())
            def fmt_src(m):
                d = stock_info[m]
                return f"🤖 {m} (計{d['total']}問: 二等{d['二等']} / 一等{d['一等']})"
            selected_src = st.radio("出題セット:", model_opts, format_func=fmt_src)
            
            st.divider()
            st.subheader("2. 試験設定")
            c1, c2 = st.columns(2)
            with c1: exam_type = st.radio("試験タイプ", ["二等 (30分/50問)", "一等 (75分/70問)"])
            with c2:
                is_real = st.checkbox("🔥 本番モード (解説なし・ノンストップ)", value=False)
                st.caption("OFF: 練習モード (解説あり・タイマー一時停止)")

            st.divider()
            if st.button("試験開始", type="primary", use_container_width=True):
                level = "二等" if "二等" in exam_type else "一等"
                q_count = 50 if level == "二等" else 70
                limit_min = 30 if level == "二等" else 75
                qs = quiz_logic.get_exam_questions(level, q_count, selected_src)
                if not qs:
                    st.error(f"選択されたモデルには「{level}」の問題データがありません。")
                else:
                    st.session_state.questions = qs
                    st.session_state.time_limit = limit_min * 60
                    st.session_state.mode_real = is_real
                    st.session_state.exam_state = "EXAM"
                    st.session_state.current_index = 0
                    st.session_state.score = 0
                    st.session_state.user_answers = []
                    st.session_state.total_consumed = 0.0
                    st.session_state.is_explaining = False
                    st.session_state.start_time = time.time()
                    st.rerun()

    # EXAM: 試験中画面
    elif st.session_state.exam_state == "EXAM":
        q_idx = st.session_state.current_index
        total_q = len(st.session_state.questions)
        q = st.session_state.questions[q_idx]
        
        now = time.time()
        curr_cons = 0 if st.session_state.is_explaining else (now - st.session_state.start_time)
        rem = st.session_state.time_limit - (st.session_state.total_consumed + curr_cons)
        
        if rem <= 0 and not st.session_state.is_explaining:
            st.error("⏰ 時間切れ終了！")
            time.sleep(2)
            st.session_state.exam_state = "RESULT"
            st.rerun()

        st.progress((q_idx) / total_q)
        
        timer_running = not st.session_state.is_explaining
        ui_parts.render_timer(int(rem), timer_running)

        st.subheader(f"Q{q_idx+1}. {q['question']}")
        
        ops = q['options']
        if st.session_state.is_explaining:
            last = st.session_state.user_answers[-1]
            if last['ok']: st.success("✅ 正解！")
            else: st.error("❌ 不正解...")
            
            for oid in ["1", "2", "3"]:
                lbl = f"{oid}. {ops.get(oid, '')}"
                if oid == str(q['answer']):
                    st.success(f"✅ {lbl} (あなたの回答・正解)" if oid == last['u'] else f"⭕ {lbl} (正解)")
                elif oid == last['u']:
                    st.error(f"❌ {lbl} (あなたの回答)")
                else:
                    st.markdown(f"<div style='padding:16px;border-radius:0.5rem;border:1px solid rgba(128,128,128,0.2);margin-bottom:1rem;'>⬜ {lbl}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            c_src, c_rep = st.columns([4, 1])
            with c_src:
                src_txt = f"🤖 {q.get('source_model','?')} | 📖 {q.get('chapter','?')} | 🆔 {q.get('id','?')}"
                st.caption(src_txt)

            st.info(f"💡 解説:\n\n{q['explanation']}")
            
            # --- ボタン配置エリア ---
            col_next, col_dummy, col_report = st.columns([3, 4, 2])
            
            with col_next:
                if st.button("次へ ➡", type="primary", use_container_width=True):
                    st.session_state.is_explaining = False
                    st.session_state.current_index += 1
                    if st.session_state.current_index >= total_q:
                        st.session_state.exam_state = "RESULT"
                    else:
                        st.session_state.start_time = time.time()
                    st.rerun()
            
            with col_report:
                # ★ 練習モードの場合のみ報告ボタンと説明文を表示
                if not st.session_state.mode_real:
                    if st.button("⚠️ 報告"):
                        if ui_parts.report_question(q): st.toast("報告しました", icon="✅")
                    st.caption("※ 誤りがあれば報告")
        else:
            ans = None
            if st.button(f"1. {ops.get('1','')}", use_container_width=True): ans="1"
            if st.button(f"2. {ops.get('2','')}", use_container_width=True): ans="2"
            if st.button(f"3. {ops.get('3','')}", use_container_width=True): ans="3"
            
            if ans:
                elapsed = time.time() - st.session_state.start_time
                st.session_state.total_consumed += elapsed
                is_ok = (ans == str(q['answer']))
                if is_ok: st.session_state.score += 1
                st.session_state.user_answers.append({"q": q, "u": ans, "ok": is_ok})
                
                if st.session_state.mode_real:
                    st.session_state.current_index += 1
                    if st.session_state.current_index >= total_q:
                        st.session_state.exam_state = "RESULT"
                    else:
                        st.session_state.start_time = time.time()
                    st.rerun()
                else:
                    st.session_state.is_explaining = True
                    st.rerun()
        
        # ★ 中断ボタンを追加
        st.markdown("---")
        if st.button("↩️ 試験を中断してメニューへ戻る", type="secondary", use_container_width=True):
            st.session_state.exam_state = "MENU"
            st.rerun()

    # RESULT: 結果画面
    elif st.session_state.exam_state == "RESULT":
        st.header("🏁 結果発表")
        sc = st.session_state.score
        tot = len(st.session_state.questions)
        per = int((sc / tot) * 100) if tot > 0 else 0
        
        if per >= 80:
            st.balloons(); st.success(f"🈴 合格！ ({sc}/{tot}問 - {per}%)")
        else:
            st.error(f"💪 不合格... ({sc}/{tot}問 - {per}%) - 合格ラインは80%です")
            
        st.divider()
        st.subheader("📊 分野別正解率")
        stats = defaultdict(lambda: {"c": 0, "t": 0})
        for log in st.session_state.user_answers:
            ch = log['q'].get('chapter', 'その他')
            stats[ch]['t'] += 1
            if log['ok']: stats[ch]['c'] += 1
        
        for ch, d in sorted(stats.items()):
            if d['t'] > 0:
                acc = d['c'] / d['t']
                st.markdown(f"**{ch}** : {d['c']}/{d['t']} ({int(acc*100)}%)")
                st.progress(acc)
        
        st.divider()
        wrong_list = [log for log in st.session_state.user_answers if not log['ok']]
        if wrong_list:
            if st.button(f"🔥 間違えた問題({len(wrong_list)}問)だけ復習する", type="primary"):
                st.session_state.questions = [x['q'] for x in wrong_list]
                st.session_state.time_limit = 99999
                st.session_state.mode_real = False
                st.session_state.exam_state = "EXAM"
                st.session_state.current_index = 0
                st.session_state.score = 0
                st.session_state.user_answers = []
                st.session_state.total_consumed = 0
                st.session_state.start_time = time.time()
                st.rerun()
        
        st.subheader("📝 回答詳細")
        for i, log in enumerate(st.session_state.user_answers):
            q = log['q']
            icon = "✅" if log['ok'] else "❌"
            u_sel = log['u']
            c_ans = str(q['answer'])
            ops = q['options']
            src_txt = f"🤖 {q.get('source_model','?')} | 📖 {q.get('chapter','?')} | 🆔 {q.get('id','?')}"

            with st.expander(f"Q{i+1} {icon} : {q['question'][:30]}..."):
                st.caption(src_txt)
                st.markdown(f"**問題**: {q['question']}")
                st.markdown("---")
                for oid in ["1", "2", "3"]:
                    lbl = f"{oid}. {ops.get(oid, '')}"
                    if oid == c_ans:
                        st.success(f"✅ {lbl} (あなたの回答・正解)" if oid == u_sel else f"⭕ {lbl} (正解)")
                    elif oid == u_sel:
                        st.error(f"❌ {lbl} (あなたの回答)")
                    else:
                        st.markdown(f"<div style='padding:16px;border-radius:0.5rem;border:1px solid rgba(128,128,128,0.2);margin-bottom:1rem;'>⬜ {lbl}</div>", unsafe_allow_html=True)
                st.markdown("---")
                st.info(f"💡 **解説**:\n\n{q['explanation']}")
                
                # ★ 結果画面の報告ボタンにも説明を追加
                if st.button("⚠️ この問題を報告", key=f"rep_{i}"):
                     if ui_parts.report_question(q): st.toast("報告しました", icon="✅")
                st.caption("※ 解説や問題に誤りがある場合は報告してください")
        
        if st.button("メニューへ戻る"):
            st.session_state.exam_state = "MENU"
            st.rerun()