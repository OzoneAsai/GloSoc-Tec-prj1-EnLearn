from flask import Flask, render_template, request, jsonify, session, g
from datasets import load_dataset
import nltk
import random
import flask_cors
from flask import send_from_directory, abort
import os

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# -----------------------------
# Flaskアプリの初期設定
# -----------------------------
app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # 開発用途のダミーキー
flask_cors.CORS(app)

# -----------------------------
# グローバル変数 (簡易メモリ保持)
# -----------------------------
app.config["SHUFFLED_DATA"] = None      # シャッフル後の英日ペアを保管するリスト
app.config["CURRENT_INDEX"] = 0         # 学習進捗のカウンター
app.config["PHASE"] = 1                # 現在のフェーズ (1, 2, 3 を想定)
app.config["BATCH_SIZE"] = 2           # 一度に処理するデータの数

# -----------------------------
# データセットロードと初期化
# -----------------------------
def init_dataset(seed=42):
    """英日ペアデータをロードし、指定シードでシャッフルしたリストを返す。"""
    ds = load_dataset("OzoneAsai/EnglishFlashcards")
    data_list = list(zip(ds["enja"]["English"], ds["enja"]["Japanese"]))
    random.seed(seed)
    random.shuffle(data_list)
    return data_list

# -----------------------------
# アプリ起動時のフック (必要に応じて)
# -----------------------------
@app.before_first_request
def before_first_request():
    """サーバー起動後、初回リクエスト前にシャッフル済みのデータを読み込む。"""
    if app.config["SHUFFLED_DATA"] is None:
        app.config["SHUFFLED_DATA"] = init_dataset(seed=42)  # シードを固定
        app.config["CURRENT_INDEX"] = 0
        app.config["PHASE"] = 1

# -----------------------------
# エンドポイント: /start
# データセットの再初期化 & 学習サイクル開始
# -----------------------------
@app.route("/start", methods=["GET"])
def start():
    # 毎回初期化したい場合などはここでリセットする
    seed = request.args.get("seed", 42, type=int)
    shuffled_data = init_dataset(seed)
    app.config["SHUFFLED_DATA"] = shuffled_data
    app.config["CURRENT_INDEX"] = 0
    app.config["PHASE"] = 1
    
    # 2件を切り出して返す (Phase1)
    slice_data = shuffled_data[0:app.config["BATCH_SIZE"]]
    response_data = []
    for eng, jpn in slice_data:
        response_data.append({"original_english": eng, "masked_english": mask_sentence(eng), "japanese": jpn})
    
    return jsonify({
        "message": "Phase1 started with fresh data.",
        "phase": app.config["PHASE"],
        "current_index": app.config["CURRENT_INDEX"],
        "rows": response_data
    })

def mask_sentence(sentence):
    """指定された品詞をマスクする関数。記号やハイフンはマスクしない。"""
    tokens = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(tokens)
    
    masked_sentence = []
    for word, pos in tagged:
        # 動詞 (VB*), 前置詞 (IN), 接続詞 (CC), 不定詞マーカー (TO) をマスク
        # かつ単語がアルファベットのみで構成されている場合
        if (pos.startswith("VB") or pos in ("IN", "CC", "TO")) and word.isalpha():
            masked_sentence.append("____")
        else:
            masked_sentence.append(word)
    return " ".join(masked_sentence)

BASE_DIRECTORY = "./frontend"

@app.route('/', methods=['GET'])
def serve_main():
    return render_template('index.html')

@app.route('/<path:file_path>', methods=['GET'])
def serve_file(file_path):
    try:
        # ファイルパスの正規化とディレクトリトラバーサル防止
        secure_path = os.path.normpath(os.path.join(BASE_DIRECTORY, file_path))
        
        # ベースディレクトリ外へのアクセスを防止
        if not secure_path.startswith(os.path.abspath(BASE_DIRECTORY)):
            abort(403, description="Forbidden: Invalid file path")
        
        # ファイルの存在確認
        if not os.path.isfile(secure_path):
            abort(404, description="File not found")
        
        # ファイルを返す
        return send_from_directory(BASE_DIRECTORY, file_path)
    except Exception as e:
        abort(500, description=str(e))

# -----------------------------
# エンドポイント: /phase1
# 2行分を返して、リスニング+リーディングを行う
# -----------------------------
@app.route("/phase1", methods=["GET"])
def phase1():
    # 現在のインデックスを取得
    idx = app.config["CURRENT_INDEX"]
    data = app.config["SHUFFLED_DATA"]
    
    # フェーズを明示的に1に設定しておく
    app.config["PHASE"] = 1
    
    # BATCH_SIZE件切り出してマスキング
    slice_data = data[idx:idx+app.config["BATCH_SIZE"]]
    masked_rows = []

    for eng, jpn in slice_data:
        masked_english = mask_sentence(eng)
        masked_rows.append({
            "original_english": eng,
            "masked_english": masked_english,
            "japanese": jpn
        })

    return jsonify({
        "message": "Phase1: Listen and read these rows (with masked placeholders).",
        "phase": app.config["PHASE"],
        "current_index": idx,
        "rows": masked_rows
    })

# -----------------------------
# エンドポイント: /phase2
# Phase1の行から、動詞・前置詞・接続詞をマスクして返す
# -----------------------------
@app.route("/phase2", methods=["GET"])
def phase2():
    idx = app.config["CURRENT_INDEX"]
    data = app.config["SHUFFLED_DATA"]
    
    # フェーズを2に更新
    app.config["PHASE"] = 2
    
    # BATCH_SIZE件切り出してマスキング（既にmask_sentenceを使っているので再度マスクする必要はない）
    slice_data = data[idx:idx+app.config["BATCH_SIZE"]]
    masked_rows = []

    for eng, jpn in slice_data:
        masked_english = mask_sentence(eng)
        masked_rows.append({
            "original_english": eng,
            "masked_english": masked_english,
            "japanese": jpn
        })

    return jsonify({
        "message": "Phase2: Here are your masked rows. Fill the blanks!",
        "phase": app.config["PHASE"],
        "current_index": idx,
        "rows": masked_rows
    })

# -----------------------------
# エンドポイント: /check_answer
# ユーザーが送信した回答を判定する (簡易実装)
# -----------------------------
@app.route("/check_answer", methods=["POST"])
def check_answer():
    data = request.get_json()
    original = data.get("original_english", "")
    answers = data.get("answers", [])
    masked_english = data.get("masked_english", "")

    tokens = nltk.word_tokenize(original)
    tagged = nltk.pos_tag(tokens)
    
    correct_tags = []
    for w, pos in tagged:
        if pos.startswith("VB") or pos in ("IN", "CC", "TO"):
            correct_tags.append(w.lower())  # 正解候補

    # 正答カウント
    correct_count = 0
    for ans in answers:
        if ans.lower() in correct_tags:
            correct_count += 1

    # シンプルなフィードバック
    feedback = f"{correct_count}/{len(correct_tags)} correct answers."

    return jsonify({
        "message": "Answer checked.",
        "feedback": feedback,
        "correct_count": correct_count,
        "required": len(correct_tags)
    })

# -----------------------------
# エンドポイント: /next_phase
# サイクル制御 (Phase3 相当) → 次へ進む or 終了チェック
# -----------------------------
@app.route("/next_phase", methods=["POST"])
def next_phase():
    # 現在のindexを +BATCH_SIZE
    app.config["CURRENT_INDEX"] += app.config["BATCH_SIZE"]
    
    # もしデータ数を超えたなら終了またはループなどのロジック
    data_length = len(app.config["SHUFFLED_DATA"])
    if app.config["CURRENT_INDEX"] >= data_length:
        return jsonify({
            "message": "All data exhausted. Training complete!",
            "phase": "complete",
            "current_index": app.config["CURRENT_INDEX"]
        })
    
    # これでフェーズを1に戻す (Phase3からPhase1へ)
    app.config["PHASE"] = 1
    return jsonify({
        "message": "Moved to next set of rows.",
        "phase": app.config["PHASE"],
        "current_index": app.config["CURRENT_INDEX"]
    })

# -----------------------------
# エンドポイント: /getSound (ダミー)
# 実際の音声ファイルは返さず、ダミーデータやステータスを返すだけ
# -----------------------------
@app.route("/getSound", methods=["GET"])
def get_sound():
    # ダミーで何か固定のレスポンスを返すだけの例
    return jsonify({
        "message": "This endpoint is a dummy. No audio file is returned.",
        "sound_url": None
    })

# -----------------------------
# Flaskアプリ起動
# -----------------------------
if __name__ == "__main__":
    # 開発時に使うポートなどを設定
    app.run(host="0.0.0.0", port=5000, debug=True)
