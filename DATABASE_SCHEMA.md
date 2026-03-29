# 数据库表结构

## 核心表

### users - 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| username | VARCHAR(50) | 用户名 |
| password | VARCHAR(255) | 密码(SHA256) |
| role | VARCHAR(20) | 角色(admin/normal) |
| created_at | DATETIME | 创建时间 |

### words - 单词表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| textbook_id | INT | 所属课本ID |
| book_name | VARCHAR(100) | 课本名称 |
| word | VARCHAR(100) | 单词 |
| word_json | LONGTEXT | 有道词典JSON数据 |
| created_at | DATETIME | 创建时间 |

### word_textbooks - 课本表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| book_name | VARCHAR(100) | 课本名称 |
| alias | VARCHAR(100) | 别名 |
| title | VARCHAR(200) | 标题 |
| description | TEXT | 描述 |
| word_count | INT | 单词数量 |
| file_size | VARCHAR(50) | 文件大小 |
| recite_user_count | INT | 使用人数 |
| cover_url | VARCHAR(500) | 封面图URL |
| download_url | VARCHAR(500) | 下载URL |
| version | VARCHAR(20) | 版本 |
| tags | VARCHAR(100) | 标签 |
| local_file | VARCHAR(500) | 本地文件路径 |

### word_play_records - 学习记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| user_id | INT | 用户ID |
| word_id | INT | 单词ID |
| textbook_id | INT | 课本ID |
| play_count | INT | 播放次数 |
| created_at | DATETIME | 创建时间 |

### word_quiz_records - 背诵记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| user_id | INT | 用户ID |
| word_id | INT | 单词ID |
| textbook_id | INT | 课本ID |
| quiz_count | INT | 背诵次数 |
| updated_at | DATETIME | 更新时间 |

### word_wrong_counts - 错题计数表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| user_id | INT | 用户ID |
| word_id | INT | 单词ID |
| textbook_id | INT | 课本ID |
| wrong_count | INT | 错误次数 |
| created_at | DATETIME | 创建时间 |

### word_wrong_review_records - 错题复习记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| user_id | INT | 用户ID |
| word_id | INT | 单词ID |
| textbook_id | INT | 课本ID |
| correct_count | INT | 正确次数 |
| updated_at | DATETIME | 更新时间 |

### grammar_questions - 语法练习题表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| textbook_id | INT | 所属课本ID |
| content_id | INT | 章节ID |
| question_type | VARCHAR(20) | 题目类型 |
| question | TEXT | 题目 |
| options | TEXT | 选项(JSON数组) |
| answer | VARCHAR(10) | 答案 |
| explanation | TEXT | 解析 |
| created_at | DATETIME | 创建时间 |

### grammar_content - 语法章节表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| textbook_id | INT | 所属课本ID |
| title | VARCHAR(200) | 章节标题 |
| parent_id | INT | 父章节ID |
| order_index | INT | 排序 |
| created_at | DATETIME | 创建时间 |

### user_progress - 用户进度表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| user_id | INT | 用户ID |
| content_id | INT | 章节ID |
| status | VARCHAR(20) | 状态 |
| updated_at | DATETIME | 更新时间 |
