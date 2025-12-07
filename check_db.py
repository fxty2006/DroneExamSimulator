import os
import json
import glob
import logger  # 共通ログを使用

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATUS_FILE = os.path.join(DATA_DIR, "db_status.json")

def check_and_clean(silent=True):
    logger.log("Starting DB Check...", "CHECK")
    logs = []
    error_details = []
    
    def log(msg):
        if not silent: print(msg)
        logs.append(msg)

    if not os.path.exists(DATA_DIR):
        logger.log("Data dir missing", "ERROR")
        return ["❌ 'data' フォルダが見つかりません。"], 0, []

    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    files = [f for f in files if "db_status.json" not in f]
    
    if not files:
        return ["⚠️ データベースファイル(.json)がありません。"], 0, []

    total_fixed = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list): continue

            ids = [q['id'] for q in data if 'id' in q and isinstance(q['id'], int)]
            max_id = max(ids) if ids else 0
            file_modified = False
            
            for q in data:
                if 'id' not in q:
                    max_id += 1
                    q['id'] = max_id
                    file_modified = True
                
                missing = []
                required = ["question", "options", "answer", "explanation"]
                for k in required:
                    if k not in q or not q[k]: missing.append(k)
                
                if "options" in q and isinstance(q["options"], dict):
                    if not q["options"].get("1") or not q["options"].get("2") or not q["options"].get("3"):
                        missing.append("options(1-3)")
                elif "options" not in q:
                    missing.append("options")

                if missing:
                    error_details.append({
                        "ファイル名": filename,
                        "ID": q.get('id', '不明'),
                        "不備項目": ", ".join(missing),
                        "状態": "要修正"
                    })

            if file_modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                total_fixed += 1
                logger.log(f"Fixed ID in {filename}", "CHECK")

        except Exception as e:
            logger.error(e, f"Error in {filename}")
            error_details.append({
                "ファイル名": filename,
                "ID": "-",
                "不備項目": str(e),
                "状態": "読込不可"
            })

    if error_details:
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(error_details, f, indent=4, ensure_ascii=False)
            logger.log(f"Found {len(error_details)} errors", "CHECK")
        except: pass
    else:
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)
        logger.log("No errors found", "CHECK")

    return logs, total_fixed, error_details

if __name__ == "__main__":
    check_and_clean(silent=False)