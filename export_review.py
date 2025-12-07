import json
import glob
import os
import csv
import logger  # 共通ログを使用

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_DIR = os.path.join(DATA_DIR, "csv_review")

def clean_text(text):
    if not text: return ""
    return str(text).replace("\n", " ").replace("\r", "")

def run_export():
    logger.log("Starting Export...", "EXPORT")
    if not os.path.exists(DATA_DIR): return 0, 0, "データフォルダなし"
    if not os.path.exists(CSV_DIR): os.makedirs(CSV_DIR)

    files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    files = [f for f in files if "db_status.json" not in f]

    file_count = 0
    total_questions = 0
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list): continue

            fname = os.path.basename(filepath)
            csv_filename = fname.replace(".json", ".csv")
            output_path = os.path.join(CSV_DIR, csv_filename)
            model_name = fname.replace("db_", "").replace(".json", "")

            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["モデル", "ID", "レベル", "章", "問題文", "選択肢1", "選択肢2", "選択肢3", "正解", "解説"])
                
                for q in data:
                    ops = q.get('options', {})
                    writer.writerow([
                        model_name, q.get('id',''), q.get('level',''), q.get('chapter',''),
                        clean_text(q.get('question','')), 
                        clean_text(ops.get('1','')), clean_text(ops.get('2','')), clean_text(ops.get('3','')),
                        q.get('answer',''), clean_text(q.get('explanation',''))
                    ])
                    total_questions += 1
            file_count += 1
        except Exception as e:
            logger.error(e, f"Export failed {fname}")
        
    logger.log(f"Export finished: {file_count} files", "EXPORT")
    return file_count, total_questions, CSV_DIR

if __name__ == "__main__":
    run_export()