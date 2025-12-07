import csv
import json
import os
import shutil
import glob
import datetime
import logger  # 共通ログを使用

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_DIR = os.path.join(DATA_DIR, "csv_review")
BACKUP_DIR = os.path.join(DATA_DIR, "backup_json")

def run_import():
    logger.log("Starting Import...", "IMPORT")
    if not os.path.exists(CSV_DIR): return 0, 0
    if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)

    csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
    json_files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    json_filenames = {os.path.basename(p) for p in json_files}
    
    updates_by_file = {}
    
    for csv_path in csv_files:
        csv_name = os.path.basename(csv_path)
        expected_json = csv_name.replace(".csv", ".json")
        
        if expected_json in json_filenames:
            try:
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    updates_by_file[expected_json] = list(reader)
            except Exception as e:
                logger.error(e, f"CSV read failed {csv_name}")

    file_count = 0
    total_update_count = 0
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for filename, rows in updates_by_file.items():
        json_path = os.path.join(DATA_DIR, filename)
        file_updated_items = 0
        try:
            shutil.copy2(json_path, os.path.join(BACKUP_DIR, f"{filename}_{now_str}.bak"))
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data_map = {str(q['id']): q for q in data if 'id' in q}
            
            for row in rows:
                q_id = str(row.get("ID", -1))
                if q_id in data_map:
                    target = data_map[q_id]
                    target['question'] = row.get("問題文", target.get('question',''))
                    target['answer'] = row.get("正解", target.get('answer',''))
                    target['explanation'] = row.get("解説", target.get('explanation',''))
                    if 'options' not in target: target['options'] = {}
                    target['options']['1'] = row.get("選択肢1", target['options'].get('1',''))
                    target['options']['2'] = row.get("選択肢2", target['options'].get('2',''))
                    target['options']['3'] = row.get("選択肢3", target['options'].get('3',''))
                    file_updated_items += 1
            
            if file_updated_items > 0:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                file_count += 1
                total_update_count += file_updated_items
                logger.log(f"Updated {filename}: {file_updated_items} items", "IMPORT")

        except Exception as e:
            logger.error(e, f"Update failed {filename}")
        
    logger.log(f"Import finished: {file_count} files", "IMPORT")
    return file_count, total_update_count

if __name__ == "__main__":
    run_import()