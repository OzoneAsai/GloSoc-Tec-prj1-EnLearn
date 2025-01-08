import zipfile
from flask import Flask, render_template, request, jsonify, session, g
import random
import flask_cors
from flask import send_from_directory, abort
import os
import hashlib
from gtts import gTTS  # Import gTTS

import nltk
import os

import requests

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
flask_cors.CORS(app, resources={r"/*": {"origins": "*"}})

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


# -----------------------------
# アプリ起動時のフック (必要に応じて)
# -----------------------------
@app.before_first_request
def before_first_request():
    """サーバー起動後、初回リクエスト前にデータを読み込む。"""
    print("init")
    initialize_audios()
    if app.config["SHUFFLED_DATA"] is None:
        app.config["SHUFFLED_DATA"] = init_dataset()  # シードを固定
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
# エンドポイント: /getSound
# 音声を生成して返す
# -----------------------------

# 音声ファイルを保存するディレクトリ
AUDIO_DIR_AAC = os.path.join('audios', 'aac')
AUDIO_DIR_MP3 = os.path.join('audios', 'mp3')

# ディレクトリが存在しない場合は作成
os.makedirs(AUDIO_DIR_AAC, exist_ok=True)
os.makedirs(AUDIO_DIR_MP3, exist_ok=True)

@app.route("/getSound", methods=["GET"])
def get_sound():
    sentence = request.args.get('sentence', '', type=str)
    if not sentence:
        return jsonify({
            "message": "No sentence provided.",
            "sound_url": None
        }), 400

    # 文章のハッシュを作成してファイル名に使用
    hash_object = hashlib.md5(sentence.encode('utf-8'))
    filename_base = hash_object.hexdigest()

    # AACファイルのパス
    filename_aac = f"{filename_base}.aac"
    audio_path_aac = os.path.join(AUDIO_DIR_AAC, filename_aac)

    # MP3ファイルのパス
    filename_mp3 = f"{filename_base}.mp3"
    audio_path_mp3 = os.path.join(AUDIO_DIR_MP3, filename_mp3)

    # 既存のAACファイルが存在する場合
    if os.path.isfile(audio_path_aac):
        sound_url = f"/audios/aac/{filename_aac}"
        return jsonify({
            "message": "AAC audio found.",
            "sound_url": sound_url
        })

    # AACファイルが存在しない場合、MP3ファイルをチェック
    if not os.path.isfile(audio_path_mp3):
        try:
            # gTTSを使用してMP3形式で音声を生成
            tts = gTTS(text=sentence, lang='en')
            tts.save(audio_path_mp3)
        except Exception as e:
            return jsonify({
                "message": f"Error generating audio: {str(e)}",
                "sound_url": None
            }), 500

    # MP3ファイルのURLを構築
    sound_url = f"/audios/mp3/{filename_mp3}"

    return jsonify({
        "message": "MP3 audio generated successfully.",
        "sound_url": sound_url
    })

# 静的ファイルのルーティング設定
@app.route('/audios/<path:filename>')
def serve_audio(filename):
    if filename.endswith('.aac'):
        return send_from_directory(AUDIO_DIR_AAC, filename)
    elif filename.endswith('.mp3'):
        return send_from_directory(AUDIO_DIR_MP3, filename)
    else:
        return jsonify({"message": "File format not supported."}), 400

# -----------------------------
# Flaskアプリ起動
# -----------------------------
if __name__ == "__main__":
    # 開発時に使うポートなどを設定
    app.run(host="0.0.0.0", port=7860,)
