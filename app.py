from flask import Flask, request, jsonify, g, send_from_directory
import mysql.connector
from mysql.connector import pooling
from datetime import datetime
import hashlib
import jwt
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'english-learning-secret-key-2024'

# Database pool
db_pool = pooling.MySQLConnectionPool(
    pool_name="english_pool",
    pool_size=5,
    host='127.0.0.1',
    user='root',
    password='notes123',
    database='english_db'
)

def get_db():
    return db_pool.get_connection()

def parse_word_json(word_json_str):
    """解析单词JSON，返回结构化数据"""
    import json
    try:
        data = json.loads(word_json_str)
        content = data.get('content', {})
        word = content.get('word', {})
        word_content = word.get('content', {})
        
        # 提取翻译（中文释义）
        trans = word_content.get('trans', [])
        meanings = []
        meaning_en = ''
        for t in trans:
            pos = t.get('pos', '')
            tran_cn = t.get('tranCn', '').strip()
            tran_other = t.get('tranOther', '').strip()
            if tran_cn:
                if pos:
                    meanings.append(f"{pos} {tran_cn}")
                else:
                    meanings.append(tran_cn)
            if tran_other and not meaning_en:
                meaning_en = tran_other
        
        # 提取例句
        sentences = []
        sentence_data = word_content.get('sentence', {})
        if sentence_data:
            for sent in sentence_data.get('sentences', [])[:3]:
                s_content = sent.get('sContent', '').strip()
                s_cn = sent.get('sCn', '').strip()
                if s_content:
                    sentences.append({'en': s_content, 'cn': s_cn})
        
        # 提取音标
        us_phone = word_content.get('usphone', '')
        uk_phone = word_content.get('ukphone', '')
        
        # 提取短语
        phrases = []
        phrase_data = word_content.get('phrase', {})
        if phrase_data:
            for p in phrase_data.get('phrases', [])[:5]:
                p_content = p.get('pContent', '').strip()
                p_cn = p.get('pCn', '').strip()
                if p_content:
                    phrases.append({'en': p_content, 'cn': p_cn})
        
        # 提取美音/英音发音参数
        us_speech = word_content.get('usspeech', '')
        uk_speech = word_content.get('ukspeech', '')
        
        return {
            'word': data.get('headWord', ''),
            'usphone': us_phone,
            'ukphone': uk_phone,
            'meaning': '；'.join(meanings) if meanings else '',
            'meaning_en': meaning_en,
            'examples': sentences,
            'phrases': phrases,
            'usspeech': us_speech,
            'ukspeech': uk_speech,
            'raw': data
        }
    except:
        return None

def make_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_token(token):
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return data
    except:
        return None

def token_required(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        data = verify_token(token)
        if not data:
            return jsonify({'error': '未登录'}), 401
        g.user_id = data['user_id']
        g.username = data['username']
        g.role = data['role']
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    @token_required
    def wrapper(*args, **kwargs):
        if g.role != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ============ 认证相关 ============

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3 or len(password) < 6:
        return jsonify({'error': '用户名至少3位，密码至少6位'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({'error': '用户名已存在'}), 400
    
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')",
        (username, make_password(password))
    )
    db.commit()
    
    user_id = cursor.lastrowid
    cursor.close()
    db.close()
    
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'role': 'user',
        'exp': int(time.time()) + 86400 * 30
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({'token': token, 'user': {'id': user_id, 'username': username, 'role': 'user'}})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not user or user['password'] != make_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': int(time.time()) + 86400 * 30
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': {'id': user['id'], 'username': user['username'], 'role': user['role']}
    })

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_me():
    return jsonify({'id': g.user_id, 'username': g.username, 'role': g.role})

# ============ 单词课本 ============

@app.route('/api/textbooks', methods=['GET'])
def get_textbooks():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.id, t.title as name, t.book_name, t.alias, COUNT(r.id) as word_count 
        FROM word_textbooks t 
        LEFT JOIN words r ON t.id = r.textbook_id 
        GROUP BY t.id 
        ORDER BY t.id
    """)
    textbooks = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(textbooks)

@app.route('/api/textbooks/<int:id>', methods=['GET'])
def get_textbook(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM word_textbooks WHERE id = %s", (id,))
    textbook = cursor.fetchone()
    cursor.close()
    db.close()
    return jsonify(textbook or {})

# ============ 单词 ============

@app.route('/api/textbooks/<int:textbook_id>/words', methods=['GET'])
@token_required
def get_textbook_words(textbook_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 获取该课本的所有单词（直接从words表，按textbook_id筛选）
    cursor.execute("""
        SELECT id, textbook_id, book_name, word, word_json 
        FROM words 
        WHERE textbook_id = %s
        ORDER BY word
    """, (textbook_id,))
    words = cursor.fetchall()
    cursor.close()
    db.close()
    
    # 直接返回word_json，前端解析
    result = []
    for w in words:
        parsed = parse_word_json(w['word_json'])
        w['parsed'] = parsed  # 保留解析结果
        result.append(w)
    
    return jsonify(result)

@app.route('/api/words/<int:id>', methods=['GET'])
@token_required
def get_word(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, textbook_id, book_name, word, word_json FROM words WHERE id = %s", (id,))
    word_row = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not word_row:
        return jsonify({})
    
    # 解析JSON并返回
    parsed = parse_word_json(word_row['word_json'])
    if parsed:
        parsed['id'] = word_row['id']
        parsed['textbook_id'] = word_row['textbook_id']
        parsed['word_json'] = word_row['word_json']
        return jsonify(parsed)
    return jsonify({})

@app.route('/api/words/random', methods=['GET'])
@token_required
def get_random_word():
    """根据播放次数获取随机单词"""
    textbook_id = request.args.get('textbook_id', type=int)
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 先获取当前播放次数分布
    cursor.execute("""
        SELECT w.id, COALESCE(wpr.play_count, 0) as play_count
        FROM words w
        LEFT JOIN word_play_records wpr ON w.id = wpr.word_id 
            AND wpr.user_id = %s AND wpr.textbook_id = %s
        WHERE w.textbook_id = %s
    """, (g.user_id, textbook_id, textbook_id))
    
    records = cursor.fetchall()
    
    # 找出最小播放次数
    min_count = min(r['play_count'] for r in records) if records else 0
    
    # 从最小次数的单词中随机选一个
    min_words = [r for r in records if r['play_count'] == min_count]
    import random
    selected = random.choice(min_words)
    
    # 获取单词详情
    cursor.execute("SELECT id, textbook_id, book_name, word, word_json FROM words WHERE id = %s", (selected['id'],))
    word_row = cursor.fetchone()
    
    # 解析JSON，并返回word_json供前端使用
    word = None
    if word_row:
        parsed = parse_word_json(word_row['word_json'])
        if parsed:
            parsed['id'] = word_row['id']
            parsed['textbook_id'] = word_row['textbook_id']
            parsed['word_json'] = word_row['word_json']  # 返回原始JSON供前端解析
            word = parsed
    
    # 更新播放次数
    cursor.execute("""
        INSERT INTO word_play_records (user_id, word_id, textbook_id, play_count)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE play_count = play_count + 1
    """, (g.user_id, selected['id'], textbook_id))
    db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({
        'word': word or {},
        'min_count': min_count,
        'min_word_count': len(min_words)
    })

@app.route('/api/words/<int:id>/wrong', methods=['POST'])
@token_required
def record_wrong(id):
    """记录答错"""
    textbook_id = request.json.get('textbook_id')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO word_wrong_counts (user_id, word_id, textbook_id, wrong_count)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE wrong_count = wrong_count + 1
    """, (g.user_id, id, textbook_id))
    db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({'message': '记录成功'})

@app.route('/api/words/<int:id>/quiz-correct', methods=['POST'])
@token_required
def record_quiz_correct(id):
    """记录背单词答对，记录背诵次数"""
    data = request.get_json()
    textbook_id = data.get('textbook_id')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO word_quiz_records (user_id, word_id, textbook_id, quiz_count)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE quiz_count = quiz_count + 1
    """, (g.user_id, id, textbook_id))
    db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({'message': '记录成功'})

@app.route('/api/words/<int:id>/wrong-review-correct', methods=['POST'])
@token_required
def record_wrong_review_correct(id):
    """记录错题复习答对（首次答对才计数）"""
    data = request.get_json()
    textbook_id = data.get('textbook_id')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO word_wrong_review_records (user_id, word_id, textbook_id, correct_count)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE correct_count = correct_count + 1
    """, (g.user_id, id, textbook_id))
    db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({'message': '记录成功'})

@app.route('/api/textbooks/<int:textbook_id>/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(textbook_id):
    """获取答错过的单词，按错题次数排序"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT w.id, w.textbook_id, w.book_name, w.word, w.word_json,
               COALESCE(wwc.wrong_count, 0) as wrong_count
        FROM words w
        LEFT JOIN word_wrong_counts wwc ON w.id = wwc.word_id 
            AND wwc.user_id = %s AND wwc.textbook_id = %s
        WHERE w.textbook_id = %s AND COALESCE(wwc.wrong_count, 0) > 0
        ORDER BY wrong_count DESC
    """, (g.user_id, textbook_id, textbook_id))
    
    words = cursor.fetchall()
    
    # 解析JSON
    result = []
    for w in words:
        parsed = parse_word_json(w['word_json'])
        if parsed:
            parsed['id'] = w['id']
            parsed['textbook_id'] = w['textbook_id']
            parsed['wrong_count'] = w['wrong_count']
            parsed['word_json'] = w['word_json']  # 返回原始JSON供前端解析
            result.append(parsed)
    
    cursor.close()
    db.close()
    return jsonify(result)

@app.route('/api/textbooks/<int:textbook_id>/wrong-words-with-options', methods=['GET'])
@token_required
def get_wrong_words_with_options(textbook_id):
    """获取答错过的单词（带选项），按(错题次数-答对次数)降序，只显示差值>0的"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT w.id, w.textbook_id, w.book_name, w.word, w.word_json,
               COALESCE(wwc.wrong_count, 0) as wrong_count,
               COALESCE(wwrc.correct_count, 0) as correct_count,
               (COALESCE(wwc.wrong_count, 0) - COALESCE(wwrc.correct_count, 0)) as diff_count
        FROM words w
        LEFT JOIN word_wrong_counts wwc ON w.id = wwc.word_id 
            AND wwc.user_id = %s AND wwc.textbook_id = %s
        LEFT JOIN word_wrong_review_records wwrc ON w.id = wwrc.word_id 
            AND wwrc.user_id = %s AND wwrc.textbook_id = %s
        WHERE w.textbook_id = %s 
            AND COALESCE(wwc.wrong_count, 0) > 0
            AND (COALESCE(wwc.wrong_count, 0) - COALESCE(wwrc.correct_count, 0)) > 0
        ORDER BY diff_count DESC
    """, (g.user_id, textbook_id, g.user_id, textbook_id, textbook_id))
    
    words = cursor.fetchall()
    
    # 解析JSON
    parsed_words = []
    all_meanings = []
    for w in words:
        parsed = parse_word_json(w['word_json'])
        if parsed:
            parsed['id'] = w['id']
            parsed['textbook_id'] = w['textbook_id']
            parsed['wrong_count'] = w['wrong_count']
            parsed['word_json'] = w['word_json']  # 返回原始JSON供前端解析
            parsed_words.append(parsed)
            if parsed.get('meaning'):
                all_meanings.append(parsed['meaning'])
    
    # 如果错题太少，从课本所有单词获取选项
    if len(parsed_words) < 4:
        cursor.execute("""
            SELECT word_json FROM words WHERE textbook_id = %s
        """, (textbook_id,))
        for row in cursor.fetchall():
            parsed = parse_word_json(row['word_json'])
            if parsed and parsed.get('meaning'):
                all_meanings.append(parsed['meaning'])
    
    import random
    for w in parsed_words:
        correct_meaning = w.get('meaning', '')
        wrong_options = [m for m in all_meanings if m != correct_meaning]
        random.shuffle(wrong_options)
        w['options'] = [correct_meaning] + wrong_options[:3]
        random.shuffle(w['options'])
    
    cursor.close()
    db.close()
    return jsonify({'words': parsed_words})

@app.route('/api/textbooks/<int:textbook_id>/quiz-words', methods=['GET'])
@token_required
def get_quiz_words(textbook_id):
    """获取用于背单词的单词（一次只查一条）
    返回：当前单词 + 背诵次数最小的单词数量
    """
    import random
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 查询一条单词（学过的，按背诵次数升序）
    cursor.execute("""
        SELECT w.id, w.textbook_id, w.book_name, w.word, w.word_json,
               COALESCE(wqr.quiz_count, 0) as quiz_count
        FROM words w
        LEFT JOIN word_play_records wpr ON w.id = wpr.word_id 
            AND wpr.user_id = %s
        LEFT JOIN word_quiz_records wqr ON w.id = wqr.word_id 
            AND wqr.user_id = %s AND wqr.textbook_id = %s
        WHERE w.textbook_id = %s AND COALESCE(wpr.play_count, 0) > 0
        ORDER BY quiz_count ASC, w.id ASC
        LIMIT 1
    """, (g.user_id, g.user_id, textbook_id, textbook_id))
    
    word_row = cursor.fetchone()
    
    if not word_row:
        cursor.close()
        db.close()
        return jsonify({'word': None, 'min_quiz_word_count': 0})
    
    # 解析单词JSON
    parsed = parse_word_json(word_row['word_json'])
    if not parsed:
        cursor.close()
        db.close()
        return jsonify({'word': None, 'min_quiz_word_count': 0})
    
    parsed['id'] = word_row['id']
    parsed['textbook_id'] = word_row['textbook_id']
    parsed['quiz_count'] = word_row['quiz_count']
    parsed['word_json'] = word_row['word_json']
    
    # 获取该单词的meaning用于生成选项
    correct_meaning = parsed.get('meaning', '')
    
    # 查询该课本的所有单词，解析出meaning用于生成错误选项
    cursor.execute("""
        SELECT word_json FROM words 
        WHERE textbook_id = %s AND word_json IS NOT NULL
    """, (textbook_id,))
    all_word_json = cursor.fetchall()
    
    # 解析所有meaning
    all_meanings = []
    for row in all_word_json:
        p = parse_word_json(row['word_json'])
        if p and p.get('meaning') and p['meaning'] != correct_meaning:
            all_meanings.append(p['meaning'])
    
    # 去重并随机打乱
    all_meanings = list(set(all_meanings))
    random.shuffle(all_meanings)
    
    # 生成3个错误选项
    options = [correct_meaning] + all_meanings[:3]
    random.shuffle(options)
    parsed['options'] = options
    
    # 计算背诵次数最少的单词数量
    min_quiz_count = word_row['quiz_count']
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM words w
        LEFT JOIN word_play_records wpr ON w.id = wpr.word_id AND wpr.user_id = %s
        LEFT JOIN word_quiz_records wqr ON w.id = wqr.word_id AND wqr.user_id = %s AND wqr.textbook_id = %s
        WHERE w.textbook_id = %s AND COALESCE(wpr.play_count, 0) > 0
        AND COALESCE(wqr.quiz_count, 0) = %s
    """, (g.user_id, g.user_id, textbook_id, textbook_id, min_quiz_count))
    min_quiz_word_count = cursor.fetchone()['cnt']
    
    cursor.close()
    db.close()
    return jsonify({
        'word': parsed,
        'min_quiz_count': min_quiz_count,
        'min_quiz_word_count': min_quiz_word_count
    })

@app.route('/api/textbooks/<int:textbook_id>/wrong-word', methods=['GET'])
@token_required
def get_wrong_word(textbook_id):
    """获取一条错题复习单词（按差值降序）
    差值 = 答错次数 - 复习答对次数
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 获取一条差值>0的单词
    cursor.execute("""
        SELECT w.id, w.textbook_id, w.book_name, w.word, w.word_json,
               COALESCE(wwc.wrong_count, 0) as wrong_count,
               COALESCE(wwrc.correct_count, 0) as correct_count,
               (COALESCE(wwc.wrong_count, 0) - COALESCE(wwrc.correct_count, 0)) as diff_count
        FROM words w
        LEFT JOIN word_wrong_counts wwc ON w.id = wwc.word_id 
            AND wwc.user_id = %s AND wwc.textbook_id = %s
        LEFT JOIN word_wrong_review_records wwrc ON w.id = wwrc.word_id 
            AND wwrc.user_id = %s AND wwrc.textbook_id = %s
        WHERE w.textbook_id = %s 
            AND COALESCE(wwc.wrong_count, 0) > 0
            AND (COALESCE(wwc.wrong_count, 0) - COALESCE(wwrc.correct_count, 0)) > 0
        ORDER BY diff_count DESC
        LIMIT 1
    """, (g.user_id, textbook_id, g.user_id, textbook_id, textbook_id))
    
    word_row = cursor.fetchone()
    
    if not word_row:
        cursor.close()
        db.close()
        return jsonify({'word': None, 'wrong_word_count': 0})
    
    # 解析单词JSON
    parsed = parse_word_json(word_row['word_json'])
    if not parsed:
        cursor.close()
        db.close()
        return jsonify({'word': None, 'wrong_word_count': 0})
    
    parsed['id'] = word_row['id']
    parsed['textbook_id'] = word_row['textbook_id']
    parsed['wrong_count'] = word_row['wrong_count']
    parsed['correct_count'] = word_row['correct_count']
    parsed['diff_count'] = word_row['diff_count']
    parsed['word_json'] = word_row['word_json']
    
    # 获取该单词的meaning用于生成选项
    correct_meaning = parsed.get('meaning', '')
    
    # 查询该课本的所有单词，解析出meaning用于生成错误选项
    cursor.execute("""
        SELECT word_json FROM words 
        WHERE textbook_id = %s AND word_json IS NOT NULL
    """, (textbook_id,))
    all_word_json = cursor.fetchall()
    
    # 解析所有meaning
    all_meanings = []
    for row in all_word_json:
        p = parse_word_json(row['word_json'])
        if p and p.get('meaning') and p['meaning'] != correct_meaning:
            all_meanings.append(p['meaning'])
    
    # 去重并随机打乱
    import random
    all_meanings = list(set(all_meanings))
    random.shuffle(all_meanings)
    
    # 生成3个错误选项
    options = [correct_meaning] + all_meanings[:3]
    random.shuffle(options)
    parsed['options'] = options
    
    # 计算剩余错题数量
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM words w
        LEFT JOIN word_wrong_counts wwc ON w.id = wwc.word_id 
            AND wwc.user_id = %s AND wwc.textbook_id = %s
        LEFT JOIN word_wrong_review_records wwrc ON w.id = wwrc.word_id 
            AND wwrc.user_id = %s AND wwrc.textbook_id = %s
        WHERE w.textbook_id = %s 
            AND COALESCE(wwc.wrong_count, 0) > 0
            AND (COALESCE(wwc.wrong_count, 0) - COALESCE(wwrc.correct_count, 0)) > 0
    """, (g.user_id, textbook_id, g.user_id, textbook_id, textbook_id))
    wrong_word_count = cursor.fetchone()['cnt']
    
    cursor.close()
    db.close()
    return jsonify({
        'word': parsed,
        'wrong_word_count': wrong_word_count
    })

# ============ 管理员API ============

@app.route('/api/admin/words', methods=['POST'])
@admin_required
def add_word():
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO words (word, phonetic, meaning, image_url, example_sentence, audio_path)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data.get('word'),
        data.get('phonetic'),
        data.get('meaning'),
        data.get('image_url'),
        data.get('example_sentence'),
        data.get('audio_path')
    ))
    db.commit()
    word_id = cursor.lastrowid
    
    # 关联课本
    textbook_ids = data.get('textbook_ids', [])
    for tid in textbook_ids:
        cursor.execute(
            "INSERT INTO word_textbook_relations (word_id, textbook_id) VALUES (%s, %s)",
            (word_id, tid)
        )
        # 更新课本单词数
        cursor.execute("""
            UPDATE word_textbooks SET word_count = (
                SELECT COUNT(*) FROM word_textbook_relations WHERE textbook_id = %s
            ) WHERE id = %s
        """, (tid, tid))
    
    db.commit()
    cursor.close()
    db.close()
    
    return jsonify({'id': word_id, 'message': '添加成功'})

@app.route('/api/admin/textbooks', methods=['POST'])
@admin_required
def add_textbook():
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO word_textbooks (name, description)
        VALUES (%s, %s)
    """, (data.get('name'), data.get('description')))
    db.commit()
    
    textbook_id = cursor.lastrowid
    cursor.close()
    db.close()
    
    return jsonify({'id': textbook_id, 'message': '添加成功'})

@app.route('/api/admin/grammar', methods=['POST'])
@admin_required
def add_grammar():
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO grammar_content (title, content, category, sort_order)
        VALUES (%s, %s, %s, %s)
    """, (
        data.get('title'),
        data.get('content'),
        data.get('category'),
        data.get('sort_order', 0)
    ))
    db.commit()
    
    content_id = cursor.lastrowid
    cursor.close()
    db.close()
    
    return jsonify({'id': content_id, 'message': '添加成功'})

@app.route('/api/admin/questions', methods=['POST'])
@admin_required
def add_question():
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO grammar_questions (content_id, question, options, answer, question_type)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data.get('content_id'),
        data.get('question'),
        data.get('options'),
        data.get('answer'),
        data.get('question_type')
    ))
    db.commit()
    
    question_id = cursor.lastrowid
    cursor.close()
    db.close()
    
    return jsonify({'id': question_id, 'message': '添加成功'})

# ============ 语法内容 ============

@app.route('/api/grammar', methods=['GET'])
def get_grammar_list():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, title, category, sort_order FROM grammar_content ORDER BY sort_order, id")
    content = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(content)

@app.route('/api/grammar/<int:id>', methods=['GET'])
@token_required
def get_grammar_content(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grammar_content WHERE id = %s", (id,))
    content = cursor.fetchone()
    cursor.close()
    db.close()
    return jsonify(content or {})

@app.route('/api/grammar/<int:content_id>/pages', methods=['GET'])
@token_required
def get_grammar_pages(content_id):
    """获取语法内容分页"""
    import re
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grammar_content WHERE id = %s", (content_id,))
    content = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not content:
        return jsonify({'pages': [], 'total': 0})
    
    html = content.get('content', '')
    
    # 按h1/h2/h3标签分割内容为页面
    # 保留标题和其后面的内容作为一个页面
    sections = re.split(r'(?=<h[123])', html)
    
    # 过滤掉空白页面和只有标签没有实际内容的页面
    def has_real_content(page):
        # 必须同时有标题和段落内容才算有效页面
        has_heading = bool(re.search(r'<h[123][^>]*>.*?</h[123]>', page))
        has_paragraph = bool(re.search(r'<p[^>]*>.*?</p>', page))
        return has_heading and has_paragraph
    
    pages = [s.strip() for s in sections if s.strip() and has_real_content(s)]
    
    return jsonify({
        'pages': pages,
        'total': len(pages)
    })

@app.route('/api/grammar/<int:content_id>/progress', methods=['GET', 'POST'])
@token_required
def grammar_progress(content_id):
    """获取或保存阅读进度"""
    if request.method == 'GET':
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT page_index FROM grammar_reading_progress 
            WHERE user_id = %s AND content_id = %s
        """, (g.user_id, content_id))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify({'page_index': result['page_index'] if result else 0})
    else:
        data = request.get_json()
        page_index = data.get('page_index', 0)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO grammar_reading_progress (user_id, content_id, page_index)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE page_index = %s
        """, (g.user_id, content_id, page_index, page_index))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True})

@app.route('/api/grammar/<int:content_id>/questions', methods=['GET'])
@token_required
def get_grammar_questions(content_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grammar_questions WHERE content_id = %s", (content_id,))
    questions = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(questions)

# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=False)
