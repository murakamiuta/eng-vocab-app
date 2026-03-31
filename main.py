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

# データベース接続用の共通関数
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print("DB接続エラー:", e)
        raise HTTPException(status_code=500, detail="Database connection failed")

# ==========================================
# 1. 通常のテスト問題を取得（6択 ＆ ダミーは範囲内から！）
# ==========================================
@app.get("/api/questions")
def get_questions(start: int = 1, end: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ① 指定された範囲の単語を取得
        cur.execute("SELECT id, english, japanese FROM words WHERE id >= %s AND id <= %s", (start, end))
        target_rows = cur.fetchall()

        if not target_rows:
            return []

        # ② ダミー選択肢のプールを「今回取得した範囲内の単語だけ」に限定する
        pool_words = [row[1] for row in target_rows]

        questions = []
        for row in target_rows:
            word_id = row[0]
            english = row[1]
            japanese = row[2]

            # 正解以外の単語を「同じ範囲内」からランダムに 5つ 選ぶ
            pool = [w for w in pool_words if w != english]
            wrong_choices = random.sample(pool, 5) if len(pool) >= 5 else pool
            
            # 正解と混ぜてシャッフル
            choices = wrong_choices + [english]
            random.shuffle(choices)

            questions.append({
                "id": word_id,
                "japanese": japanese,
                "correct_answer": english,
                "choices": choices
            })

        # ランダムに出題順をシャッフル
        random.shuffle(questions)

        cur.close()
        conn.close()
        return questions

    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch questions")

# ==========================================
# 2. 間違えた問題の保存
# ==========================================
@app.post("/api/mistake")
def save_mistake(req: MistakeRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # すでに登録されていないかチェックしてから追加
        cur.execute("SELECT 1 FROM mistakes WHERE word_id = %s", (req.word_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO mistakes (word_id) VALUES (%s)", (req.word_id,))
            conn.commit()
            
        cur.close()
        conn.close()
        return {"message": "Mistake saved!"}
    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to save mistake")

# ==========================================
# 3. 復習問題の取得（6択 ＆ ダミーは全単語から）
# ==========================================
@app.get("/api/questions/mistakes")
def get_mistake_questions():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # mistakes テーブルと words テーブルを結合して取得
        cur.execute("""
            SELECT w.id, w.english, w.japanese 
            FROM words w
            JOIN mistakes m ON w.id = m.word_id
        """)
        target_rows = cur.fetchall()

        if not target_rows:
            return []

        # 復習モードの場合は、選択肢不足を防ぐため「全単語」をダミー候補にする
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
# 4. 間違えた問題の削除（正解した時）
# ==========================================
@app.delete("/api/mistake/{word_id}")
def delete_mistake(word_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM mistakes WHERE word_id = %s", (word_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        return {"message": "Mistake deleted!"}
    except Exception as e:
        print("エラー:", e)
        raise HTTPException(status_code=500, detail="Failed to delete mistake")