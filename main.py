import os
import json
import random
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ==========================================
# 1. 外部のJSONファイルから単語データを読み込む
# ==========================================
with open("words.json", "r", encoding="utf-8") as f:
    words_db = json.load(f)

class MistakeRequest(BaseModel):
    word_id: int

# ==========================================
# 2. 【新機能】範囲を指定して、シャッフルした問題の束を返すAPI
# ==========================================
@app.get("/api/questions")
def get_questions(start: int = 1, end: int = 10):
    """指定された範囲の単語をランダムな順番で一気に返すAPI"""
    
    # ① ユーザーが指定した範囲（start 〜 end）の単語だけを抽出
    target_words = [w for w in words_db if start <= w["id"] <= end]
    
    # ② 抽出した単語の順番をランダムにシャッフル！（これで重複が出なくなります）
    random.shuffle(target_words)
    
    # ③ ダミーの選択肢を作るために、全単語の英語リストを用意
    all_english = [w["english"] for w in words_db]
    
    # ④ フロントエンド（画面）に返すための問題リストを作成
    questions_list = []
    for target in target_words:
        # 6つの選択肢をランダムに選ぶ
        choices = random.sample(all_english, min(6, len(all_english)))
        
        # 正解が含まれていなかったら、一つを正解にすり替える
        if target["english"] not in choices:
            choices[0] = target["english"]
        
        # 選択肢の並び順もシャッフル
        random.shuffle(choices)
        
        # 1問分のデータをリストに追加
        questions_list.append({
            "id": target["id"],
            "japanese": target["japanese"],
            "choices": choices,
            "correct_answer": target["english"]
        })
        
    return questions_list

# ==========================================
# 3. 間違えた問題の保存・削除（変更なし）
# ==========================================
@app.post("/api/mistake")
def add_mistake(req: MistakeRequest):
    if not DATABASE_URL:
        return {"message": "ローカルテスト等でDBが無い場合はスキップ"}
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO mistakes (word_id) VALUES (%s) ON CONFLICT (word_id) DO NOTHING", (req.word_id,))
    return {"message": "クラウドのDBにフラグを保存しました"}

@app.delete("/api/mistake/{word_id}")
def remove_mistake(word_id: int):
    if not DATABASE_URL:
        return {"status": "skipped"}
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM mistakes WHERE word_id = %s", (word_id,))
    return {"status": "success", "message": f"ID {word_id} をクラウドから削除しました"}

# ==========================================
# 4. 【アップデート】間違えた問題を「山札」にして一括で返す
# ==========================================
@app.get("/api/questions/mistakes")
def get_mistake_questions():
    if not DATABASE_URL:
         return [] # DBがない場合は空っぽを返す

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT word_id FROM mistakes")
            db_results = cursor.fetchall()
            mistake_ids = [row[0] for row in db_results]

    if not mistake_ids:
        return [] # 間違えた問題がゼロの場合
    
    # ① 間違えたIDの単語だけを抽出
    target_mistakes = [w for w in words_db if w["id"] in mistake_ids]
    
    # ② 抽出した単語をシャッフル
    random.shuffle(target_mistakes)
    
    all_english = [w["english"] for w in words_db]
    questions_list = []
    
    # ③ フロントエンドに返すための山札リストを作成
    for target in target_mistakes:
        choices = random.sample(all_english, min(6, len(all_english)))
        if target["english"] not in choices:
            choices[0] = target["english"]
        random.shuffle(choices)
        
        questions_list.append({
            "id": target["id"],
            "japanese": target["japanese"],
            "choices": choices,
            "correct_answer": target["english"]
        })

    return questions_list