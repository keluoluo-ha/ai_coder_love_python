# config.py
import os
from dotenv import load_dotenv

# 加载当前目录下的.env文件，注入到系统环境变量
load_dotenv()

# ---------------- LLM 大模型配置 ----------------
# ChatTongyi会自动读取环境变量 DASHSCOPE_API_KEY
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen-plus")  # 默认兜底qwen-plus

# ---------------- MySQL 数据库配置 ----------------
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DATABASE")
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# PostgreSQL向量库配置
PG_CONFIG = {
    "host": os.getenv("PG_HOST"),
    "port": int(os.getenv("PG_PORT")),  # 端口转数字
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "database": os.getenv("PG_DB")
}

# LangChain专用连接字符串
PG_CONN_STR = (
    f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}"
    f"@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}"
)
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
