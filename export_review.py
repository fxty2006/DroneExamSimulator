import json
import glob
import os
import csv

# 設定
DATA_DIR = "data"
CSV_DIR = os.path.join(DATA_DIR, "csv_review") # CSV専用フォルダ

def clean_text(text):
    """Excelで見やすいように改行をスペースに置換"""
    if not text: return ""
    return str(text).replace("\n", " ").replace("\r", "")

def main():
    print("📊 データベース個別出力ツール (AIレビュー用)")
    print("-" * 50)
    
    if not os.path.exists(DATA_DIR):
        print("❌ 'data' フォルダがありません。")
        return

    # 保存用フォルダ作成
    if not os.path.exists(CSV_DIR):
        os.makedirs(CSV_DIR)
        print(f"📁 保存用フォルダを作成しました: {CSV_DIR}")

    files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    if not files:
        print("❌ JSONファイルが見つかりません。問題を生成してください。")
        return

    print(f"📂 {len(files)} 個のファイルを処理します...\n")

    total_files = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        # 拡張子を .csv に変更
        csv_filename = filename.replace(".json", ".csv")
        output_path = os.path.join(CSV_DIR, csv_filename)
        
        # モデル名抽出
        model_name = filename.replace("db_", "").replace(".json", "")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list): continue
            
            # CSV書き込み (各ファイルごと)
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # ヘッダー行
                writer.writerow([
                    "モデル(ファイル名)", "ID", "レベル", "章", 
                    "問題文", "選択肢1", "選択肢2", "選択肢3", 
                    "正解", "解説"
                ])

                count = 0
                for q in data:
                    ops = q.get('options', {})
                    writer.writerow([
                        model_name,
                        q.get('id', ''),
                        q.get('level', ''),
                        q.get('chapter', ''),
                        clean_text(q.get('question', '')),
                        clean_text(ops.get('1', '')),
                        clean_text(ops.get('2', '')),
                        clean_text(ops.get('3', '')),
                        q.get('answer', ''),
                        clean_text(q.get('explanation', ''))
                    ])
                    count += 1
            
            print(f"   ✅ 出力: {csv_filename} ({count}問)")
            total_files += 1

        except Exception as e:
            print(f"   ⚠️ エラー: {filename} - {e}")

    print("-" * 50)
    print(f"🎉 完了！ 合計 {total_files} 個のCSVファイルを以下に出力しました。")
    print(f"👉 フォルダ: {CSV_DIR}")

if __name__ == "__main__":
    main()