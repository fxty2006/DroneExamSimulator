import streamlit as st
import streamlit.components.v1 as components
import os
import time
import csv

# 定数定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_FILE = os.path.join(DATA_DIR, "csv_review", "reported.csv")
PDF_PATH = os.path.join(BASE_DIR, "rules.pdf")

# カスタムCSSの注入
def inject_custom_css():
    st.markdown("""
    <style>
    div.stButton > button {
        text-align: left; justify-content: flex-start; width: 100%; height: auto;
        padding: 15px; white-space: normal;
    }
    .report-btn { border: 1px solid #ff4b4b; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# JSタイマー表示
def render_timer(remaining_sec, is_running):
    # 復習モード判定 (例: 10時間=36000秒以上なら復習モードとみなす)
    if remaining_sec > 36000:
        st.markdown("""
        <div style="
            font-size: 1.2rem; font-weight: bold; text-align: right;
            padding: 10px; color: #0068c9; background-color: #f0f2f6; 
            border-radius: 5px; margin-bottom: 10px;
        ">
            ∞ 復習モード（時間無制限）
        </div>
        """, unsafe_allow_html=True)
        return

    # 解説中などのステータス表示
    status_text = ""
    if not is_running:
        status_text = " ⏸️(解説中)"
    
    # JS埋め込み
    # isRunningがtrueのときだけカウントダウンし、falseなら停止したまま表示する
    js_code = f"""
    <div id="timer_display" style="
        font-size: 1.5rem; font-weight: bold; text-align: right;
        padding: 10px; color: {'#333' if remaining_sec > 60 else '#d32f2f'};
        background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px;
    ">
        残り時間: --:--
    </div>
    <script>
        let timeLeft = {remaining_sec};
        let isRunning = {'true' if is_running else 'false'};
        let statusText = "{status_text}";
        const display = document.getElementById("timer_display");
        
        function updateDisplay() {{
            let m = Math.floor(timeLeft / 60);
            let s = Math.floor(timeLeft % 60);
            let timeStr = m + "分 " + (s < 10 ? "0" : "") + s + "秒";
            display.innerText = "残り時間: " + timeStr + statusText;
            if (timeLeft <= 60) display.style.color = "#d32f2f";
        }}
        
        updateDisplay();
        
        if (isRunning && timeLeft > 0) {{
            const interval = setInterval(() => {{
                timeLeft--;
                updateDisplay();
                if (timeLeft <= 0) {{
                    clearInterval(interval);
                    display.innerText = "時間切れ！";
                }}
            }}, 1000);
        }}
    </script>
    """
    components.html(js_code, height=60)

# 問題報告機能
def report_question(q, reason="ユーザー報告"):
    if not os.path.exists(os.path.dirname(REPORT_FILE)):
        os.makedirs(os.path.dirname(REPORT_FILE))
    
    file_exists = os.path.exists(REPORT_FILE)
    try:
        with open(REPORT_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["日時", "理由", "モデル", "章", "ID", "問題文"])
            
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                reason,
                q.get('source_model','?'),
                q.get('chapter','?'),
                q.get('id','?'),
                q.get('question','')
            ])
        return True
    except:
        return False

# PDFの存在チェック
def check_pdf_exists():
    if not os.path.exists(PDF_PATH):
        st.error("⚠️ PDFファイルが見つかりません！")
        st.info("以下の手順でファイルを配置してください：")
        st.markdown("""
        1. 国交省のサイトから **「無人航空機の飛行の安全に関する教則」（最新版）** をダウンロードしてください。
           * ファイル名例: `無人航空機の飛行の安全に関する教則 令和７年２月１日第４版.pdf`
        2. ファイル名を **`rules.pdf`** に変更（リネーム）してください。
        3. このアプリのフォルダ（`start.bat`がある場所）に置いてください。
        """)
        st.warning("※ ファイルを配置後、画面を更新してください。")
        st.stop()