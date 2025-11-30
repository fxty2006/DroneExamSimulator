import google.generativeai as genai
import os
import time
import sys

# --- 設定 ---
KEY_FILE = "apikey.txt"

def main():
    print("🏥 API 健康診断ツール (自動検出版)")
    print("-" * 50)

    # 1. APIキーの読み込み
    api_key = None
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                if content: api_key = content
        except: pass
    
    if not api_key: api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ APIキーが見つかりません。apikey.txt を確認してください。")
        return

    # マスキングして表示
    if len(api_key) > 10:
        visible_key = api_key[:5] + "*" * 10 + api_key[-5:]
    else:
        visible_key = "*****"
    
    print(f"🔑 キー: {visible_key}")
    genai.configure(api_key=api_key)

    # 2. モデルの動的取得 (Generatorと同じロジック)
    print("\n🔍 Generatorと同じ基準でモデルを選別しています...")
    
    all_models = []
    recommended_models = []

    # Generatorと同じフィルタ条件
    TARGET_KEYWORDS = ["latest", "2.5", "2.0"]
    EXCLUDED_KEYWORDS = ["preview", "exp", "image", "vision", "thinking", "robotics", "nano", "tts", "gemma", "learnlm"]

    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                all_models.append(clean_name)
                
                # フィルタリング判定
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

    # テスト対象の決定
    if recommended_models:
        target_list = sorted(recommended_models, reverse=True)
        print(f"✨ {len(target_list)} 個の推奨モデルが見つかりました。これらを診断します。")
    else:
        target_list = sorted(all_models, reverse=True)
        print(f"⚠️ 推奨モデルが見つからなかったため、全モデル({len(target_list)}個)を診断します。")

    print("\n💉 接続テストを開始します...\n")

    success_count = 0

    for i, model_name in enumerate(target_list):
        # アイコン装飾 (Generatorと合わせる)
        icon = "  "
        if "latest" in model_name: icon = "🆕"
        elif "2.5" in model_name:  icon = "🚀"
        type_icon = ""
        if "pro" in model_name: type_icon = "👑"
        elif "flash" in model_name: type_icon = "⚡"
        
        display_name = f"{icon} {type_icon} {model_name}"
        print(f"   {i+1:>2}. {display_name:<30} ...", end=" ")
        
        try:
            model = genai.GenerativeModel(model_name)
            # 負荷をかけないよう、ごく短い挨拶だけさせる
            response = model.generate_content("Hello")
            
            if response.text:
                print("✅ [正常]")
                success_count += 1
            else:
                print("⚠️ [空応答]")

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                print("📉 [429 Limit]") # リソース枯渇
            elif "404" in err_msg:
                print("❌ [404 Not Found]")
            else:
                short_err = err_msg.split('\n')[0][:30]
                print(f"❌ [Error] {short_err}...")

        time.sleep(0.5) # 連続アクセス制限を防ぐため少し待つ

    print("-" * 50)
    print(f"📝 診断終了 (正常: {success_count} / 対象: {len(target_list)})")

if __name__ == "__main__":
    main()