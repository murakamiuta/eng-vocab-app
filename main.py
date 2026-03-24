from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
import random

# APIの本体を作成
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中なので、とりあえずどこからでもアクセスOKにします
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# 間違えた問題のIDを保存するリスト [cite: 8]
mistakes_db = []

# スマホから送られてくるデータの形を定義
class MistakeRequest(BaseModel):
    word_id: int

# --- ここからがAPIのルール（エンドポイント）です ---

@app.get("/api/question")
def get_question():
    """問題と6択の選択肢を返すAPI"""
    
    # 仮データの中からランダムに1つの単語（正解）を選ぶ [cite: 13]
    target_word = random.choice(words_db)
    
    # すべての英語のリストを作り、そこからランダムに6つ選ぶ [cite: 4, 12]
    all_english = [w["english"] for w in words_db]
    choices = random.sample(all_english, min(6, len(all_english)))
    
    # もし選ばれた6つの中に正解が入っていなければ、1つを正解と差し替える
    if target_word["english"] not in choices:
        choices[0] = target_word["english"]
        
    # 選択肢の順番をシャッフルする
    random.shuffle(choices)

    # スマホ側が使いやすいようにデータをまとめて返す
    return {
        "id": target_word["id"],
        "japanese": target_word["japanese"],
        "choices": choices,
        "page": target_word["page"], # 正誤判定後にページ数を出すために必要です [cite: 7, 14]
        "correct_answer": target_word["english"]
    }

@app.post("/api/mistake")
def add_mistake(req: MistakeRequest):
    """間違えた問題にフラグを立てるAPI [cite: 8]"""
    if req.word_id not in mistakes_db:
        mistakes_db.append(req.word_id)
    return {"message": "フラグを保存しました", "current_mistakes": mistakes_db}