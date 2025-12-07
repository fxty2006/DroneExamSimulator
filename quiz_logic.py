import os
import json
import glob
import random
import re
from collections import defaultdict
import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "exam_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(e, "Config load failed")
    return {}

def get_available_models_info():
    logger.log("Scanning stock...", "QUIZ")
    files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    stats = defaultdict(lambda: {'total': 0, '二等': 0, '一等': 0})
    
    for f in files:
        fname = os.path.basename(f)
        if not fname.startswith("db_"): continue
        
        # ファイル名解析: db_{model}_{level}_{chapter}.json
        # split('_') だとモデル名の中のアンダースコアで崩れるため、後ろから解析する等の工夫が必要だが
        # ここでは簡易的に「拡張子除去」「先頭db_除去」してから分解を試みる
        core_name = fname[3:-5] # "db_" と ".json" を除く
        parts = core_name.split('_')
        
        if len(parts) >= 3:
            chapter = parts[-1]
            level = parts[-2]
            # 残りがモデル名
            model_name = "_".join(parts[:-2])
            
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    count = len(data)
                    stats[model_name]['total'] += count
                    if level in stats[model_name]:
                        stats[model_name][level] += count
            except: pass
    return dict(stats)

def count_total_questions():
    info = get_available_models_info()
    return sum(m['total'] for m in info.values())

def get_exam_questions(level, total_count_request, target_model=None):
    logger.log(f"Exam Req: {level}, {total_count_request}qs, Model={target_model}", "QUIZ")
    
    files = glob.glob(os.path.join(DATA_DIR, "db_*.json"))
    candidates = []
    
    for f in files:
        fname = os.path.basename(f)
        
        # ファイル名からモデル名を抽出
        # db_{model}_{level}_{ch}.json
        core_name = fname[3:-5]
        parts = core_name.split('_')
        if len(parts) >= 3:
            current_file_model = "_".join(parts[:-2])
        else:
            current_file_model = "unknown"

        # モデル指定がある場合のフィルタリング
        if target_model and current_file_model != target_model:
            continue
        
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                # レベル一致チェック
                for q in data:
                    if q.get('level') == level:
                        # ★重要: 出典情報をデータに注入する
                        q['source_model'] = current_file_model
                        candidates.append(q)
                        
        except Exception as e:
            logger.error(e, f"Read error {fname}")
    
    if not candidates:
        logger.log("No candidates.", "WARN")
        return []

    # 以下、ウェイト処理等は変更なし
    config = load_config()
    weights = {}
    if level in config:
        weights = config[level].get("weights", {})
    
    if not weights:
        if len(candidates) <= total_count_request:
            random.shuffle(candidates)
            return candidates
        return random.sample(candidates, total_count_request)

    grouped_qs = defaultdict(list)
    def extract_chapter_num(text):
        m = re.search(r'第(\d+)章', str(text))
        return m.group(1) if m else "others"

    for q in candidates:
        ch_num = extract_chapter_num(q.get('chapter', ''))
        grouped_qs[ch_num].append(q)

    final_questions = []
    for ch_key, count in weights.items():
        ch_num = extract_chapter_num(ch_key)
        target_group = grouped_qs.get(ch_num, [])
        
        k = min(len(target_group), count)
        if k > 0:
            selected = random.sample(target_group, k)
            final_questions.extend(selected)
            for s in selected:
                if s in target_group: target_group.remove(s)

    shortage = total_count_request - len(final_questions)
    if shortage > 0:
        remainders = []
        for q_list in grouped_qs.values():
            remainders.extend(q_list)
        if remainders:
            k = min(len(remainders), shortage)
            final_questions.extend(random.sample(remainders, k))

    random.shuffle(final_questions)
    return final_questions