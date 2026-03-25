from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
import random
import psycopg2 # ← 変更：Supabase（PostgreSQL）と会話するための翻訳機
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ==========================================
# 🔑 クラウドデータベースの鍵（URL）を設定します
# 先ほどコピーしてパスワードを書き換えたURLを、以下の "" の中に貼り付けてください！
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- 仮のデータ ---
words_db = [
    {"id": 1, "english": "follow", "japanese": "〜に従う", "page": 24},
    {"id": 2, "english": "consider", "japanese": "〜を考慮する", "page": 25},
    {"id": 3, "english": "increase", "japanese": "増える", "page": 25},
    {"id": 4, "english": "expect", "japanese": "〜を予期する", "page": 26},
    {"id": 5, "english": "decide", "japanese": "〜を決定する", "page": 26},
    {"id": 6, "english": "develop", "japanese": "発達する", "page": 27},
    {"id": 7, "english": "provide", "japanese": "〜を与える", "page": 27},
]

class MistakeRequest(BaseModel):
    word_id: int

# --- APIのエンドポイント ---

@app.get("/api/question")
def get_question():
    """問題と6択の選択肢を返すAPI（変更なし）"""
    target_word = random.choice(words_db)
    all_english = [w["english"] for w in words_db]
    choices = random.sample(all_english, min(6, len(all_english)))
    if target_word["english"] not in choices:
        choices[0] = target_word["english"]
    random.shuffle(choices)

    return {
        "id": target_word["id"],
        "japanese": target_word["japanese"],
        "choices": choices,
        "page": target_word["page"],
        "correct_answer": target_word["english"]
    }

@app.post("/api/mistake")
def add_mistake(req: MistakeRequest):
    """【Supabase対応】間違えた問題のIDをクラウドに保存する"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            # PostgreSQLの文法に変更（? ではなく %s を使い、重複エラーを防ぐ）
            cursor.execute("INSERT INTO mistakes (word_id) VALUES (%s) ON CONFLICT (word_id) DO NOTHING", (req.word_id,))
    return {"message": "クラウドのDBにフラグを保存しました"}

@app.delete("/api/mistake/{word_id}")
def remove_mistake(word_id: int):
    """【Supabase対応】正解したときに、クラウドからそのIDを消す"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM mistakes WHERE word_id = %s", (word_id,))
    return {"status": "success", "message": f"ID {word_id} をクラウドから削除しました"}

@app.get("/api/question/mistakes")
def get_mistake_question():
    """【Supabase対応】クラウドから間違えたリストを取り出して出題する"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT word_id FROM mistakes")
            db_results = cursor.fetchall()
            mistake_ids = [row[0] for row in db_results]

    if not mistake_ids:
        return {"data": None, "message": "全てクリアしました！"}
    
    target_mistakes = [w for w in words_db if w["id"] in mistake_ids]
    target_word = random.choice(target_mistakes)
    
    all_english = [w["english"] for w in words_db]
    choices = random.sample(all_english, min(6, len(all_english)))
    if target_word["english"] not in choices:
        choices[0] = target_word["english"]
    random.shuffle(choices)

    return {
        "id": target_word["id"],
        "japanese": target_word["japanese"],
        "choices": choices,
        "page": target_word["page"],
        "correct_answer": target_word["english"]
    }