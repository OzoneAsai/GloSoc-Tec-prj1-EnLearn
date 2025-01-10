import zipfile
from flask import Flask, render_template, request, jsonify, session, g
import random
from flask_cors import CORS
from flask import send_from_directory, abort
import os
import hashlib
from gtts import gTTS  # Import gTTS

import nltk
import os

import pandas as pd
import requests
import csv

# Hugging Faceのキャッシュ場所を変更
os.environ["HF_HOME"] = "./hf_cache"

# 必要に応じて他のキャッシュパスも設定
os.environ["HF_DATASETS_CACHE"] = "./hf_datasets_cache"
os.environ["TRANSFORMERS_CACHE"] = "./hf_transformers_cache"

# NLTKデータの保存場所を指定
nltk_data_dir = "./nltk_data"
if nltk_data_dir not in nltk.data.path:
    nltk.data.path.append(nltk_data_dir)

print(nltk.data.path)

nltk.download('punkt', download_dir=nltk_data_dir)
nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir)
from datasets import load_dataset

# -----------------------------
# Flaskアプリの初期設定
# -----------------------------
app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # 開発用途のダミーキー
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# グローバル変数 (簡易メモリ保持)
# -----------------------------
app.config["SHUFFLED_DATA"] = None      # シャッフル後の英日ペアを保管するリスト
app.config["CURRENT_INDEX"] = 0         # 学習進捗のカウンター
app.config["PHASE"] = 1                # 現在のフェーズ (1, 2, 3 を想定)
app.config["BATCH_SIZE"] = 2           # 一度に処理するデータの数
app.config["METADATA"] = {}            # 英文と音声ファイルのマッピング

# -----------------------------
# データセットロードと初期化
# -----------------------------
def init_dataset():
    """英日ペアデータをロードし、そのままリストを返す。"""
    ds = load_dataset("OzoneAsai/EnglishFlashcards")
    data_list = list(zip(ds["enja"]["English"], ds["enja"]["Japanese"]))
    return data_list

# ダウンロード用の定数
ZIP_URL = "https://huggingface.co/datasets/OzoneAsai/GloSocTes1Audio/resolve/main/audios.zip?download=true"
ZIP_FILE_NAME = "audios.zip"
TARGET_FOLDER = "audios"

def initialize_audios():
    """audio フォルダが存在しない場合にダウンロードと解凍を行う"""
    if not os.path.exists(TARGET_FOLDER):
        print(f"{TARGET_FOLDER} フォルダが見つかりません。ダウンロードを開始します。")

        # ZIP ファイルをダウンロード
        print(f"{ZIP_FILE_NAME} をダウンロードしています...")
        response = requests.get(ZIP_URL, stream=True)
        if response.status_code == 200:
            with open(ZIP_FILE_NAME, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"{ZIP_FILE_NAME} のダウンロードが完了しました。")
        else:
            raise Exception(f"ダウンロードに失敗しました。ステータスコード: {response.status_code}")

        # ZIP ファイルを解凍
        print(f"{ZIP_FILE_NAME} を解凍しています...")
        with zipfile.ZipFile(ZIP_FILE_NAME, "r") as zip_ref:
            zip_ref.extractall(".")
        print(f"{ZIP_FILE_NAME} の解凍が完了しました。")

        # ZIP ファイルを削除（不要な場合）
        os.remove(ZIP_FILE_NAME)
        print(f"{ZIP_FILE_NAME} を削除しました。")
    else:
        print(f"{TARGET_FOLDER} フォルダが既に存在します。初期化は不要です。")

def load_metadata():
    """metadata.csvを読み込み、英文と音声ファイルのマッピングを作成する。"""
    metadata_path = "metadata.csv"
    if not os.path.isfile(metadata_path):
        raise FileNotFoundError(f"{metadata_path} が見つかりません。")
    
    metadata = {}
    with open(metadata_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            english = row['English'].strip()
            audio_path = row['AudioPath'].strip()
            metadata[english.lower()] = audio_path  # 小文字化して一貫性を持たせる
    return metadata

# -----------------------------
# アプリ起動時のフック (必要に応じて)
# -----------------------------
@app.before_first_request
def before_first_request_func():
    """サーバー起動後、初回リクエスト前にデータを読み込む。"""
    print("Initializing audios...")
    initialize_audios()
    print("Loading metadata...")
    app.config["METADATA"] = load_metadata()
    print("Initializing dataset...")
    if app.config["SHUFFLED_DATA"] is None:
        app.config["SHUFFLED_DATA"] = init_dataset()  # シードを固定
        app.config["CURRENT_INDEX"] = 0
        app.config["PHASE"] = 1
    print("Initialization complete.")

# -----------------------------
# マスク関数
# -----------------------------
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

# -----------------------------
# APIエンドポイント
# -----------------------------

# エンドポイント: /start
# データセットの再初期化 & 学習サイクル開始
@app.route("/start", methods=["GET"])
def start():
    # 毎回初期化したい場合などはここでリセットする
    seed = request.args.get("seed", 42, type=int)
    shuffled_data = init_dataset()
    random.seed(seed)
    random.shuffle(shuffled_data)
    app.config["SHUFFLED_DATA"] = shuffled_data
    app.config["CURRENT_INDEX"] = 0
    app.config["PHASE"] = 1
    
    # 2件を切り出して返す (Phase1)
    slice_data = shuffled_data[0:app.config["BATCH_SIZE"]]
    response_data = []
    for eng, jpn in slice_data:
        masked_english = mask_sentence(eng)
        response_data.append({"original_english": eng, "masked_english": masked_english, "japanese": jpn})
    
    return jsonify({
        "message": "Phase1 started with fresh data.",
        "phase": app.config["PHASE"],
        "current_index": app.config["CURRENT_INDEX"],
        "rows": response_data,
        "session_id": hashlib.md5(os.urandom(16)).hexdigest()  # セッションIDを生成
    })

from werkzeug.utils import safe_join
from werkzeug.exceptions import NotFound

@app.route('/', methods=['GET'])
def serve_main():
    return render_template('index.html')

@app.route('/static/<path:file_path>', methods=['GET'])
def serve_static(file_path):
    BASE_DIRECTORY = "static"  # 'static' ディレクトリを使用
    try:
        # 安全なパス結合
        secure_path = safe_join(BASE_DIRECTORY, file_path)
        
        # ファイルの存在確認
        if not os.path.isfile(secure_path):
            abort(404, description="File not found")
        
        # ファイルを返す
        return send_from_directory(BASE_DIRECTORY, file_path)
    except NotFound:
        abort(403, description="Forbidden: Invalid file path")
    except Exception as e:
        abort(500, description=str(e))

# エンドポイント: /phase1
# 2行分を返して、リスニング+リーディングを行う
@app.route("/phase1", methods=["GET"])
def phase1_endpoint():
    session_id = request.args.get("session_id", type=str)
    if not session_id:
        return jsonify({"message": "Session ID is required."}), 400

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

# エンドポイント: /phase2
# Phase1の行から、動詞・前置詞・接続詞をマスクして返す
@app.route("/phase2", methods=["GET"])
def phase2_endpoint():
    session_id = request.args.get("session_id", type=str)
    if not session_id:
        return jsonify({"message": "Session ID is required."}), 400

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

# エンドポイント: /check_answer
# ユーザーが送信した回答を判定する (簡易実装)

@app.route("/check_answer", methods=["POST"])
def check_answer_endpoint():
    data = request.get_json()
    session_id = data.get("session_id", "")
    original = data.get("original_english", "")
    answers = data.get("answers", [])
    masked_english = data.get("masked_english", "")

    if not session_id:
        return jsonify({"message": "Session ID is required."}), 400

    tokens = nltk.word_tokenize(original)
    tagged = nltk.pos_tag(tokens)
    
    correct_tags = []
    for w, pos in tagged:
        # 動詞 (VB*), 前置詞 (IN), 接続詞 (CC), 不定詞マーカー (TO) を正解候補とする
        # かつ単語がアルファベットのみで構成されている場合
        if (pos.startswith("VB") or pos in ("IN", "CC", "TO")) and w.isalpha():
            correct_tags.append(w.lower())  # 正解候補

    # 正答カウント
    correct_count = 0
    feedback_messages = []
    for user_ans, correct_ans in zip(answers, correct_tags):
        if user_ans.lower() == correct_ans:
            correct_count += 1
            feedback_messages.append("Correct!")
        else:
            feedback_messages.append(f"Incorrect. The correct answer was '{correct_ans}'.")

    feedback = " ".join(feedback_messages)
    response = {
        "message": "Answer checked.",
        "feedback": feedback,
        "correct_count": correct_count,
        "required": len(correct_tags)
    }
    return jsonify(response), 200

# エンドポイント: /next_phase
# サイクル制御 (Phase3 相当) → 次へ進む or 終了チェック
@app.route("/next_phase", methods=["POST"])
def next_phase_endpoint():
    data = request.get_json()
    session_id = data.get("session_id", "")
    if not session_id:
        return jsonify({"message": "Session ID is required."}), 400

    # 現在のindexを +BATCH_SIZE
    app.config["CURRENT_INDEX"] += app.config["BATCH_SIZE"]
    
    # もしデータ数を超えたなら終了またはループなどのロジック
    data_length = len(app.config["SHUFFLED_DATA"])
    if app.config["CURRENT_INDEX"] >= data_length:
        app.config["PHASE"] = 3  # 完了フェーズ
        return jsonify({
            "message": "All data exhausted. Training complete!",
            "phase": "complete",
            "current_index": app.config["CURRENT_INDEX"]
        })
    
    # 現在のフェーズに基づき、次のフェーズへ
    if app.config["PHASE"] == 1:
        # Phase1からPhase2へ移行
        app.config["PHASE"] = 2
        return jsonify({
            "message": "Moved to Phase2.",
            "phase": app.config["PHASE"],
            "current_index": app.config["CURRENT_INDEX"]
        })
    elif app.config["PHASE"] == 2:
        # Phase2からPhase1へ戻す（次のバッチ）
        app.config["PHASE"] = 1
        return jsonify({
            "message": "Moved to Phase1.",
            "phase": app.config["PHASE"],
            "current_index": app.config["CURRENT_INDEX"]
        })
    else:
        return jsonify({"message": "Invalid phase."}), 400

# エンドポイント: /getSound
# 音声を生成して返す

# CSVファイルのパスを設定
METADATA_CSV_PATH = "metadata.csv"

def load_metadata_csv():
    """CSVファイルを読み込み、DataFrameを返す"""
    try:
        metadata_df = pd.read_csv(METADATA_CSV_PATH)
        return metadata_df
    except FileNotFoundError:
        return None

@app.route("/getSound", methods=["GET"])
def get_sound_endpoint():
    sentence = request.args.get('sentence', '', type=str)
    print(f"Received sentence: {sentence}")
    if not sentence:
        return jsonify({
            "message": "No sentence provided.",
            "sound_url": None
        }), 400

    # 検索のためのキーを準備
    sentence_lower = sentence.lower()
    sentence_original = sentence

    # 方法1: 辞書で小文字化されたキーを使用して検索
    metadata_dict = app.config.get("METADATA_DICT", {})
    audio_path = metadata_dict.get(sentence_lower, None)

    # 方法1: 辞書で元のキーを使用して検索（必要に応じて）
    if not audio_path:
        audio_path = metadata_dict.get(sentence_original, None)

    # 方法2: CSVファイルを用いた検索
    if not audio_path:
        metadata_df = load_metadata_csv()
        if metadata_df is None:
            return jsonify({
                "message": "Metadata CSV file not found.",
                "sound_url": None
            }), 500

        # まず小文字化して検索
        audio_path_row = metadata_df[metadata_df['English'].str.lower() == sentence_lower]
        if not audio_path_row.empty:
            audio_path = audio_path_row.iloc[0]['AudioPath']
        else:
            # 小文字化で見つからなければ、元の文で再検索
            audio_path_row = metadata_df[metadata_df['English'] == sentence_original]
            if not audio_path_row.empty:
                audio_path = audio_path_row.iloc[0]['AudioPath']

    # どちらの方法でも見つからない場合
    if not audio_path:
        return jsonify({
            "message": "Audio file for the provided sentence does not exist.",
            "sound_url": None
        }), 404

    # 音声ファイルの存在を確認
    if not os.path.isfile(audio_path):
        return jsonify({
            "message": "Audio file not found on the server.",
            "sound_url": None
        }), 404

    # 音声URLを構築
    sound_url = audio_path.replace('./', '/')
    return jsonify({
        "message": "Audio found.",
        "sound_url": sound_url
    }), 200

# 静的ファイルのルーティング設定
@app.route('/audios/<path:filename>')
def serve_audio_static(filename):
    audio_dir = os.path.join('audios')
    return send_from_directory(audio_dir, filename)

# -----------------------------
# Flaskアプリ起動
# -----------------------------
if __name__ == "__main__":
    # 開発時に使うポートなどを設定
    app.run(host="0.0.0.0", port=7860, )
