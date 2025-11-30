import csv
import json
import os
import shutil
import glob
import datetime

# 設定
DATA_DIR = "data"
CSV_DIR = os.path.join(DATA_DIR, "csv_review")   # CSVがあるフォルダ
BACKUP_DIR = os.path.join(DATA_DIR, "backup_json") # バックアップ保存先

def main():
    print("📥 データベース一括修正ツール (詳細表示版)")
    print("-" * 60)

    # 1. フォルダの存在確認
    if not os.path.exists(CSV_DIR):
        print(f"❌ '{CSV_DIR}' フォルダが見つかりません。")
        print("   先に export_review.py を実行してください。")
        return

    # バックアップフォルダの作成
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"📁 バックアップ用フォルダを作成しました: {BACKUP_DIR}")

    # 2. ファイルリストの取得
    csv_paths = glob.glob(os.path.join(CSV_DIR, "*.csv"))
    json_paths = glob.glob(os.path.join(DATA_DIR, "db_*.json"))

    csv_filenames = {os.path.basename(p) for p in csv_paths}
    json_filenames = {os.path.basename(p) for p in json_paths}

    # 3. マッチング処理
    update_targets = []  # 更新対象
    missing_json = []    # JSON不足 (CSVはあるがJSONがない)
    missing_csv = []     # CSV不足  (JSONはあるがCSVがない)

    # CSV基準でチェック
    for csv_file in csv_filenames:
        target_json = csv_file.replace(".csv", ".json")
        if target_json in json_filenames:
            update_targets.append(target_json)
        else:
            missing_json.append(csv_file)

    # JSON基準でチェック
    for json_file in json_filenames:
        target_csv = json_file.replace(".json", ".csv")
        if target_csv not in csv_filenames:
            missing_csv.append(json_file)

    # 4. 状況報告
    print(f"\n📂 検出: JSON {len(json_filenames)} ファイル / CSV {len(csv_filenames)} ファイル\n")

    print(f"   ✅ 更新対象 (マッチ): {len(update_targets)} ファイル")
    
    if missing_json:
        print(f"   ⚠️ 更新不可 (JSONなし): {len(missing_json)} ファイル")
        print("      (以下のCSVは適用先がないため無視されます)")
        for f in sorted(missing_json):
            print(f"         ・ {f}")
    
    if missing_csv:
        print(f"   ℹ️ 対象外 (CSVなし): {len(missing_csv)} ファイル")
        print("      (以下のJSONはCSVがないため変更されません)")
        for f in sorted(missing_csv):
            print(f"         ・ {f}")

    if not update_targets:
        print("\n❌ 更新可能なペアが見つかりませんでした。処理を終了します。")
        return

    # 5. 実行確認
    print("\n   上記の内容でインポートを実行しますか？ (y/n)")
    if input("   > ").strip().lower() != 'y':
        print("キャンセルしました。")
        return

    # 6. CSV読み込みと適用処理
    print("\n📖 データを読み込んで適用しています...")
    
    updates_by_file = {}
    
    for csv_path in csv_paths:
        csv_name = os.path.basename(csv_path)
        expected_json = csv_name.replace(".csv", ".json")
        
        # JSONが存在しないCSVは読み込まない
        if expected_json not in json_filenames:
            continue

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    model_name = row.get("モデル(ファイル名)")
                    if not model_name: continue
                    
                    filename = f"db_{model_name}.json"
                    if filename not in updates_by_file:
                        updates_by_file[filename] = []
                    updates_by_file[filename].append(row)
        except Exception as e:
            print(f"❌ 読込エラー: {csv_name} - {e}")

    if not updates_by_file:
        print("⚠️ 更新すべきデータが見つかりませんでした。")
        return

    # JSON更新実行
    success_count = 0
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for filename, rows in updates_by_file.items():
        json_path = os.path.join(DATA_DIR, filename)
        
        if not os.path.exists(json_path):
            continue

        try:
            # バックアップ処理
            backup_filename = f"{filename}_{now_str}.bak"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)
            shutil.copy2(json_path, backup_path)
            
            # JSON読み込み
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # IDマップ作成
            data_map = {str(q['id']): q for q in data if 'id' in q}
            update_count = 0

            for row in rows:
                q_id = str(row.get("ID", -1))
                if q_id in data_map:
                    target = data_map[q_id]
                    target['question'] = row.get("問題文", target['question'])
                    target['answer'] = row.get("正解", target['answer'])
                    target['explanation'] = row.get("解説", target['explanation'])
                    
                    if 'options' not in target: target['options'] = {}
                    target['options']['1'] = row.get("選択肢1", target['options'].get('1', ''))
                    target['options']['2'] = row.get("選択肢2", target['options'].get('2', ''))
                    target['options']['3'] = row.get("選択肢3", target['options'].get('3', ''))
                    
                    update_count += 1

            # JSON書き戻し
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print(f"   ✅ 更新完了: {filename} ({update_count}件)")
            # バックアップファイル名は長くなるので表示は省略気味に
            # print(f"      📦 バックアップ: backup_json/{backup_filename}")
            success_count += 1

        except Exception as e:
            print(f"   ❌ 更新エラー: {filename} - {e}")

    print("-" * 60)
    print(f"🎉 処理完了 (更新: {success_count}ファイル)")

if __name__ == "__main__":
    main()