from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
import random
import sqlite3 # ← 追加：標準で入っているデータベース機能
import os      # ← 追加：ファイルがあるか確認するため

# APIの本体を作成
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中なので、とりあえずどこからでもアクセスOKにします
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# --- データベースの準備（ここが抜けていました！） ---
DB_FILE = "app_data.db" # 保存するファイルの名前

def init_db():
    """データベースとテーブル（表）を作成する"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # 間違えた問題IDを保存するための「表」を作る
        cursor.execute("CREATE TABLE IF NOT EXISTS mistakes (word_id INTEGER PRIMARY KEY)")
        conn.commit()

# アプリ起動時にデータベースを準備（ファイルを作成）する
init_db()
# ==========================================

# --- 仮のデータ（まずは7個だけでテストします） ---
words_db = [
    {"id": 1, "english": "follow", "japanese": "〜に従う", "page": 24},
    {"id": 2, "english": "consider", "japanese": "〜を考慮する", "page": 25},
    {"id": 3, "english": "increase", "japanese": "増える", "page": 25},
    {"id": 4, "english": "expect", "japanese": "〜を予期する", "page": 26},
    {"id": 5, "english": "decide", "japanese": "〜を決定する", "page": 26},
    {"id": 6, "english": "develop", "japanese": "発達する", "page": 27},
    {"id": 7, "english": "provide", "japanese": "〜を与える", "page": 27},
]

# --- （ここから下を全部書き換えます） ---

# スマホから送られてくるデータの形を定義
class MistakeRequest(BaseModel):
    word_id: int

# --- ここからがAPIのルール（エンドポイント）です ---

@app.get("/api/question")
def get_question():
    """問題と6択の選択肢を返すAPI（ここは変更なし）"""
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
    """【DB対応】間違えた問題のIDをデータベースに保存する"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # INSERT OR IGNORE: もし既に同じIDがあってもエラーにせず無視する
        cursor.execute("INSERT OR IGNORE INTO mistakes (word_id) VALUES (?)", (req.word_id,))
        conn.commit()
    return {"message": "データベースにフラグを保存しました"}

@app.delete("/api/mistake/{word_id}")
def remove_mistake(word_id: int):
    """【DB対応】正解したときに、データベースからそのIDを消す"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # DELETE: 指定したIDのデータを削除する
        cursor.execute("DELETE FROM mistakes WHERE word_id = ?", (word_id,))
        conn.commit()
    return {"status": "success", "message": f"ID {word_id} をDBから削除しました"}

@app.get("/api/question/mistakes")
def get_mistake_question():
    """【DB対応】データベースから間違えたリストを取り出して出題する"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # SELECT: mistakesという表から word_id をすべて持ってくる
        cursor.execute("SELECT word_id FROM mistakes")
        # 取ってきたデータをPythonで扱いやすいリストに変換する
        db_results = cursor.fetchall()
        mistake_ids = [row[0] for row in db_results]

    if not mistake_ids:
        # データベースの中に間違えた問題が1つもない場合
        return {"data": None, "message": "全てクリアしました！"}
    
    # データベースから取ってきたIDと一致する単語だけを words_db から抽出
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