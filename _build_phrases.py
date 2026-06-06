"""
提取所有单词的短语，汇集成一个新的单词本
- 创建 textbook "短语汇总" (book_name = 'PhrasesAll')
- 提取所有唯一短语，构造 word_json 插入 words 表
"""
import mysql.connector
import json
import random
import sys

DB_CONFIG = {
    'host': '192.168.71.189',
    'user': 'root',
    'password': 'notes123',
    'database': 'english_db'
}

BATCH_SIZE = 500   # 每批插入数
SAMPLE_LIMIT = None  # 设为 N 则只处理前 N 个有短语的单词（用于测试），None = 全部

def extract_phrases_from_word(word, word_json_str):
    """从 word_json 中提取所有短语"""
    phrases = []
    try:
        data = json.loads(word_json_str)
        wc = data.get('content', {}).get('word', {}).get('content', {})
        phrase_data = wc.get('phrase')
        if phrase_data and isinstance(phrase_data, dict):
            phrase_list = phrase_data.get('phrases', [])
            for p in phrase_list:
                pc = p.get('pContent', '').strip()
                pcn = p.get('pCn', '').strip()
                if pc:
                    phrases.append((pc, pcn, word))
    except:
        pass
    return phrases

def build_word_json(phrase, phrase_cn, source_word):
    """为短语构造 word_json"""
    word_json = {
        "headWord": phrase,
        "content": {
            "word": {
                "wordHead": phrase,
                "wordId": f"phrase_{abs(hash(phrase)) % 10**8}",
                "content": {
                    "usphone": "",
                    "ukphone": "",
                    "trans": [
                        {
                            "pos": "",
                            "tranCn": phrase_cn or f"[短语] 来自: {source_word}",
                            "tranOther": ""
                        }
                    ],
                    "phrase": {
                        "phrases": [
                            {
                                "pContent": phrase,
                                "pCn": phrase_cn or ""
                            }
                        ]
                    }
                }
            },
            "bookId": "PhrasesAll"
        }
    }
    return word_json

def main():
    print("=" * 60)
    print("短语汇总 - 单词本构建脚本")
    print("=" * 60)
    
    # 连接数据库
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)
    
    # Step 1: 计算总数据量
    print("\n[1/5] 统计有短语的单词...")
    cursor.execute("SELECT COUNT(*) as cnt FROM words WHERE word_json LIKE '%phrase%'")
    total_words = cursor.fetchone()['cnt']
    print(f"  有短语数据的单词: {total_words}")
    
    # Step 2: 分批提取所有唯一短语
    print("\n[2/5] 提取并去重短语...")
    limit_clause = f"LIMIT {SAMPLE_LIMIT}" if SAMPLE_LIMIT else ""
    cursor.execute(f"""
        SELECT word, word_json FROM words 
        WHERE word_json LIKE '%phrase%' 
        ORDER BY id {limit_clause}
    """)
    
    unique_phrases = {}  # key: phrase (lowercase), value: (phrase_display, phrase_cn, source_word)
    processed = 0
    for row in cursor.fetchall():
        phrases = extract_phrases_from_word(row['word'], row['word_json'])
        for pc, pcn, src in phrases:
            key = pc.lower()
            if key not in unique_phrases:
                unique_phrases[key] = (pc, pcn, src)
        processed += 1
        if processed % 5000 == 0:
            print(f"  已处理 {processed}/{total_words if not SAMPLE_LIMIT else SAMPLE_LIMIT} 个单词, 收集到 {len(unique_phrases)} 个唯一短语")
    
    print(f"\n  完成! 总计唯一短语: {len(unique_phrases)}")
    
    # Step 3: 创建新课本
    print("\n[3/5] 创建新课本 '短语汇总'...")
    
    # 检查是否已存在
    cursor.execute("SELECT id FROM word_textbooks WHERE book_name = 'PhrasesAll'")
    existing = cursor.fetchone()
    
    if existing:
        textbook_id = existing['id']
        print(f"  课本已存在，ID = {textbook_id}，将清空旧数据...")
        cursor.execute("DELETE FROM words WHERE textbook_id = %s", (textbook_id,))
        cursor.execute("UPDATE word_textbooks SET title = '短语汇总', alias = 'PhrasesAll', word_count = 0 WHERE id = %s", (textbook_id,))
        db.commit()
    else:
        # word_textbooks.id 不是 AUTO_INCREMENT，需手动指定
        cursor.execute("SELECT COALESCE(MAX(id), 81) + 1 FROM word_textbooks")
        next_id = cursor.fetchone()['COALESCE(MAX(id), 81) + 1']
        
        cursor.execute("""
            INSERT INTO word_textbooks (id, book_name, title, description, word_count)
            VALUES (%s, 'PhrasesAll', '短语汇总', '从所有单词中提取的短语集合，包含各类考试词汇中的常用搭配。', %s)
        """, (next_id, len(unique_phrases)))
        textbook_id = next_id
        db.commit()
        print(f"  课本已创建，ID = {textbook_id}")
    
    # Step 4: 批量插入短语单词
    print(f"\n[4/5] 批量插入 {len(unique_phrases)} 个短语到 words 表...")
    
    phrase_list = list(unique_phrases.values())
    random.shuffle(phrase_list)  # 打乱顺序
    
    sql = """
        INSERT INTO words (textbook_id, book_name, word, word_json) 
        VALUES (%s, 'PhrasesAll', %s, %s)
    """
    
    total_inserted = 0
    batch = []
    
    for display_phrase, phrase_cn, source_word in phrase_list:
        try:
            wj = build_word_json(display_phrase, phrase_cn, source_word)
            wj_str = json.dumps(wj, ensure_ascii=False)
            batch.append((textbook_id, display_phrase, wj_str))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                db.commit()
                total_inserted += len(batch)
                batch = []
                if total_inserted % 10000 == 0:
                    print(f"  已插入 {total_inserted}/{len(unique_phrases)}")
                    
        except Exception as e:
            print(f"  错误: {display_phrase} - {e}")
    
    # 最后一批
    if batch:
        cursor.executemany(sql, batch)
        db.commit()
        total_inserted += len(batch)
    
    # Step 5: 更新课本单词计数
    print(f"\n[5/5] 更新课本计数...")
    cursor.execute("UPDATE word_textbooks SET word_count = %s WHERE id = %s", (total_inserted, textbook_id))
    db.commit()
    
    print(f"\n{'=' * 60}")
    print(f"完成! 短语汇总课本 ID = {textbook_id}")
    print(f"插入短语数: {total_inserted}")
    print(f"请刷新页面查看新课本")
    print(f"{'=' * 60}")
    
    cursor.close()
    db.close()

if __name__ == '__main__':
    if '--test' in sys.argv:
        SAMPLE_LIMIT = 2000
        print("!!! 测试模式: 只处理前2000个单词 !!!")
    main()
