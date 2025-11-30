import os
import json
import glob

DATA_DIR = "data"

def check_and_clean():
    print("\n🔍 データベースの診断とID管理を行います...\n")
    
    # 1. フォルダ自体の存在チェック
    if not os.path.exists(DATA_DIR):
        print("❌ 'data' フォルダが見つかりません。")
        print("   先に [1] 問題を作成する (Generator) を実行してください。")
        return

    # 2. JSONファイルの存在チェック (ここを追加)
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not files:
        print("⚠️ データベースファイル(.json)がまだありません。")
        print("   先に [1] 問題を作成する (Generator) を実行して、問題を作ってください。")
        return

    files_to_update = []
    total_errors = 0

    print(f"📂 {len(files)} 個のファイルを検査します...\n")

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list): continue

            valid_data = []
            # ファイル内の最大IDを探す
            ids = [q['id'] for q in data if 'id' in q and isinstance(q['id'], int)]
            max_id = max(ids) if ids else 0
            modified = False
            file_err = 0

            for q in data:
                # 必須項目チェック
                if all(k in q for k in ["question", "options", "answer", "explanation"]) and q["options"]:
                    # IDチェック
                    if 'id' not in q:
                        max_id += 1
                        q['id'] = max_id
                        modified = True
                    valid_data.append(q)
                else:
                    file_err += 1
                    modified = True # 不良データ削除

            total_errors += file_err
            msg = f"   📄 {filename} : "
            if file_err > 0: msg += f"⚠️不備{file_err}件 "
            if modified and file_err == 0: msg += "🆔ID付与 "
            if not modified and file_err == 0: msg += "✅正常"
            print(msg)

            if modified:
                files_to_update.append((filepath, valid_data))

        except Exception as e:
            print(f"❌ 読込エラー {filename}: {e}")

    print("-" * 60)
    if not files_to_update:
        print("✨ 全データ正常です。修復の必要はありません。")
        return

    print(f"\n🛠️ {len(files_to_update)} ファイルの更新が必要です（ID付与または不良削除）。")
    if input("   実行しますか？ (y/n) > ").strip().lower() == 'y':
        for path, data in files_to_update:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        print("✨ 完了しました。")
    else:
        print("キャンセルしました。")

if __name__ == "__main__":
    check_and_clean()