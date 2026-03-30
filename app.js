const API = '/api';

// 解析单词JSON为简单对象
function parseWordJson(jsonStr) {
    try {
        const data = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
        const content = data.content || {};
        const word = content.word || {};
        const wordContent = word.content || {};
        
        // 提取翻译
        const trans = wordContent.trans || [];
        let meaning = '';
        let meaning_en = '';
        for (const t of trans) {
            if (t.tranCn && !meaning) {
                meaning = (t.pos ? t.pos + ' ' : '') + t.tranCn;
            }
            if (t.tranOther && !meaning_en) {
                meaning_en = t.tranOther;
            }
        }
        // 收集所有词性的意思
        const meanings = [];
        for (const t of trans) {
            if (t.tranCn) {
                meanings.push((t.pos ? t.pos + ' ' : '') + t.tranCn);
            }
        }
        if (meanings.length > 0) meaning = meanings.join('；');
        
        // 提取例句（多个）
        const examples = [];
        const sentence = wordContent.sentence;
        if (sentence && sentence.sentences) {
            for (const s of sentence.sentences) {
                if (s.sContent) {
                    examples.push({ en: s.sContent || '', cn: s.sCn || '' });
                }
            }
        }
        
        // 提取短语（多个）
        const phrases = [];
        const phrase = wordContent.phrase;
        if (phrase && phrase.phrases) {
            for (const p of phrase.phrases) {
                phrases.push({ en: p.pContent || '', cn: p.pCn || '' });
            }
        }
        
        // 提取同义词/近义词（多个）
        const synos = [];
        const syno = wordContent.syno;
        if (syno && syno.synos) {
            for (const s of syno.synos) {
                const words = s.hwds ? s.hwds.map(h => h.w) : [];
                synos.push({ pos: s.pos || '', tran: s.tran || '', words: words });
            }
        }
        
        // 提取相关测试题
        const exams = [];
        const exam = wordContent.exam;
        if (exam) {
            for (const e of exam) {
                const choices = [];
                if (e.choices) {
                    for (const c of e.choices) {
                        choices.push({ choiceIndex: c.choiceIndex, choice: c.choice || '' });
                    }
                }
                exams.push({
                    question: e.question || '',
                    answer: e.answer ? {
                        explain: e.answer.explain || '',
                        rightIndex: e.answer.rightIndex
                    } : null,
                    examType: e.examType,
                    choices: choices
                });
            }
        }
        
        return {
            word: data.headWord || word.wordHead || '',
            phonetic: wordContent.usphone || wordContent.ukphone || '',
            meaning: meaning,
            meaning_en: meaning_en,
            // 额外信息
            usphone: wordContent.usphone || '',
            ukphone: wordContent.ukphone || '',
            // 例句（多个）
            examples: examples,
            // 短语（多个）
            phrases: phrases,
            // 同义词（多个）
            synos: synos,
            // 测试题（多个）
            exams: exams,
            // 原始JSON
            raw: data
        };
    } catch (e) {
        console.error('解析单词JSON失败:', e);
        return null;
    }
}
        let token = localStorage.getItem('english_token');
        let user = null;
        let textbooks = [];
        let currentTextbookId = null;
        let words = [];
        let currentWordIndex = 0;
        let currentWord = null;
        let sessionWordCount = 0;  // 本轮已学数量
        let quizWords = [];
        let quizIndex = 0;
        let quizMode = 'normal';
        let quizHasWrongAttempt = false;  // 当前单词是否有过错误选择
        let isPlaying = false;
        let playTimeout = null;
        let wrongWords = [];
        let grammarList = [];
        
        // 错题缓存
        let wrongWordsCache = { textbookId: null, data: null, timestamp: 0 };
        const WRONG_CACHE_MAX_AGE = 2 * 60 * 1000;  // 错题缓存2分钟
        
        // Auth
        let isLogin = true;
        
        function toggleAuth() {
            isLogin = !isLogin;
            document.getElementById('authTitle').textContent = isLogin ? '登录' : '注册';
            document.getElementById('authSubmit').textContent = isLogin ? '登录' : '注册';
        }
        
        async function handleAuth() {
            console.log('handleAuth called');
            const username = document.getElementById('authUsername').value.trim();
            const password = document.getElementById('authPassword').value;
            console.log('username:', username, 'password:', password ? '***' : 'empty');
            
            if (!username || !password) {
                showToast('请输入用户名和密码');
                return;
            }
            
            const url = isLogin ? `${API}/auth/login` : `${API}/auth/register`;
            
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                
                if (data.error) {
                    showToast(data.error);
                    return;
                }
                
                token = data.token;
                user = data.user;
                localStorage.setItem('english_token', token);
                showApp();
            } catch (e) {
                showToast('网络错误');
            }
        }
        
        function updateWordCount(count) {
            document.getElementById('wordCount').textContent = count;
        }
        
        function logout() {
            closeSettings();
            token = null;
            user = null;
            localStorage.removeItem('english_token');
            document.getElementById('authScreen').style.display = 'flex';
            document.getElementById('app').classList.remove('active');
        }
        
        function openSettings() {
            const modal = document.getElementById('settingsModal');
            const theme = localStorage.getItem('theme') || 'dark';
            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.theme === theme);
            });
            if (user) {
                document.getElementById('settingsUsername').textContent = user.username;
            }
            modal.classList.add('show');
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('show');
        }
        
        function switchTheme(theme) {
            localStorage.setItem('theme', theme);
            applyTheme(theme);
            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.theme === theme);
            });
        }
        
        function applyTheme(theme) {
            if (theme === 'auto') {
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                theme = prefersDark ? 'dark' : 'light';
            }
            document.documentElement.setAttribute('data-theme', theme);
        }
        
        function initTheme() {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            applyTheme(savedTheme);
        }
        
        function showApp() {
            document.getElementById('authScreen').style.display = 'none';
            document.getElementById('app').classList.add('active');
            document.getElementById('userInitial').textContent = user.username[0].toUpperCase();
            initTheme();
            initApp();
        }
        
        async function initApp() {
            await loadTextbooks();
            // loadTextbooks() 已经会调用 fetchNextWord()，不需要重复调用
            loadGrammar();
        }
        
        async function loadTextbooks() {
            try {
                const res = await fetch(`${API}/textbooks`);
                textbooks = await res.json();
                const select = document.getElementById('textbookSelect');
                select.innerHTML = '<option value="">选择课本</option>' + 
                    textbooks.map(t => `<option value="${t.id}">${t.name} (${t.word_count || 0})</option>`).join('');
                
                // 背单词的课本选择器
                const quizSelect = document.getElementById('quizTextbookSelect');
                if (quizSelect) {
                    quizSelect.innerHTML = '<option value="">选择课本</option>' + 
                        textbooks.map(t => `<option value="${t.id}">${t.name} (${t.word_count || 0})</option>`).join('');
                }
                
                // 从服务器获取保存的单词本ID
                let savedTextbookId = null;
                try {
                    const settingsRes = await fetch(`${API}/user/settings`, {
                        headers: {'Authorization': `Bearer ${token}`}
                    });
                    if (settingsRes.ok) {
                        const settings = await settingsRes.json();
                        savedTextbookId = settings.lastTextbookId;
                    }
                } catch (e) {
                    console.error('获取设置失败', e);
                }
                
                // 默认选中保存的单词本，如果没有则选第一个
                if (textbooks.length > 0) {
                    const targetId = textbooks.find(t => t.id == savedTextbookId) ? savedTextbookId : textbooks[0].id;
                    document.getElementById('textbookSelect').value = targetId;
                    currentTextbookId = targetId;
                    // 同步到背单词选择器
                    const quizSelect = document.getElementById('quizTextbookSelect');
                    if (quizSelect) {
                        quizSelect.value = targetId;
                    }
                    // 获取单词（会更新右上角待学数量）
                    await fetchNextWord();
                }
            } catch (e) {
                console.error(e);
            }
        }
        
        async function loadQuizTextbook() {
            const quizTextbookId = document.getElementById('quizTextbookSelect').value;
            if (!quizTextbookId) return;
            
            currentTextbookId = quizTextbookId;
            quizWords = [];
            quizIndex = 0;
            loadQuizWords();
        }
        
        async function loadTextbook() {
            currentTextbookId = document.getElementById('textbookSelect').value;
            if (!currentTextbookId) return;
            
            // 保存选择到服务器
            try {
                await fetch(`${API}/user/settings`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({lastTextbookId: currentTextbookId})
                });
            } catch (e) {
                console.error('保存设置失败', e);
            }
            
            // 检查当前在哪个tab
            const isQuizTab = document.getElementById('tab-quiz').classList.contains('active');
            
            // 同步到背单词选择器
            const quizSelect = document.getElementById('quizTextbookSelect');
            if (quizSelect) {
                quizSelect.value = currentTextbookId;
            }
            
            if (isQuizTab) {
                // 在背单词tab，加载背单词内容
                await loadQuizWords();
            } else {
                // 在学单词tab，获取新单词
                await fetchNextWord();
            }
        }
        
        async function fetchNextWord() {
            try {
                const res = await fetch(`${API}/words/random?textbook_id=${currentTextbookId}`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const data = await res.json();
                if (data.word && data.word.id) {
                    currentWord = data.word;
                    updateWordCount(data.min_word_count);  // 只显示待学单词数
                    showWord(data.word);
                }
            } catch (e) {
                console.error(e);
            }
        }
        
        function showWord(word) {
            // 如果有word_json，用parseWordJson解析
            if (word.word_json) {
                const parsed = parseWordJson(word.word_json);
                if (parsed) {
                    word = { ...word, ...parsed };
                }
            }
            currentWord = word;
            document.getElementById('wordText').textContent = word.word || '';
            document.getElementById('wordPhonetic').textContent = word.phonetic ? `/${word.phonetic}/` : '';
            document.getElementById('wordMeaning').textContent = word.meaning || '';
            // 例句显示英文（只取第一个）
            const example = word.examples && word.examples.length > 0 ? word.examples[0] : null;
            document.getElementById('wordExample').textContent = example ? (example.en || '') : '';
            document.getElementById('wordExampleTrans').textContent = example ? (example.cn || '') : '';
            // 显示后自动播放
            setTimeout(() => autoPlay(), 300);
        }
        
        function playWord() {
            if (!currentWord) return;
            playPronunciation(currentWord.word, 'us');
        }
        
        // 检测是否为中文
        function isChinese(text) {
            return /[\u4e00-\u9fa5]/.test(text);
        }
        
        // 只读单词，不读词性
        function speakWordOnly(text) {
            speechSynthesis.cancel();
            const utt = new SpeechSynthesisUtterance(text);
            utt.lang = 'en-US';
            utt.rate = 0.8;
            speechSynthesis.speak(utt);
        }
        
        // 通用speak函数，过滤词性标记，自动检测语言
        function speak(text) {
            if (!text) return;
            // 过滤掉词性标记如 adj., v., n., adv. 等
            const cleaned = text.replace(/\b(adj|adv|v\.?|n\.?|adj\.?|adv\.?|conj\.?|prep\.?|pron\.?|int\.?|aux\.?|modal\.?|det\.?)\b/gi, '').trim();
            const utt = new SpeechSynthesisUtterance(cleaned || text);
            // 自动检测语言：中文用zh-CN，英文用en-US
            utt.lang = isChinese(cleaned || text) ? 'zh-CN' : 'en-US';
            utt.rate = 0.8;
            speechSynthesis.speak(utt);
        }
        
        function togglePlay() {
            if (isPlaying) {
                // 如果正在播放，点击直接停止
                speechSynthesis.cancel();
                isPlaying = false;
                clearTimeout(playTimeout);
            } else {
                // 如果没在播放，点击从头开始播放
                autoPlay();
            }
        }
        
        function autoPlay() {
            if (!currentWord) return;
            
            // 如果有word_json，用parseWordJson解析
            let word = currentWord;
            if (currentWord.word_json) {
                const parsed = parseWordJson(currentWord.word_json);
                if (parsed) {
                    word = { ...currentWord, ...parsed };
                }
            }
            
            // 获取第一个例句
            const firstExample = (word.examples && word.examples.length > 0) ? word.examples[0].en : '';
            
            clearTimeout(playTimeout);  // 清除之前排队的播放
            speechSynthesis.cancel();
            isPlaying = true;
            let step = 0;
            const steps = [
                () => speakWordOnly(word.word || ''),
                () => { step = 1; speak(word.meaning || ''); },
                () => { step = 2; speak(firstExample); },
                () => { isPlaying = false; }
            ];
            
            function run() {
                if (!isPlaying || step >= steps.length) {
                    isPlaying = false;
                    return;
                }
                steps[step]();
                step++;
                playTimeout = setTimeout(run, 2000);
            }
            run();
        }
        
        function nextWord() {
            if (isTransitioning) return;
            isTransitioning = true;
            // 向上滑或点击下一步时，获取下一个最低播放次数的单词
            fetchNextWord().finally(() => {
                setTimeout(() => isTransitioning = false, 300);
            });
        }
        
        // prevWord不再需要，因为是随机均频播放
        function prevWord() {
            // 均频播放不支持后退，保持空实现
        }
        
        // Swipe handling
        let touchStartY = 0;
        let touchStartX = 0;
        let touchHandled = false;  // 防止touch和click重复触发
        let isTransitioning = false;  // 防止nextWord重复调用
        
        document.addEventListener('touchstart', e => {
            touchStartY = e.touches[0].clientY;
            touchStartX = e.touches[0].clientX;
        });
        
        document.addEventListener('touchend', e => {
            // 只在学单词标签页响应滑动事件
            if (!document.getElementById('tab-learn').classList.contains('active')) {
                return;
            }
            
            const deltaY = e.changedTouches[0].clientY - touchStartY;
            const deltaX = e.changedTouches[0].clientX - touchStartX;
            
            // 如果详情页已打开，右滑关闭，上下左右都不触发其他操作
            const wordDetailModal = document.getElementById('wordDetailModal');
            if (wordDetailModal.classList.contains('show')) {
                if (deltaX > 85 && Math.abs(deltaX) > Math.abs(deltaY)) {
                    closeWordDetail();
                }
                return;
            }
            
            if (Math.abs(deltaY) > 50 && Math.abs(deltaY) > Math.abs(deltaX)) {
                // 上下滑动都获取新单词
                nextWord();
            } else if (deltaX < -100 && Math.abs(deltaX) > Math.abs(deltaY)) {
                openWordDetail();
            }
        });
        
        // Word card touch handlers for direct swipe detection
        function wordCardTouchStart(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }
        
        function wordCardTouchMove(e) {
            // Prevent scrolling when swiping horizontally
            const deltaX = e.touches[0].clientX - touchStartX;
            if (Math.abs(deltaX) > Math.abs(e.touches[0].clientY - touchStartY)) {
                e.preventDefault();
            }
        }
        
        function wordCardTouchEnd(e) {
            // 如果有模态框打开，不处理触摸事件
            const wordDetailModal = document.getElementById('wordDetailModal');
            const settingsModal = document.getElementById('settingsModal');
            if (wordDetailModal.classList.contains('show') || settingsModal.classList.contains('show')) {
                return;
            }
            
            if (touchHandled) return;
            touchHandled = true;
            setTimeout(() => touchHandled = false, 100);
            
            const deltaX = e.changedTouches[0].clientX - touchStartX;
            const deltaY = e.changedTouches[0].clientY - touchStartY;
            
            // Left swipe - open word detail
            if (deltaX < -80 && Math.abs(deltaX) > Math.abs(deltaY)) {
                openWordDetail();
            }
            // Right swipe - next word
            else if (deltaX > 80 && Math.abs(deltaX) > Math.abs(deltaY)) {
                nextWord();
            }
            // Up or down swipe - next word
            else if (Math.abs(deltaY) > 50 && Math.abs(deltaY) > Math.abs(deltaX)) {
                nextWord();
            }
        }
        
        // PC鼠标滑动支持
        let mouseDown = false;
        let mouseStartX = 0;
        let mouseStartY = 0;
        let mouseDragged = false;  // 标记是否拖拽过
        
        const wordCard = document.getElementById('wordCard');
        if (wordCard) {
            wordCard.addEventListener('mousedown', e => {
                mouseDown = true;
                mouseDragged = false;
                mouseStartX = e.clientX;
                mouseStartY = e.clientY;
            });
            
            wordCard.addEventListener('mousemove', e => {
                if (!mouseDown) return;
                const deltaX = e.clientX - mouseStartX;
                const deltaY = e.clientY - mouseStartY;
                // 如果移动超过10px，认为是拖拽
                if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
                    mouseDragged = true;
                }
            });
            
            wordCard.addEventListener('mouseup', e => {
                if (!mouseDown) return;
                mouseDown = false;
                
                // 如果有模态框打开，不处理
                const wordDetailModal = document.getElementById('wordDetailModal');
                const settingsModal = document.getElementById('settingsModal');
                if (wordDetailModal.classList.contains('show') || settingsModal.classList.contains('show')) {
                    return;
                }
                
                const deltaX = e.clientX - mouseStartX;
                const deltaY = e.clientY - mouseStartY;
                
                // Left swipe - open word detail
                if (deltaX < -80 && Math.abs(deltaX) > Math.abs(deltaY)) {
                    openWordDetail();
                    mouseDragged = true;
                }
                // Right swipe - next word
                else if (deltaX > 80 && Math.abs(deltaX) > Math.abs(deltaY)) {
                    nextWord();
                    mouseDragged = true;
                }
                // Up or down swipe - next word
                else if (Math.abs(deltaY) > 50 && Math.abs(deltaY) > Math.abs(deltaX)) {
                    nextWord();
                    mouseDragged = true;
                }
            });
            
            wordCard.addEventListener('mouseleave', e => {
                mouseDown = false;
            });
            
            // 处理点击事件（只有非拖拽时才触发）
            wordCard.addEventListener('click', e => {
                if (mouseDragged) {
                    e.stopPropagation();
                    mouseDragged = false;
                    return;
                }
                // 如果有模态框打开，不处理
                const wordDetailModal = document.getElementById('wordDetailModal');
                const settingsModal = document.getElementById('settingsModal');
                if (wordDetailModal.classList.contains('show') || settingsModal.classList.contains('show')) {
                    return;
                }
                togglePlay();
            });
        }
        
        function openWordDetail() {
            if (!currentWord) return;
            
            // 如果有word_json，用parseWordJson解析
            let word = currentWord;
            if (currentWord.word_json) {
                const parsed = parseWordJson(currentWord.word_json);
                if (parsed) {
                    word = { ...currentWord, ...parsed };
                }
            }
            
            let html = '';
            
            // 1. 单词
            html += `<div class="word-detail-word">${word.word || ''}</div>`;
            
            // 2. 音标（美音+英音）
            let phoneticHtml = '';
            if (word.usphone) phoneticHtml += `<span class="phonetic-item" onclick="playPronunciation('${word.word}', 'us')">美 /${word.usphone}/</span>`;
            if (word.ukphone) phoneticHtml += `<span class="phonetic-item" onclick="playPronunciation('${word.word}', 'uk')">英 /${word.ukphone}/</span>`;
            if (phoneticHtml) html += `<div class="word-detail-phonetics">${phoneticHtml}</div>`;
            
            // 3. 图片
            if (word.picture) {
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">图片</div>
                    <div class="word-detail-picture"><img src="${word.picture}" alt="单词图片" onerror="this.style.display='none'"></div>
                </div>`;
            }
            
            // 4. 中文含义
            if (word.meaning) {
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">中文含义</div>
                    <div class="word-detail-value">${word.meaning}</div>
                </div>`;
            }
            
            // 5. 记忆法
            if (word.remMethod) {
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">记忆法</div>
                    <div class="word-detail-value">${word.remMethod}</div>
                </div>`;
            }
            
            // 6. 英文含义
            if (word.meaning_en) {
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">英文含义</div>
                    <div class="word-detail-value">${word.meaning_en}</div>
                </div>`;
            }
            
            // 7. 例句（多个）
            if (word.examples && word.examples.length > 0) {
                let examplesHtml = '';
                for (const ex of word.examples) {
                    examplesHtml += `<div class="example-item">
                        <div class="example-en">${ex.en}</div>
                        <div class="example-cn">${ex.cn}</div>
                    </div>`;
                }
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">例句</div>
                    <div class="word-detail-examples">${examplesHtml}</div>
                </div>`;
            }
            
            // 8. 同根词（多个）
            if (word.relWords && word.relWords.length > 0) {
                let relWordsHtml = '';
                for (const r of word.relWords) {
                    relWordsHtml += `<span class="relword-item">${r.word} ${r.pos} ${r.tran}</span>`;
                }
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">同根词</div>
                    <div class="word-detail-relwords">${relWordsHtml}</div>
                </div>`;
            }
            
            // 9. 相关短语（多个）
            if (word.phrases && word.phrases.length > 0) {
                let phrasesHtml = '';
                for (const p of word.phrases) {
                    phrasesHtml += `<div class="phrase-item">
                        <span class="phrase-en">${p.en}</span>
                        <span class="phrase-cn">${p.cn}</span>
                    </div>`;
                }
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">相关短语</div>
                    <div class="word-detail-phrases">${phrasesHtml}</div>
                </div>`;
            }
            
            // 10. 近义词（多个）
            if (word.synonyms && word.synonyms.length > 0) {
                let synosHtml = '';
                for (const s of word.synonyms) {
                    const pos = s.pos ? `<span class="syn-pos">${s.pos}</span>` : '';
                    const tran = s.tran ? `<span class="syn-tran">${s.tran}</span>` : '';
                    synosHtml += `<span class="synonym-item">${s.word}${pos}${tran}</span>`;
                }
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">近义词</div>
                    <div class="word-detail-synonyms">${synosHtml}</div>
                </div>`;
            }
            
            // 11. 相关测试题
            if (word.exams && word.exams.length > 0) {
                let examsHtml = '';
                for (const e of word.exams) {
                    let choicesHtml = '';
                    if (e.choices && e.choices.length > 0) {
                        for (const c of e.choices) {
                            const isRight = c.choiceIndex === e.answer?.rightIndex;
                            const style = isRight ? 'style="color:#4CAF50;font-weight:bold"' : '';
                            choicesHtml += `<div class="choice-item" ${style}>${c.choiceIndex}. ${c.choice}</div>`;
                        }
                    }
                    const explainText = e.answer?.explain || '';
                    examsHtml += `<div class="exam-item">
                        <div class="exam-question">${e.question || ''}</div>
                        <div class="exam-choices">${choicesHtml}</div>
                        ${explainText ? `<div class="exam-answer">答案解析：${explainText}</div>` : ''}
                    </div>`;
                }
                html += `<div class="word-detail-section">
                    <div class="word-detail-label">相关测试题</div>
                    <div class="word-detail-exams">${examsHtml}</div>
                </div>`;
            }
            
            document.getElementById('detailContent').innerHTML = html;
            document.getElementById('wordDetailModal').classList.add('show');
            
            // 详情页触摸滑动关闭
            const modal = document.getElementById('wordDetailModal');
            const modalContent = modal.querySelector('.word-detail-container');
            let modalTouchStartX = 0;
            let modalTouchStartY = 0;
            
            modalContent.ontouchstart = function(e) {
                modalTouchStartX = e.touches[0].clientX;
                modalTouchStartY = e.touches[0].clientY;
            };
            modalContent.ontouchend = function(e) {
                const deltaX = e.changedTouches[0].clientX - modalTouchStartX;
                const deltaY = e.changedTouches[0].clientY - modalTouchStartY;
                if (deltaX > 85 && deltaX > deltaY) {
                    closeWordDetail();
                }
            };
        }
        
        // 播放发音（优先有道API，失败则用浏览器TTS）
        function playPronunciation(word, type) {
            const audio = new Audio();
            audio.src = `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=${type === 'us' ? 2 : 1}`;
            audio.play().catch(e => {
                // 有道失败，备用浏览器TTS
                speechSynthesis.cancel();
                const utt = new SpeechSynthesisUtterance(word);
                utt.lang = type === 'us' ? 'en-US' : 'en-GB';
                utt.rate = 0.8;
                speechSynthesis.speak(utt);
            });
        }
        
        function closeWordDetail() {
            document.getElementById('wordDetailModal').classList.remove('show');
        }
        
        // Quiz
        function switchQuizTab(mode, btn) {
            quizMode = mode;
            document.querySelectorAll('.quiz-tab').forEach(t => {
                t.classList.remove('active');
                t.style.background = 'var(--surface)';
                t.style.borderColor = 'var(--border)';
                t.style.color = 'var(--text-secondary)';
            });
            btn.classList.add('active');
            btn.style.background = 'var(--primary)';
            btn.style.borderColor = 'var(--primary)';
            btn.style.color = 'white';
            
            if (mode === 'normal') {
                loadQuizWords();
            } else {
                loadWrongWords();
            }
        }
        
        // 背单词状态
        let quizMinCountWordCount = 0;  // 背诵次数最小的单词数量
        let quizCurrentWord = null;  // 当前背的单词
        let quizCurrentIndex = 0;  // 当前单词索引
        let quizWrongWordCount = 0;  // 剩余错题数量
        let quizRecordedWrongOptions = new Set();  // 已记录过的错误选项
        
        async function loadQuizWords() {
            if (!currentTextbookId) {
                document.getElementById('quizWord').textContent = '请先选择课本';
                document.getElementById('quizOptions').innerHTML = '';
                return;
            }
            
            try {
                const res = await fetch(`${API}/textbooks/${currentTextbookId}/quiz-words`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const data = await res.json();
                
                if (data.word) {
                    quizCurrentWord = data.word;
                    quizMinCountWordCount = data.min_quiz_word_count || 0;
                    updateWordCount(quizMinCountWordCount);
                    showQuizWord();
                } else {
                    document.getElementById('quizWord').textContent = '恭喜！所有单词已背完';
                    document.getElementById('quizOptions').innerHTML = '';
                    updateWordCount(0);
                }
            } catch (e) {
                console.error('加载单词失败:', e);
            }
        }
        
        async function loadWrongWords() {
            if (!currentTextbookId) {
                document.getElementById('quizWord').textContent = '请先选择课本';
                return;
            }
            
            try {
                const res = await fetch(`${API}/textbooks/${currentTextbookId}/wrong-word`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const data = await res.json();
                
                if (data.word) {
                    quizCurrentWord = data.word;
                    quizWrongWordCount = data.wrong_word_count || 0;
                    updateWordCount(quizWrongWordCount);
                    showQuizWord();
                } else {
                    document.getElementById('quizWord').textContent = '恭喜！错题已复习完';
                    document.getElementById('quizOptions').innerHTML = '';
                    updateWordCount(0);
                }
            } catch (e) {
                console.error('加载错题失败:', e);
            }
        }
        
        function showQuizWord() {
            if (!quizCurrentWord) {
                document.getElementById('quizWord').textContent = '请先学习一些单词再来背';
                document.getElementById('quizOptions').innerHTML = '';
                return;
            }
            
            // 重置错误选项记录
            quizRecordedWrongOptions.clear();
            
            const quizWord = quizCurrentWord;
            // 如果有word_json，用parseWordJson解析
            let word = quizWord;
            if (quizWord.word_json) {
                const parsed = parseWordJson(quizWord.word_json);
                if (parsed) {
                    word = { ...quizWord, ...parsed };
                }
            }
            
            document.getElementById('quizWord').textContent = word.word || '';
            
            // 使用后端预生成的选项（1个正确+3个错误）
            const options = word.options || [word.meaning];
            document.getElementById('quizOptions').innerHTML = options.map((opt, i) => 
                `<div class="quiz-option" onclick="selectOption(this, ${i}, ${JSON.stringify(opt).replace(/"/g, '&quot;')})">${opt}</div>`
            ).join('');
            
            // Auto play
            setTimeout(() => speak(word.word || ''), 500);
            
            // 更新右上角剩余数量
            if (quizMode === 'wrong') {
                updateWordCount(quizWrongWordCount);
            } else {
                updateWordCount(quizMinCountWordCount);
            }
        }
        
        function playQuizWord() {
            if (quizCurrentWord) {
                speak(quizCurrentWord.word);
            }
        }
        
        async function selectOption(el, idx, text) {
            const correct = quizCurrentWord.meaning;
            const options = document.querySelectorAll('.quiz-option');
            
            if (text === correct) {
                // 正确
                el.classList.add('correct');
                options.forEach(o => o.style.pointerEvents = 'none');
                
                if (quizMode === 'wrong') {
                    // 错题复习模式：记录答对，然后加载下一条
                    try {
                        await fetch(`${API}/words/${quizCurrentWord.id}/wrong-review-correct`, {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({textbook_id: currentTextbookId})
                        });
                    } catch (e) {}
                    
                    // 答对后加载下一题
                    setTimeout(() => {
                        loadWrongWords();
                    }, 800);
                } else {
                    // 普通背单词模式：记录背诵次数
                    try {
                        await fetch(`${API}/words/${quizCurrentWord.id}/quiz-correct`, {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({textbook_id: currentTextbookId})
                        });
                    } catch (e) {}
                    
                    // 答对后延迟加载下一个单词
                    setTimeout(() => {
                        loadQuizWords();
                    }, 800);
                }
            } else {
                // 错误
                el.classList.add('wrong');
                
                // 只记录一次同一个错误选项
                if (!quizRecordedWrongOptions.has(text)) {
                    quizRecordedWrongOptions.add(text);
                    try {
                        await fetch(`${API}/words/${quizCurrentWord.id}/wrong`, {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({textbook_id: currentTextbookId})
                        });
                    } catch (e) {}
                }
                
                // 0.5秒后取消红色，允许重新选择
                setTimeout(() => {
                    el.classList.remove('wrong');
                }, 500);
            }
        }
        
        // Grammar
        let grammarTocVisible = false;
        let grammarTouchStartX = 0;
        let grammarTouchStartY = 0;
        let grammarTouchEndX = 0;
        let grammarTouchEndY = 0;
        let currentGrammarIndex = 0;
        let currentPageIndex = 0;
        let currentPages = [];
        let isScrollingToc = false;

        async function loadGrammar() {
            try {
                const res = await fetch(`${API}/grammar`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                grammarList = await res.json();
                
                // 生成完整目录
                const tocList = document.getElementById('grammarTocList');
                tocList.innerHTML = grammarList.map((g, i) => 
                    `<div class="grammar-toc-item" data-index="${i}">${g.title}</div>`
                ).join('');
                
                // 添加点击事件
                document.querySelectorAll('.grammar-toc-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const idx = parseInt(item.dataset.index);
                        selectGrammar(idx);
                    });
                });
                
                // 默认选中上次阅读的章节，或第一章
                let lastContentId = localStorage.getItem('lastGrammarContentId');
                let defaultIndex = 0;
                if (lastContentId) {
                    defaultIndex = grammarList.findIndex(g => g.id == lastContentId);
                    if (defaultIndex < 0) defaultIndex = 0;
                }
                if (grammarList.length > 0) {
                    await selectGrammar(defaultIndex);
                } else {
                    document.getElementById('grammarPage').innerHTML = '<p style="text-align:center;color:var(--text-secondary)">暂无语法内容</p>';
                }
                
            } catch (e) {
                console.error(e);
            }
        }
        
        function toggleGrammarToc() {
            grammarTocVisible = !grammarTocVisible;
            document.getElementById('grammarTocOverlay').classList.toggle('active', grammarTocVisible);
            document.getElementById('grammarTocPanel').classList.toggle('active', grammarTocVisible);
        }
        
        async function selectGrammar(index, fromSwipe = null) {
            currentGrammarIndex = index;
            currentPageIndex = 0;
            
            // 关闭目录面板
            grammarTocVisible = false;
            document.getElementById('grammarTocOverlay').classList.remove('active');
            document.getElementById('grammarTocPanel').classList.remove('active');
            
            // 保存当前阅读的语法内容ID
            const item = grammarList[index];
            if (item) {
                localStorage.setItem('lastGrammarContentId', item.id);
            }
            
            try {
                // 获取分页内容
                const res = await fetch(`${API}/grammar/${item.id}/pages`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const data = await res.json();
                currentPages = data.pages || [];
                
                // 加载阅读进度
                const progressRes = await fetch(`${API}/grammar/${item.id}/progress`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                const progressData = await progressRes.json();
                currentPageIndex = Math.min(progressData.page_index || 0, currentPages.length - 1);
                
                // 更新标题
                document.getElementById('grammarTitle').textContent = item.title;
                
                // 渲染页面
                renderGrammarPages();
                
                // 跨章节滑动时：直接跳到目标页（无动画，避免眩晕）
                if (fromSwipe) {
                    goToGrammarPage(currentPageIndex, false); // false = 无动画
                } else {
                    // 从目录选择，正常跳转
                    goToGrammarPage(currentPageIndex);
                }
                
                // 更新目录选中状态
                document.querySelectorAll('.grammar-toc-item').forEach((item, i) => {
                    item.classList.toggle('selected', i === index);
                });
                
            } catch (e) {
                console.error(e);
            }
            
        }
        
        function renderGrammarPages() {
            const pagesContainer = document.getElementById('grammarPages');
            const pagesCount = currentPages.length;
            
            // 生成所有页面
            pagesContainer.innerHTML = currentPages.map((page, i) => 
                `<div class="grammar-page">${page}</div>`
            ).join('');
            
            // 更新进度显示
            updateGrammarProgress();
        }
        
        function updateGrammarProgress() {
            const pagesCount = currentPages.length;
            const pageInfo = document.getElementById('grammarPageInfo');
            
            pageInfo.textContent = pagesCount > 0 ? `${currentPageIndex + 1}/${pagesCount}` : '0/0';
        }
        
        async function goToGrammarPage(pageIndex, animate = true) {
            if (pageIndex < 0 || pageIndex >= currentPages.length) return;
            
            currentPageIndex = pageIndex;
            
            // 滑动到指定页面
            const pagesContainer = document.getElementById('grammarPages');
            if (animate) {
                pagesContainer.style.transition = 'transform 0.3s ease';
            } else {
                pagesContainer.style.transition = 'none';
            }
            pagesContainer.style.transform = `translateX(-${pageIndex * 100}%)`;
            
            // 更新进度
            updateGrammarProgress();
            
            // 保存阅读进度
            const item = grammarList[currentGrammarIndex];
            if (item) {
                try {
                    await fetch(`${API}/grammar/${item.id}/progress`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ page_index: pageIndex })
                    });
                } catch (e) {}
            }
        }
        
        function grammarPrevPage() {
            if (currentPageIndex > 0) {
                // 当前章节的前一页
                goToGrammarPage(currentPageIndex - 1);
            } else if (currentGrammarIndex > 0) {
                // 已经当前章节第一页，切换到上一章节的最后一页
                selectGrammar(currentGrammarIndex - 1, 'prev').then(() => {
                    // 跳到上一章节的最后一页
                    if (currentPages.length > 0) {
                        goToGrammarPage(currentPages.length - 1, false); // 无动画
                    }
                });
            }
        }
        
        function grammarNextPage() {
            if (currentPageIndex < currentPages.length - 1) {
                // 当前章节的下一页
                goToGrammarPage(currentPageIndex + 1);
            } else if (currentGrammarIndex < grammarList.length - 1) {
                // 已经当前章节最后一页，切换到下一章节的第一页
                selectGrammar(currentGrammarIndex + 1, 'next').then(() => {
                    goToGrammarPage(0, false); // 无动画
                });
            }
        }
        
        // 触摸滑动处理 - 区分目录滚动和内容翻页
        function grammarTouchStart(e) {
            grammarTouchStartX = e.touches[0].clientX;
            grammarTouchStartY = e.touches[0].clientY;
            isScrollingToc = false;
        }
        
        function grammarTouchMove(e) {
            grammarTouchEndX = e.touches[0].clientX;
            grammarTouchEndY = e.touches[0].clientY;
            
            // 如果水平移动距离大于垂直距离，说明是翻页
            const deltaX = Math.abs(grammarTouchEndX - grammarTouchStartX);
            const deltaY = Math.abs(grammarTouchEndY - grammarTouchStartY);
            
            // 不阻止默认行为，让页面自然滚动
        }
        
        function grammarTouchEnd(e) {
            const deltaX = grammarTouchEndX - grammarTouchStartX;
            const deltaY = grammarTouchEndY - grammarTouchStartY;
            
            // 水平滑动大于垂直滑动 且 滑动距离大于50px
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX < 0) {
                    // 左滑 -> 下一页
                    grammarNextPage();
                } else {
                    // 右滑 -> 上一页
                    grammarPrevPage();
                }
            }
        }

        // Exercise swipe
        let exerciseTouchStartX = 0;
        let exerciseTouchStartY = 0;
        let exerciseTouchEndX = 0;
        let exerciseTouchEndY = 0;
        
        function exerciseTouchStart(e) {
            if (e.touches.length > 0) {
                exerciseTouchStartX = e.touches[0].clientX;
                exerciseTouchStartY = e.touches[0].clientY;
                exerciseTouchEndX = exerciseTouchStartX;
                exerciseTouchEndY = exerciseTouchStartY;
            }
        }
        
        function exerciseTouchMove(e) {
            if (e.touches.length > 0) {
                exerciseTouchEndX = e.touches[0].clientX;
                exerciseTouchEndY = e.touches[0].clientY;
            }
        }
        
        function exerciseTouchEnd(e) {
            const deltaX = exerciseTouchEndX - exerciseTouchStartX;
            const deltaY = exerciseTouchEndY - exerciseTouchStartY;
            
            // 水平滑动 且 滑动距离大于50px
            if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
                if (deltaX < 0) {
                    // 左滑 -> 下一题 (index增加)
                    if (exerciseIndex < exerciseQuestions.length - 1) {
                        exerciseIndex++;
                    } else {
                        // 循环到第一题
                        exerciseIndex = 0;
                    }
                    currentQuestion = exerciseQuestions[exerciseIndex];
                    saveExercisePosition();
                    showQuestion();
                } else {
                    // 右滑 -> 上一题 (index减少)
                    if (exerciseIndex > 0) {
                        exerciseIndex--;
                    } else {
                        // 循环到最后一题
                        exerciseIndex = exerciseQuestions.length - 1;
                    }
                    currentQuestion = exerciseQuestions[exerciseIndex];
                    saveExercisePosition();
                    showQuestion();
                }
            }
            // 重置起始值
            exerciseTouchStartX = 0;
            exerciseTouchStartY = 0;
            exerciseTouchEndX = 0;
            exerciseTouchEndY = 0;
        }

        // 语法页面PC鼠标滑动支持
        const grammarWrapper = document.getElementById('grammarContentWrapper');
        if (grammarWrapper) {
            let gMouseDown = false;
            let gMouseStartX = 0;
            let gMouseStartY = 0;
            
            grammarWrapper.addEventListener('mousedown', e => {
                gMouseDown = true;
                gMouseStartX = e.clientX;
                gMouseStartY = e.clientY;
            });
            
            grammarWrapper.addEventListener('mouseup', e => {
                if (!gMouseDown) return;
                gMouseDown = false;
                
                const deltaX = e.clientX - gMouseStartX;
                const deltaY = e.clientY - gMouseStartY;
                
                if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
                    if (deltaX < 0) {
                        grammarNextPage();
                    } else {
                        grammarPrevPage();
                    }
                }
            });
            
            grammarWrapper.addEventListener('mouseleave', () => {
                gMouseDown = false;
            });
        }
        
        // 练习页面PC鼠标滑动支持
        const exerciseContainer = document.getElementById('exerciseContainer');
        if (exerciseContainer) {
            let eMouseDown = false;
            let eMouseStartX = 0;
            let eMouseStartY = 0;
            
            exerciseContainer.addEventListener('mousedown', e => {
                eMouseDown = true;
                eMouseStartX = e.clientX;
                eMouseStartY = e.clientY;
            });
            
            exerciseContainer.addEventListener('mouseup', e => {
                if (!eMouseDown) return;
                eMouseDown = false;
                
                const deltaX = e.clientX - eMouseStartX;
                const deltaY = e.clientY - eMouseStartY;
                
                if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
                    if (deltaX < 0) {
                        // 左滑 -> 下一题
                        if (exerciseIndex < exerciseQuestions.length - 1) {
                            exerciseIndex++;
                        } else {
                            exerciseIndex = 0;
                        }
                    } else {
                        // 右滑 -> 上一题
                        if (exerciseIndex > 0) {
                            exerciseIndex--;
                        } else {
                            exerciseIndex = exerciseQuestions.length - 1;
                        }
                    }
                    currentQuestion = exerciseQuestions[exerciseIndex];
                    saveExercisePosition();
                    showQuestion();
                }
            });
            
            exerciseContainer.addEventListener('mouseleave', () => {
                eMouseDown = false;
            });
        }

        // Exercise
        let currentQuestion = null;
        let exerciseQuestions = [];
        let exerciseIndex = 0;
        let currentExerciseGrammarId = null; // 记录当前练习的语法ID
        
        async function loadExercise() {
            // 使用当前正在学习的语法章节
            if (grammarList.length === 0 || currentGrammarIndex === -1) {
                document.getElementById('exerciseQuestion').textContent = '请先学习语法内容';
                return;
            }
            
            // 获取当前章节的练习题
            const currentGrammar = grammarList[currentGrammarIndex];
            
            try {
                const res = await fetch(`${API}/grammar/${currentGrammar.id}/questions`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                exerciseQuestions = await res.json();
                
                if (exerciseQuestions.length > 0) {
                    // 如果是同一个语法章节，恢复之前的位置
                    if (currentExerciseGrammarId === currentGrammar.id) {
                        // 保持当前 exerciseIndex
                    } else {
                        // 新章节，从头开始
                        currentExerciseGrammarId = currentGrammar.id;
                        exerciseIndex = 0;
                        // 从localStorage读取保存的位置
                        const saved = localStorage.getItem(`exercise_${currentGrammar.id}`);
                        if (saved !== null) {
                            exerciseIndex = Math.min(parseInt(saved) || 0, exerciseQuestions.length - 1);
                        }
                    }
                    currentQuestion = exerciseQuestions[exerciseIndex];
                    showQuestion();
                } else {
                    document.getElementById('exerciseQuestion').textContent = '本节暂无练习题';
                    document.getElementById('exerciseOptions').innerHTML = '';
                    document.getElementById('exerciseResult').style.display = 'none';
                    document.getElementById('exerciseInfo').textContent = '';
                }
            } catch (e) {
                console.error(e);
                document.getElementById('exerciseQuestion').textContent = '加载失败';
            }
        }
        
        function saveExercisePosition() {
            if (currentExerciseGrammarId && exerciseQuestions.length > 0) {
                localStorage.setItem(`exercise_${currentExerciseGrammarId}`, exerciseIndex.toString());
            }
        }
        
        function nextQuestion() {
            if (exerciseIndex < exerciseQuestions.length - 1) {
                exerciseIndex++;
                currentQuestion = exerciseQuestions[exerciseIndex];
                saveExercisePosition();
                showQuestion();
            } else {
                document.getElementById('exerciseQuestion').textContent = '本节练习已完成！';
                document.getElementById('exerciseOptions').innerHTML = '';
                document.getElementById('exerciseResult').style.display = 'none';
            }
        }
        
        function prevQuestion() {
            if (exerciseIndex > 0) {
                exerciseIndex--;
                currentQuestion = exerciseQuestions[exerciseIndex];
                saveExercisePosition();
                showQuestion();
            } else {
                document.getElementById('exerciseResult').textContent = '已经是第一题了';
                document.getElementById('exerciseResult').style.display = 'block';
                document.getElementById('exerciseResult').className = 'exercise-result wrong';
            }
        }
        
        function showQuestion() {
            selectedOption = null; // 重置选择
            document.getElementById('exerciseQuestion').textContent = currentQuestion.question;
            document.getElementById('exerciseResult').style.display = 'none';
            document.getElementById('exerciseSubmit').style.display = 'block';
            // 更新题号显示
            document.getElementById('exerciseInfo').textContent = `第${exerciseIndex + 1}题/共${exerciseQuestions.length}题`;
            
            if (currentQuestion.question_type === 'choice') {
                const options = currentQuestion.options.split('\n');
                document.getElementById('exerciseOptions').innerHTML = options.map((opt, i) =>
                    `<div class="exercise-option" onclick="selectExerciseOption(this)">${opt}</div>`
                ).join('');
                document.getElementById('exerciseOptions').style.display = 'flex';
                document.getElementById('exerciseInput').style.display = 'none';
            } else {
                document.getElementById('exerciseOptions').style.display = 'none';
                document.getElementById('exerciseInput').style.display = 'block';
                document.getElementById('exerciseInput').value = '';
            }
        }
        
        let selectedOption = null;
        
        function selectExerciseOption(el) {
            document.querySelectorAll('.exercise-option').forEach(o => o.classList.remove('selected'));
            el.classList.add('selected');
            selectedOption = el.textContent;
        }
        
        async function submitExercise() {
            let answer;
            if (currentQuestion.question_type === 'choice') {
                if (!selectedOption) {
                    // 用页面提示代替alert
                    const result = document.getElementById('exerciseResult');
                    result.style.display = 'block';
                    result.className = 'exercise-result wrong';
                    result.innerHTML = '⚠️ 请先选择一个选项';
                    return;
                }
                answer = selectedOption.charAt(0);
            } else {
                answer = document.getElementById('exerciseInput').value;
            }
            
            const isCorrect = answer.trim().toLowerCase() === currentQuestion.answer.trim().toLowerCase();
            
            const result = document.getElementById('exerciseResult');
            result.style.display = 'block';
            result.className = 'exercise-result ' + (isCorrect ? 'correct' : 'wrong');
            result.innerHTML = isCorrect 
                ? '✓ 回答正确！<br><button class="exercise-next-btn" onclick="nextQuestion()">下一题</button>'
                : `✗ 正确答案：${currentQuestion.answer}<br><button class="exercise-next-btn" onclick="nextQuestion()">下一题</button>`;
            
            document.getElementById('exerciseSubmit').style.display = 'none';
        }
        
        // Tab switching
        function switchTab(tab) {
            // 停止当前音频
            speechSynthesis.cancel();
            isPlaying = false;
            
            document.querySelectorAll('.nav-item').forEach((el, i) => {
                el.classList.toggle('active', ['learn', 'quiz', 'grammar', 'exercise'][i] === tab);
            });
            
            document.querySelectorAll('.tab-content').forEach(el => {
                el.classList.remove('active');
            });
            
            const tabId = {
                'learn': 'tab-learn',
                'quiz': 'tab-quiz', 
                'grammar': 'tab-grammar',
                'exercise': 'tab-exercise'
            }[tab];
            document.getElementById(tabId).classList.add('active');
            
            document.getElementById('moduleTitle').textContent = {
                'learn': '学单词',
                'quiz': '背单词',
                'grammar': '学语法',
                'exercise': '语法练习'
            }[tab];
            
            // 显示/隐藏 header-left (课本选择) 和 header-right (单词数量)
            // 只在 学单词和背单词 显示
            const isWordTab = (tab === 'learn' || tab === 'quiz');
            document.querySelector('.header-left').style.display = isWordTab ? 'flex' : 'none';
            document.querySelector('.header-right').style.display = isWordTab ? 'flex' : 'none';
            
            // Init tab
            if (tab === 'learn' && currentTextbookId) {
                fetchNextWord();
            } else if (tab === 'quiz') {
                loadQuizWords();
            } else if (tab === 'grammar') {
                if (grammarList.length === 0) {
                    loadGrammar();
                }
            } else if (tab === 'exercise') {
                if (grammarList.length > 0) {
                    loadExercise();
                } else {
                    loadGrammar().then(() => loadExercise());
                }
            }
        }
        
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }
        
        // Init
        if (token) {
            fetch(`${API}/auth/me`, {
                headers: {'Authorization': `Bearer ${token}`}
            }).then(res => res.json())
              .then(data => {
                  if (data.id) {
                      user = data;
                      showApp();
                  }
              })
              .catch(() => {
                  localStorage.removeItem('english_token');
              });
        }