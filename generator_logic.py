import os
import json
import re
import time
import traceback
import google.generativeai as genai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_PATH = os.path.join(BASE_DIR, "rules.pdf")
CONFIG_FILE = os.path.join(BASE_DIR, "exam_config.json")

def log_cmd(msg, is_error=False):
    timestamp = time.strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {msg}", flush=True)
        if is_error:
            print(f"[{timestamp}] [ERROR TRACE] 👇", flush=True)
            traceback.print_exc()
            print("-" * 60, flush=True)
    except: pass

def format_time(seconds):
    if seconds is None or seconds < 0: return "--分--秒"
    m, s = divmod(int(seconds), 60)
    return f"{m}分{s:02d}秒"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def clean_json_text(text):
    # マークダウン記法削除
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    # 最初の [ から 最後の ] までを抽出 (余計な末尾のコメント対策)
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match: return match.group(0)
    return text

def get_models(api_key):
    log_cmd("Fetching model list from Google API...")
    genai.configure(api_key=api_key)
    models = []
    EXCLUSION_KEYWORDS = [
        "lite", "vision", "latest", "embedding", "aistudio", 
        "competition", "tts", "robotics", "image", "learned", 
        "computer", "exp", "experimental", "legacy", "preview"
    ]
    try:
        for m in genai.list_models():
            if 'generateContent' not in m.supported_generation_methods: continue
            name = m.name.replace("models/", "")
            lower = name.lower()
            if "gemini" not in lower: continue
            if any(ex in lower for ex in EXCLUSION_KEYWORDS): continue
            if re.search(r'-\d{3}$', name): continue
            if re.search(r'-\d{2}-\d{2}', name) or re.search(r'-\d{4}', name): continue
            models.append(name)
    except Exception as e:
        log_cmd(f"Failed to fetch models: {e}", is_error=True)
        return []
    
    models.sort(key=lambda x: (
        re.findall(r'\d+\.\d+', x)[0] if re.findall(r'\d+\.\d+', x) else "0.0",
        "ultra" in x.lower(),
        "pro" in x.lower(),
        x
    ), reverse=True)
    return models

def run_generation(api_key, model_name, target_levels, num_sets, update_ui_callback):
    log_cmd("=== Generation Process Started ===")
    genai.configure(api_key=api_key)
    
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    
    update_ui_callback([], {"status": "📄 PDFを確認中..."}, {'total': 0.0, 'chapter': 0.0})
    
    if not os.path.exists(PDF_PATH):
        return "PDFが見つかりません。rules.pdfを配置してください。"

    target_filename = "rules.pdf"
    log_cmd("Checking existing PDF cache...")
    try:
        for f in genai.list_files():
            if f.display_name == target_filename:
                genai.delete_file(f.name)
                log_cmd("Deleted old PDF cache.")
                break
    except: pass

    try:
        update_ui_callback([], {"status": "⬆️ PDFをアップロード中..."}, {'total': 0.05, 'chapter': 0.0})
        uploaded_file = genai.upload_file(PDF_PATH, mime_type="application/pdf", display_name=target_filename)
        
        while True:
            file_status = genai.get_file(uploaded_file.name)
            if file_status.state.name == "ACTIVE": break
            if file_status.state.name == "FAILED": return "PDF処理失敗"
            time.sleep(2)
    except Exception as e:
        return f"Upload Error: {str(e)}"

    model = genai.GenerativeModel(model_name)
    config_data = load_config()
    file_prefix = model_name.replace(":", "").replace("/", "")
    
    tasks = []
    task_id = 0
    for set_num in range(1, num_sets + 1):
        for level in target_levels:
            if level in config_data:
                weights = config_data[level].get("weights", {})
            else:
                weights = {"第2章":3, "第3章":17, "第4章":15, "第5章":7, "第6章":8}
            
            for ch_name, count in weights.items():
                tasks.append({
                    "id": task_id,
                    "name": f"セット{set_num} [{level}] {ch_name}",
                    "status": "⬜ 待機中",
                    "progress_text": f"0/{count} (0%)",
                    "target_count": count,
                    "level": level,
                    "chapter": ch_name
                })
                task_id += 1
    
    total_tasks = len(tasks)
    start_time_total = time.time()
    
    for i, task in enumerate(tasks):
        task["status"] = "🔄 生成中..."
        level = task["level"]
        ch_name = task["chapter"] # 例: "第4章 無人航空機のシステム"
        target_count = task["target_count"]
        
        # ターゲットとなる章番号を抽出 (例: 4)
        m_target = re.search(r'第(\d+)章', ch_name)
        target_ch_num = m_target.group(1) if m_target else None
        
        # ファイル名用のID (ch4)
        ch_id = f"ch{target_ch_num}" if target_ch_num else "chX"

        if level in config_data:
            scope = config_data[level].get("scope_instruction", "")
        else:
            scope = "基本範囲"

        json_path = os.path.join(DATA_DIR, f"db_{file_prefix}_{level}_{ch_id}.json")
        
        db_data = []
        current_max_id = 0
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                    ids = [q['id'] for q in db_data if 'id' in q]
                    if ids: current_max_id = max(ids)
            except: pass

        added = 0
        failures = 0
        start_time_chapter = time.time()

        while added < target_count:
            now = time.time()
            elapsed_total = now - start_time_total
            elapsed_chapter = now - start_time_chapter
            chapter_percent = added / target_count
            total_percent = (i + chapter_percent) / total_tasks
            
            # ETA計算
            total_eta = (elapsed_total / total_percent) - elapsed_total if total_percent > 0.01 else None
            chapter_eta = (elapsed_chapter / chapter_percent) - elapsed_chapter if chapter_percent > 0.1 else None

            time_info = {
                "status": f"現在: {task['name']}",
                "elapsed_total": format_time(elapsed_total),
                "eta_total": format_time(total_eta) if total_eta else "計算中...",
                "elapsed_chapter": format_time(elapsed_chapter),
                "eta_chapter": format_time(chapter_eta) if chapter_eta else "計算中..."
            }
            task["progress_text"] = f"{added}/{target_count} ({int(chapter_percent*100)}%)"
            update_ui_callback(tasks, time_info, {'total': min(0.99, total_percent), 'chapter': chapter_percent})

            needed = target_count - added
            req = min(5, needed)
            if req <= 0: break
            
            # ★強化されたプロンプト
            prompt = f"""
            あなたはドローン国家資格({level})の試験作成者です。
            PDFの目次や見出しを確認し、「{ch_name}」のセクションに書かれている内容のみを使って、三択問題を【{req}問】作成してください。
            
            【絶対厳守: 出題範囲の限定】
            ・「{ch_name}」以外の章（例えばリスク管理や法律など、他の章の内容）は一切含めないでください。
            ・その章に書かれていない知識は使わないでください。
            ・範囲詳細: {scope}
            
            【形式】
            出力は以下のJSON形式のみ。余計な会話は不要。
            [{{"question":"...","options":{{"1":"..","2":"..","3":".."}},"answer":"1","explanation":"..."}}]
            """
            
            try:
                resp = model.generate_content(
                    [prompt, uploaded_file],
                    generation_config={"response_mime_type": "application/json", "temperature": 0.7}
                )
                new_qs = json.loads(clean_json_text(resp.text))
                
                ok_count = 0
                for q in new_qs:
                    if all(k in q for k in ["question", "options", "answer"]):
                        # 重複チェック
                        if any(e['question'] == q['question'] for e in db_data):
                            continue
                            
                        # ★章番号の強制正規化 (AIが "4" や "Chapter4" と出しても "第4章" に統一)
                        if target_ch_num:
                            # どんな値が入っていても、ターゲットの章名で上書きする
                            q['chapter'] = ch_name 
                        
                        current_max_id += 1
                        q['id'] = current_max_id
                        q['level'] = level
                        db_data.append(q)
                        ok_count += 1
                
                if ok_count > 0:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(db_data, f, indent=4, ensure_ascii=False)
                    added += ok_count
                    failures = 0
                else:
                    failures += 1
                    time.sleep(1) # 少し待機

            except Exception as e:
                failures += 1
                log_cmd(f"API Error: {e}", is_error=True)
                if "429" in str(e):
                    task["status"] = "⏳ 制限待機中"
                    time.sleep(60)
            
            if failures >= 5:
                # 無限ループ防止: 生成できなくても次へ進む
                break
        
        task["status"] = "✅ 完了"
        task["progress_text"] = f"{target_count}/{target_count} (100%)"
        update_ui_callback(tasks, time_info, {'total': (i + 1) / total_tasks, 'chapter': 1.0})

    return None