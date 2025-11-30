import streamlit as st
import json
import random
import time
import os
import re
import glob
from collections import defaultdict

# ==========================================
# 1. ページ設定 (最優先)
# ==========================================
st.set_page_config(page_title="ドローン学科試験", layout="centered")

# ==========================================
# 2. 定数・パス設定
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "exam_config.json")

# ==========================================
# 3. 状態管理 (Session State) の初期化
# ==========================================
defaults = {
    "exam_state": "MENU",       # MENU, EXAM, RESULT
    "questions": [],            # 問題リスト
    "current_index": 0,         # 現在の問題番号
    "score": 0,                 # 正解数
    "user_answers": [],         # 回答ログ
    "consumed_time": 0.0,       # 経過時間
    "q_start_time": 0.0,        # 問題開始時刻
    "is_explaining": False,     # 解説表示中か
    "exam_mode": False,         # 本番モードか
    "selected_model": ""        # 選択中のモデル
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 4. ヘルパー関数 (ロジック)
# ==========================================

def detect_available_models():
    """dataフォルダ内のモデルを検出"""
    if not os.path.exists(DATA_DIR): return ["(データなし)"]
    files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    models = set()
    for f in files:
        fname = os.path.basename(f)
        parts = fname.split('_')
        if len(parts) >= 4:
            models.add(parts[1])
    return sorted(list(models)) if models else ["(データなし)"]

def load_json_safe(filename):
    """JSON読み込み"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [x for x in data if isinstance(x, dict) and "question" in x]
        except: pass
    return []

def get_weights(level):
    """出題配分の取得"""
    weights = {
        "二等": {"ch2": 3, "ch3": 17, "ch4": 15, "ch5": 7, "ch6": 8},
        "一等": {"ch2": 4, "ch3": 24, "ch4": 20, "ch5": 10, "ch6": 12}
    }
    # configファイルがあれば上書き
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if level in cfg:
                    raw = cfg[level]["weights"]
                    w = {}
                    for k,v in raw.items():
                        m = re.search(r'第(\d+)章', k)
                        if m: w[f"ch{m.group(1)}"] = v
                    return w
        except: pass
    return weights.get(level, {})

def reset_to_menu():
    """アプリ内のメニュー画面に戻る"""
    st.session_state.exam_state = "MENU"
    st.session_state.questions = []
    st.session_state.user_answers = []
    st.session_state.score = 0
    st.session_state.current_index = 0
    st.session_state.is_explaining = False

# ==========================================
# 5. サイドバー (常時表示)
# ==========================================
with st.sidebar:
    st.markdown("### 📚 題材選択")
    models = detect_available_models()
    st.session_state.selected_model = st.radio("モデル:", models)
    
    st.markdown("---")
    
    # 【修正箇所】アプリを終了してCMDに戻る処理
    if st.button("終了してCMDメニューに戻る", key="sidebar_exit", type="primary", use_container_width=True):
        st.warning("終了します...")
        time.sleep(1) # メッセージを見せるため少し待機
        os._exit(0)   # プロセスを強制終了(start.batに戻る)

# ==========================================
# 6. メイン画面の分岐処理
# ==========================================

# ---------------- CSS スタイル ----------------
st.markdown("""
<style>
div.stButton > button { width: 100%; text-align: left; padding: 15px; }
.qid { background-color:#eee; padding:2px 8px; border-radius:4px; font-size:0.9em; }
.badge { background-color:#007bff; color:white; padding:2px 6px; border-radius:4px; font-size:0.8em; margin-right:5px; }
</style>
""", unsafe_allow_html=True)

# ---------------- MENU 画面 ----------------
if st.session_state.exam_state == "MENU":
    st.title("🚁 ドローン学科試験CBT")
    
    # モード設定
    st.session_state.exam_mode = st.checkbox("試験本番モード (解説なし・一気解き)", value=st.session_state.exam_mode)
    st.divider()

    # 開始処理を行う関数
    def launch_exam(level, review_mode=False, review_qs=None):
        target_model = st.session_state.selected_model
        
        if review_mode:
            qs = review_qs
            limit = len(qs) * 60
        else:
            weights = get_weights(level)
            prefix = os.path.join(DATA_DIR, f"db_{target_model}_{level}_")
            qs = []
            for ch, count in weights.items():
                data = load_json_safe(f"{prefix}{ch}.json")
                if data:
                    for q in data:
                        q['_id_str'] = f"{target_model}-{level}-{ch}-{q.get('id','?')}"
                        if 'chapter' not in q: q['chapter'] = f"第{ch.replace('ch','')}章"
                    qs.extend(data if len(data) < count else random.sample(data, count))
            limit = (30 if level=="二等" else 75) * 60
        
        if not qs:
            st.error("問題データがありません。Generatorで作成してください。")
            return

        random.shuffle(qs)
        st.session_state.questions = qs
        st.session_state.time_limit = limit
        st.session_state.exam_state = "EXAM"
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.consumed_time = 0.0
        st.session_state.is_explaining = False
        st.session_state.q_start_time = time.time()
        st.rerun() # 即座に画面遷移

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔰 二等")
        if st.button("二等を開始 (30分)", key="start_2", type="primary"):
            launch_exam("二等")
    with c2:
        st.subheader("👑 一等")
        if st.button("一等を開始 (75分)", key="start_1", type="primary"):
            launch_exam("一等")

# ---------------- EXAM 画面 ----------------
elif st.session_state.exam_state == "EXAM":
    if not st.session_state.questions: # エラー回避
        reset_to_menu()
        st.rerun()

    q_idx = st.session_state.current_index
    question = st.session_state.questions[q_idx]
    
    # タイマー計算
    now = time.time()
    elapsed = 0 if st.session_state.is_explaining else (now - st.session_state.q_start_time)
    total_consumed = st.session_state.consumed_time + elapsed
    remaining = st.session_state.time_limit - total_consumed
    
    if remaining <= 0 and not st.session_state.is_explaining:
        st.error("⏰ 時間切れ！")
        time.sleep(2)
        st.session_state.exam_state = "RESULT"
        st.rerun()

    # 表示
    st.progress((q_idx) / len(st.session_state.questions))
    st.caption(f"Q {q_idx+1} / {len(st.session_state.questions)} | 残り {int(remaining//60)}分 {int(remaining%60)}秒")
    
    st.markdown(f"<div><span class='badge'>{question.get('chapter','')}</span><span class='qid'>{question.get('_id_str','')}</span></div>", unsafe_allow_html=True)
    st.markdown(f"### {question['question']}")

    # 解説画面
    if st.session_state.is_explaining:
        last_log = st.session_state.user_answers[-1]
        if last_log['res']:
            st.success("✅ 正解！")
        else:
            st.error(f"❌ 不正解... 正解は「{last_log['c_key']}」")
        st.info(f"💡 解説:\n\n{question['explanation']}")
        
        if st.button("次へ ➡", key="next_btn", type="primary"):
            st.session_state.is_explaining = False
            st.session_state.current_index += 1
            if st.session_state.current_index >= len(st.session_state.questions):
                st.session_state.exam_state = "RESULT"
            else:
                st.session_state.q_start_time = time.time()
            st.rerun()

    # 回答画面
    else:
        ops = question['options']
        # コールバックを使わず、if button で処理する
        choice = None
        if st.button(f"1. {ops.get('1','')}", key=f"q{q_idx}_1"): choice = "1"
        if st.button(f"2. {ops.get('2','')}", key=f"q{q_idx}_2"): choice = "2"
        if st.button(f"3. {ops.get('3','')}", key=f"q{q_idx}_3"): choice = "3"

        if choice:
            # 回答処理
            correct = str(question['answer'])
            is_correct = (choice == correct)
            if is_correct: st.session_state.score += 1
            
            # ログ記録
            st.session_state.user_answers.append({
                "q_obj": question,
                "u_key": choice,
                "c_key": correct,
                "res": is_correct,
                "time": elapsed
            })
            
            # 累積時間を確定
            st.session_state.consumed_time += elapsed
            
            if st.session_state.exam_mode:
                # 本番モード: 即次へ
                st.session_state.current_index += 1
                if st.session_state.current_index >= len(st.session_state.questions):
                    st.session_state.exam_state = "RESULT"
                else:
                    st.session_state.q_start_time = time.time()
                st.rerun()
            else:
                # 練習モード: 解説へ
                st.session_state.is_explaining = True
                st.rerun()

# ---------------- RESULT 画面 ----------------
elif st.session_state.exam_state == "RESULT":
    st.title("🏁 結果発表")
    
    score = st.session_state.score
    total = len(st.session_state.questions)
    per = int(score / total * 100) if total > 0 else 0
    
    if per >= 80:
        st.balloons()
        st.success(f"🈴 合格！ ({score}/{total}問 - {per}%)")
    else:
        st.error(f"💪 不合格... ({score}/{total}問 - {per}%)")
        
    st.divider()
    
    # 弱点分析
    stats = defaultdict(lambda: {"ok":0, "all":0})
    wrong_qs = []
    
    for log in st.session_state.user_answers:
        ch = log['q_obj'].get('chapter', 'その他')
        stats[ch]["all"] += 1
        if log['res']: stats[ch]["ok"] += 1
        else: wrong_qs.append(log['q_obj'])
        
    st.subheader("📊 分野別正解率")
    for ch, d in sorted(stats.items()):
        p = d['ok'] / d['all']
        st.write(f"**{ch}**: {d['ok']}/{d['all']} ({int(p*100)}%)")
        st.progress(p)
        
    if wrong_qs:
        st.divider()
        st.warning(f"間違えた問題: {len(wrong_qs)}問")
        if st.button("🔥 間違えた問題だけ復習する", type="primary"):
            st.session_state.exam_mode = False # 復習は解説あり
            # 復習開始ロジック
            st.session_state.questions = wrong_qs
            st.session_state.time_limit = len(wrong_qs) * 60
            st.session_state.exam_state = "EXAM"
            st.session_state.current_index = 0
            st.session_state.score = 0
            st.session_state.user_answers = []
            st.session_state.consumed_time = 0.0
            st.session_state.is_explaining = False
            st.session_state.q_start_time = time.time()
            st.rerun()

    st.divider()
    st.subheader("📝 履歴")
    for i, log in enumerate(st.session_state.user_answers):
        q = log['q_obj']
        icon = "🔵" if log['res'] else "❌"
        with st.expander(f"{icon} Q{i+1}: {q['question'][:20]}..."):
            st.write(f"**問題**: {q['question']}")
            st.info(f"解説: {q['explanation']}")
            st.caption(f"あなたの回答: {log['u_key']} / 正解: {log['c_key']} (回答時間 {int(log['time'])}秒)")

    # ここのボタンは「アプリ内のメニュー（二等・一等選択画面）」に戻る
    if st.button("トップメニューに戻る", key="back_result", type="secondary"):
        reset_to_menu()
        st.rerun()