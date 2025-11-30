import os
import json
import glob

def get_models_and_counts():
    data_dir = "data"
    if not os.path.exists(data_dir): return {}
    
    # db_{MODEL}_{LEVEL}_{CH}.json
    files = glob.glob(os.path.join(data_dir, "db_*.json"))
    stats = {} # { "gemini-1.5-flash": {"二等": 10, "一等": 20}, ... }

    for f in files:
        fname = os.path.basename(f)
        parts = fname.split('_')
        if len(parts) >= 4:
            model = parts[1]
            level = parts[2]
            
            if model not in stats: stats[model] = {"二等": 0, "一等": 0}
            if level not in stats[model]: stats[model][level] = 0
            
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    count = len(json.load(fp))
                    stats[model][level] += count
            except: pass
    return stats

def main():
    stats = get_models_and_counts()
    
    print("-" * 60)
    print(f"   📊 現在のストック状況")
    if not stats:
        print("      (データがありません)")
    else:
        for model, counts in sorted(stats.items()):
            print(f"      🤖 {model:<20} | 二等:{counts['二等']:4d} | 一等:{counts['一等']:4d}")
    print("-" * 60)

if __name__ == "__main__":
    main()