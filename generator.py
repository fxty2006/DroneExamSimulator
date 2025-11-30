import os
import time
import json
import re
import math
import sys
import google.generativeai as genai

# --- パス設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "rules.pdf")
KEY_FILE = os.path.join(BASE_DIR, "apikey.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "exam_config.json")

BATCH_SIZE = 5 

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {
        "二等": {
            "scope_instruction": "二等範囲",
            "weights": {"第2章": 3, "第3章": 17, "第4章": 15, "第5章": 7, "第6章": 8}
        }
    }

def clean_json_text(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match: return match.group(0)
    match_obj = re.search(r'\{.*\}', text, re.DOTALL)
    if match_obj: return f"[{match_obj.group(0)}]"
    return text

# --- プログレスバー表示関数 ---
def print_progress(current, total, start_time, prefix=""):
    bar_length = 30
    if total <= 0:
        progress = 1.0
    else:
        progress = min(1.0, current / total)
        
    block = int(round(bar_length * progress))
    bar = "█" * block + "-" * (bar_length - block)
    elapsed = time.time() - start_time
    
    sys.stdout.write(f"\r{prefix} |{bar}| {int(progress*100)}% ({current}/{total}問) [経過: {int(elapsed)}秒]")
    sys.stdout.flush()

def main():
    print("🔑 APIキー設定")
    
    api_key = None
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                if content: api_key = content
        except: pass
    
    if not api_key: api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("   Google Gemini APIキーを入力してください: ").strip()

    genai.configure(api_key=api_key)

    # --- モデルの動的取得 ---
    print("\n🔍 利用可能なモデルを取得・選別しています...")
    all_models = []
    recommended_models = []

    TARGET_KEYWORDS = ["latest", "2.5", "2.0"]
    EXCLUDED_KEYWORDS = ["preview", "exp", "image", "vision", "thinking", "robotics", "nano", "tts", "gemma", "learnlm"]

    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                all_models.append(clean_name)
                is_suitable = False
                for target in TARGET_KEYWORDS:
                    if target in clean_name.lower():
                        is_suitable = True
                        break
                if is_suitable:
                    for exclude in EXCLUDED_KEYWORDS:
                        if exclude in clean_name.lower():
                            is_suitable = False
                            break
                if "gemini" not in clean_name.lower():
                    is_suitable = False
                if is_suitable:
                    recommended_models.append(clean_name)
    except Exception as e:
        print(f"❌ モデルリスト取得失敗: {e}")
        return

    if recommended_models:
        final_list = sorted(recommended_models, reverse=True)
        print("✨ 厳選されたモデルのみ表示します")
    else:
        final_list = sorted(all_models, reverse=True)
        print("⚠️ 全モデルを表示します")

    print("-" * 50)
    for i, m_name in enumerate(final_list):
        icon = "  "
        if "latest" in m_name: icon = "🆕"
        elif "2.5" in m_name:  icon = "🚀"
        type_icon = ""
        if "pro" in m_name: type_icon = "👑"
        elif "flash" in m_name: type_icon = "⚡"
        print(f"   {i + 1:<2}: {icon} {type_icon} {m_name}")
    print("-" * 50)

    selected_model_name = ""
    while True:
        choice = input(f"番号を選択 (1-{len(final_list)}) > ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(final_list):
                selected_model_name = final_list[idx]
                break
        print("❌ 正しい番号を入力してください。")

    print(f"👉 選択モデル: {selected_model_name}")
    file_prefix = selected_model_name.replace(":", "").replace("/", "")

    try:
        model = genai.GenerativeModel(selected_model_name)
    except Exception as e:
        print(f"❌ モデル設定エラー: {e}")
        return

    print(f"\n📄 PDF読み込み中...")
    if not os.path.exists(PDF_PATH):
        print(f"❌ {PDF_PATH} が見つかりません。")
        return

    try:
        uploaded_file = genai.upload_file(PDF_PATH, mime_type="application/pdf")
        print(f"✅ アップロードリクエスト完了: {uploaded_file.name}")
        
        # --- PDF処理待ちロジック ---
        print("   ⏳ Google側でのファイル処理を待機しています...", end="")
        while True:
            file_status = genai.get_file(uploaded_file.name)
            if file_status.state.name == "ACTIVE":
                print(" 完了！")
                break
            elif file_status.state.name == "FAILED":
                print("\n❌ ファイル処理に失敗しました。")
                return
            else:
                print(".", end="")
                time.sleep(2)
        # ------------------------

    except Exception as e:
        print(f"❌ エラー: {e}")
        return

    config_data = load_config()

    print("\n⚙️ 生成レベル設定")
    print("   1: 二等 (基礎)")
    print("   2: 一等 (応用)")
    print("   3: 両方 (二等を作成後、一等を作成)")
    
    target_levels = []
    while True:
        lvl_choice = input("   選択 > ").strip()
        if lvl_choice == "1":
            target_levels = ["二等"]
            break
        elif lvl_choice == "2":
            target_levels = ["一等"]
            break
        elif lvl_choice == "3":
            target_levels = ["二等", "一等"]
            break
        
    while True:
        sets_input = input(f"   何セット作成しますか？ (例: 1) > ").strip()
        if sets_input.isdigit() and int(sets_input) > 0:
            NUM_SETS = int(sets_input)
            break

    print(f"\n🚀 '{file_prefix}' のデータベースに追加作成を開始します...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    overall_start_time = time.time()

    # ==========================
    # メインループ開始
    # ==========================
    for set_num in range(1, NUM_SETS + 1):
        set_start_time = time.time()
        print(f"\n{'='*15} セット {set_num}/{NUM_SETS} {'='*15}")
        
        for level in target_levels:
            print(f"\n🔰 レベル: {level} の生成を開始します")

            if level in config_data:
                current_config = config_data[level]
                scope_instruction = current_config.get("scope_instruction", "")
                gen_weights = current_config.get("weights", {})
            else:
                gen_weights = {"第2章":3, "第3章":17, "第4章":15, "第5章":7, "第6章":8}
                scope_instruction = "基礎範囲"

            for chapter_name, count in gen_weights.items():
                ch_num_match = re.search(r'第(\d+)章', chapter_name)
                ch_id = f"ch{ch_num_match.group(1)}" if ch_num_match else "chX"
                
                filename = os.path.join(DATA_DIR, f"db_{file_prefix}_{level}_{ch_id}.json")
                
                db_data = []
                current_max_id = 0
                if os.path.exists(filename):
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            db_data = json.load(f)
                            ids = [q['id'] for q in db_data if 'id' in q and isinstance(q['id'], int)]
                            if ids: current_max_id = max(ids)
                    except: pass
                
                chapter_start_time = time.time()
                added_this_chapter = 0 
                consecutive_failures = 0
                MAX_FAILURES = 5

                print_progress(0, count, chapter_start_time, prefix=f"  [{level}] {chapter_name[:6]}...")

                while added_this_chapter < count:
                    needed = count - added_this_chapter
                    current_batch = min(BATCH_SIZE, needed)
                    
                    if current_batch <= 0: break

                    prompt = f"""
                    あなたはドローン国家資格({level})の試験作成者です。
                    添付PDFに基づき、{chapter_name}から三肢択一問題を【{current_batch}問】作成してください。
                    
                    ルール: {scope_instruction}
                    
                    【重要】
                    - 既存の問題と内容が重複しないようにしてください。
                    - 必ず指定された形式のJSON配列のみを出力してください。
                    
                    出力: JSON配列のみ。
                    [
                        {{ "level": "{level}", "chapter": "{chapter_name}", "question": "...", "options": {{"1":"...","2":"...","3":"..."}}, "answer": "1", "explanation": "..." }}
                    ]
                    """
                    
                    api_success = False
                    for _ in range(3): # リトライ3回
                        try:
                            resp = model.generate_content(
                                [prompt, uploaded_file], 
                                generation_config={"response_mime_type": "application/json"}
                            )
                            new_qs = json.loads(clean_json_text(resp.text))
                            
                            if isinstance(new_qs, list):
                                batch_added_count = 0
                                for q in new_qs:
                                    if "question" in q and "options" in q:
                                        if not any(exist['question'] == q['question'] for exist in db_data):
                                            current_max_id += 1
                                            q['id'] = current_max_id
                                            q['level'] = level 
                                            db_data.append(q)
                                            batch_added_count += 1
                                
                                if batch_added_count > 0:
                                    with open(filename, 'w', encoding='utf-8') as f:
                                        json.dump(db_data, f, indent=4, ensure_ascii=False)
                                    added_this_chapter += batch_added_count
                                    consecutive_failures = 0 
                                else:
                                    consecutive_failures += 1
                                
                                api_success = True
                                time.sleep(5)
                                break 
                                
                        except Exception as e:
                            if "429" in str(e): 
                                print_progress(min(added_this_chapter, count), count, chapter_start_time, prefix=f"  [{level}] ⏳規制中...")
                                time.sleep(20)
                            else: 
                                time.sleep(2)
                    
                    print_progress(min(added_this_chapter, count), count, chapter_start_time, prefix=f"  [{level}] {chapter_name[:6]}...")

                    if not api_success: consecutive_failures += 1
                    if consecutive_failures >= MAX_FAILURES:
                        sys.stdout.write(" ⚠️ 生成不可(重複/枯渇)")
                        sys.stdout.flush()
                        break
                
                print() 

        set_dur = time.time() - set_start_time
        print(f"⏱️  セット {set_num} 完了: {int(set_dur//60)}分 {int(set_dur%60)}秒")

    total_dur = time.time() - overall_start_time
    print(f"\n🎉 全工程完了！")
    print(f"⏰ トータル経過時間: {int(total_dur//60)}分 {int(total_dur%60)}秒")

if __name__ == "__main__":
    main()