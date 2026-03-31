import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from pydantic import BaseModel
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# CORSの設定（フロントエンドからの通信を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストのデータ型定義
class MistakeRequest(BaseModel):
    word_id: int
    user_id: str  # FirebaseのUIDを受け取る

# データベース接続用の共通関数
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print("DB接続エラー:", e)
        raise HTTPException(status_code=500, detail="Database connection failed")

# ==========================================
# 0. アプリ起動時に「ユーザー別ミス記録テーブル」を自動作成
# ==========================================
@app.on_event("startup")
def startup_event():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # user_mistakes テーブルを作成 (すでにあれば何もしない)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_mistakes (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                word_id INTEGER,
                UNIQUE(user_id, word_id)
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized: user_mistakes table is ready.")
    except Exception as e:
        print("Table creation failed:", e)

# ==========================================
# 1. 通常のテスト問題を取得（変更なし）
# ==========================================
@app.get("/api/questions")
def get_questions(start: int = 1, end: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, english, japanese FROM words WHERE id >= %s AND id <= %s", (start, end))
        target_rows = cur.fetchall()

        if not target_rows:
            return []

        pool_words = [row[1] for row in target_rows]
        questions = []
        for row in target_rows:
            word_id = row[0]
            english = row[1]
            japanese = row[2]

            pool = [w for w in pool_words if w != english]
            wrong_choices = random.sample(pool, 5) if len(pool) >= 5 else pool
            
            choices = wrong_choices + [english]
            random.shuffle(choices)

            questions.append({
                "id": word_id,
                "japanese": japanese,
                "correct_answer": english,
                "choices": choices
            })

        random.shuffle(questions)
        cur.close()
        conn.close()
        return questions

    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch questions")

# ==========================================
# 2. 間違えた問題の保存（ユーザー別に保存）
# ==========================================
@app.post("/api/mistake")
def save_mistake(req: MistakeRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # user_id と word_id の組み合わせがすでにないかチェック
        cur.execute("SELECT 1 FROM user_mistakes WHERE user_id = %s AND word_id = %s", (req.user_id, req.word_id))
        if not cur.fetchone():
            # user_mistakes テーブルに保存！
            cur.execute("INSERT INTO user_mistakes (user_id, word_id) VALUES (%s, %s)", (req.user_id, req.word_id))
            conn.commit()
            
        cur.close()
        conn.close()
        return {"message": "Mistake saved for user!"}
    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to save mistake")

# ==========================================
# 3. 復習問題の取得（そのユーザーの記録だけを取得）
# ==========================================
@app.get("/api/questions/mistakes")
def get_mistake_questions(user_id: str):  # ← user_id を必須パラメータに！
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # user_mistakes テーブルから「そのユーザーのデータ」だけを結合して取得
        cur.execute("""
            SELECT w.id, w.english, w.japanese 
            FROM words w
            JOIN user_mistakes m ON w.id = m.word_id
            WHERE m.user_id = %s
        """, (user_id,))
        target_rows = cur.fetchall()

        if not target_rows:
            return []

        cur.execute("SELECT english FROM words")
        all_english_words = [row[0] for row in cur.fetchall()]

        questions = []
        for row in target_rows:
            word_id = row[0]
            english = row[1]
            japanese = row[2]

            pool = [w for w in all_english_words if w != english]
            wrong_choices = random.sample(pool, 5) if len(pool) >= 5 else pool
            
            choices = wrong_choices + [english]
            random.shuffle(choices)

            questions.append({
                "id": word_id,
                "japanese": japanese,
                "correct_answer": english,
                "choices": choices
            })

        random.shuffle(questions)
        cur.close()
        conn.close()
        return questions

    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch mistakes")

# ==========================================
# 4. 間違えた問題の削除（そのユーザーの記録だけを消す）
# ==========================================
@app.delete("/api/mistake/{word_id}")
def delete_mistake(word_id: int, user_id: str):  # ← user_id を追加！
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # user_id と word_id が両方一致するデータだけを削除
        cur.execute("DELETE FROM user_mistakes WHERE word_id = %s AND user_id = %s", (word_id, user_id))
        conn.commit()
        
        cur.close()
        conn.close()
        return {"message": "Mistake deleted for user!"}
    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to delete mistake")