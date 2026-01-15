-- 1. 创建数据库，指定编码为 UTF8（对 Galgame 中的多语言文本至关重要）
CREATE DATABASE gal_helper_db 
WITH 
OWNER = postgres 
ENCODING = 'UTF8' 
CONNECTION LIMIT = -1;


-- 2. 切换到该数据库后，务必安装 pgvector 扩展
-- 这是你实现 RAG 向量搜索的前提条件
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. 创建受限制的数据库用户
-- 创建用户
CREATE USER gal_admin WITH PASSWORD 'PHblJ7IvI5b6uy04';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE gal_helper_db TO gal_admin;

-- 3.1. 确保 Schema 权限（你之前可能已执行，再跑一次无妨）
GRANT USAGE, CREATE ON SCHEMA public TO gal_admin;

-- 3.2. 授予所有现有表的权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gal_admin;

-- 3.3. 授予所有序列权限（关键：自增主键报错通常是因为漏了这个）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gal_admin;

-- 3.4. 修正未来表的默认权限（一劳永逸）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gal_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gal_admin;

-- 4. 检查 pgvector 是否可用
SELECT ' [1,2,3] '::vector;

-- 5. 表创建
-- 创建ID生成表
CREATE TABLE sys_sequence (
    seq_name VARCHAR(50) PRIMARY KEY, -- 对应你的表名，如 'ai_chat_session_info'
    current_value INT8 NOT NULL,      -- 当前已分配的最大 ID
    increment_by INT4 NOT NULL DEFAULT 1 -- 步长（每次取几个 ID）
);

-- 创建会话信息记录表
CREATE TABLE ai_chat_session_info (
    "id"           INT8 PRIMARY KEY,                      -- ID (INT8 对应 Java 的 Long)
	"chat_session_code" varchar(50) UNIQUE,               -- 会话编码
    "user_intent"  INT4,                                  -- 用户意图 (存储 1, 2, 3, 4 等编号)
    "chat_session_memory" JSONB,                          -- 会话记忆 (JSONB 格式，存储上下文)
	"current_message_id" INT8,                            -- 当前的消息序列
    "create_time"  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- 创建时间 (带时区)
    "update_time"  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP  -- 修改时间 (带时区)
);

-- 添加字段注释（对应你图片中的中文 Name）
COMMENT ON TABLE ai_chat_session_info IS '会话信息记录表';
COMMENT ON COLUMN ai_chat_session_info."id" IS 'ID';
COMMENT ON COLUMN ai_chat_session_info."chat_session_code" IS '会话编码';
COMMENT ON COLUMN ai_chat_session_info."user_intent" IS '用户意图';
COMMENT ON COLUMN ai_chat_session_info."chat_session_memory" IS '会话记忆';
COMMENT ON COLUMN ai_chat_session_info."current_message_id" IS '当前的消息序列';
COMMENT ON COLUMN ai_chat_session_info."create_time" IS '创建时间';
COMMENT ON COLUMN ai_chat_session_info."update_time" IS '修改时间';

-- 创建消息记录表
CREATE TABLE ai_message_info (
    "id"                 INT8 PRIMARY KEY,                      -- ID
    "fk_session_id"      INT8 NOT NULL,                         -- 会话id (外键，关联会话表)
	"message_id"         INT8 NOT NULL,                         -- 在当前会话中的消息序列
    "parent_id"          INT8,                                  -- 当前会话的父消息序列
    "role"               VARCHAR(50),                           -- 角色，例如 USER、ASSISTANT
    "message"            TEXT,                                  -- 消息内容
    "create_time"        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- 创建时间
	"update_time"        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP  -- 修改时间
);

-- 添加字段注释
COMMENT ON TABLE ai_message_info IS '消息记录表';
COMMENT ON COLUMN ai_message_info."id" IS 'ID';
COMMENT ON COLUMN ai_message_info."fk_session_id" IS '会话id';
COMMENT ON COLUMN ai_message_info."message_id" IS '在当前会话中的消息序列';
COMMENT ON COLUMN ai_message_info."parent_id" IS '当前会话的父消息序列';
COMMENT ON COLUMN ai_message_info."role" IS '角色，例如 USER、ASSISTANT';
COMMENT ON COLUMN ai_message_info."message" IS '消息内容';
COMMENT ON COLUMN ai_message_info."create_time" IS '创建时间';
COMMENT ON COLUMN ai_message_info."update_time" IS '修改时间';

-- 6. 原子化函数创建
CREATE OR REPLACE FUNCTION get_next_id(p_seq_name VARCHAR) 
RETURNS INT8 AS $$
DECLARE
    v_next_id INT8;
BEGIN
    -- 1. 锁定该行，防止并发冲突
    -- 2. 更新并返回新值
    UPDATE sys_sequence 
    SET current_value = current_value + increment_by
    WHERE seq_name = p_seq_name
    RETURNING current_value INTO v_next_id;

    RETURN v_next_id;
END;
$$ LANGUAGE plpgsql;

-- 7. 初始数据录入
INSERT INTO sys_sequence (seq_name, current_value) VALUES ('ai_chat_session_info', 1000);
INSERT INTO sys_sequence (seq_name, current_value) VALUES ('ai_message_info', 1000);