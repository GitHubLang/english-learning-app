# 英语学习APP

一个基于Web的英语学习应用，支持学单词、背单词、语法练习等功能。

## 功能特性

- **学单词**：浏览和播放单词音频，查看释义和例句
- **背单词**：基于艾宾浩斯遗忘曲线设计的背诵模式
- **语法练习**：选择题形式的语法练习
- **进度跟踪**：自动记录学习进度

## 技术栈

- **后端**：Python Flask + MySQL
- **前端**：原生JavaScript + CSS
- **数据库**：MySQL

## 文件结构

```
├── app.py              # Flask后端主程序
├── app.js              # 前端JavaScript逻辑
├── index.html          # HTML结构
├── styles.css          # CSS样式
├── DATABASE_SCHEMA.md  # 数据库表结构文档
└── REQUIREMENTS.md     # 项目需求文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install flask mysql-connector-python pyjwt bcrypt
```

### 2. 配置数据库

创建数据库 `english_db`，然后导入表结构（参考 DATABASE_SCHEMA.md）

### 3. 启动服务

```bash
python3 app.py
```

服务将在 http://0.0.0.0:8082 启动

### 4. 默认账号

- 用户名：admin
- 密码：admin123

## API接口

### 认证
- POST `/api/auth/register` - 注册
- POST `/api/auth/login` - 登录

### 单词
- GET `/api/textbooks` - 获取课本列表
- GET `/api/textbooks/<id>/words` - 获取课本单词
- POST `/api/textbooks/<id>/play` - 记录播放
- GET `/api/textbooks/<id>/quiz-words` - 获取背单词数据

### 语法
- GET `/api/grammar` - 获取语法章节
- GET `/api/grammar/<id>/questions` - 获取章节练习题
- POST `/api/grammar/<id>/progress` - 更新进度

## word_json字段说明

单词表中的 `word_json` 字段存储词典API返回的完整JSON数据，示例结构：

```json
{
  "content": {
    "word": {
      "content": {
        "trans": [
          {"tranCn": "中文释义", "pos": "词性"}
        ]
      }
    }
  }
}
```

前端通过 `parseWordJson()` 函数解析出：
- word: 单词
- phonetic: 音标
- meaning: 中文释义
- meaning_en: 英文释义
- example_sentence: 例句
- example_translation: 例句翻译
