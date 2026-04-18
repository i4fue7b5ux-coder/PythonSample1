from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy 
# Flask-Loginのインポート --- (※1)
# LoginManager：ログイン状態を管理する本体
# UserMixin：ユーザーモデルにログイン機能を追加
# login_user：ログイン処理（sessionにID保存）
# current_user：現在ログイン中のユーザー
# logout_user：ログアウト処理
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user

# パスワードのハッシュ化・検証
from werkzeug.security import generate_password_hash, check_password_hash

# OS機能（今回は秘密鍵生成に使用）
import os


# Flaskアプリ作成
app: Flask = Flask(__name__)


# DB設定（SQLite）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)


# ログインマネージャーの設定 --- (※2)
# セッションの改ざん防止用の秘密鍵
# ※毎回変わるので開発用。本番は固定値にする
app.config['SECRET_KEY'] = os.urandom(24)

# ログイン管理オブジェクト作成
login_manager = LoginManager()

# Flaskにログイン機能を組み込む（必須）
login_manager.init_app(app)


# ユーザーモデルの作成 --- (※3)
class User(UserMixin, db.Model):
    # ユーザーID（主キー）
    id = db.Column(db.Integer, primary_key=True)

    # ユーザー名（重複不可・必須）
    username = db.Column(db.String(50), nullable=False, unique=True)

    # パスワード（ハッシュ値を保存）
    # ※25文字は短い → 実務では255くらい推奨
    password = db.Column(db.String(25))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # 投稿者名
    user_name = db.Column(db.String(100))

    # 投稿内容
    contents = db.Column(db.String(100))


# ユーザーを読み込むためのコールバック --- (※4)
# sessionに保存されたuser_idを元にユーザーを復元する
@login_manager.user_loader
def load_user(user_id):
    # user_idは文字列で来るのでintに変換
    return User.query.get(int(user_id))


# ログインユーザー名を保持する変数 --- (※5)
@app.before_request
def set_login_user_name():
    global login_user_name

    # ログインしている場合のみユーザー名をセット
    login_user_name = current_user.username if current_user.is_authenticated else None

    # ⚠️ globalは複数ユーザーでバグる可能性あり
    # → flask.g を使うのが安全


# アカウント登録 --- (※6)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # GET：登録画面表示
    if request.method == "GET":
        return render_template("signup.html")
    
    # POST：登録処理
    elif request.method == "POST":
        # フォームから入力取得
        username = request.form.get('username')
        password = request.form.get('password')

        # パスワードをハッシュ化してUser作成
        user = User(
            username=username,
            password=generate_password_hash(password)
        )

        # DBに追加（まだ確定していない）
        db.session.add(user)

        # DBに保存確定
        db.session.commit()

        # ログイン画面へ
        return redirect('login')
        # ※本来は url_for('login') 推奨


# ログイン --- (※7)
@app.route('/login', methods=['GET', 'POST'])
def login():
    # GET：ログイン画面表示
    if request.method == "GET":
        return render_template("login.html")
    
    # POST：ログイン処理
    elif request.method == "POST":
        # 入力取得
        username = request.form.get('username')
        password = request.form.get('password')

        # ユーザー検索（username一致）
        user = User.query.filter_by(username=username).first()

        # ユーザーが存在＆パスワード一致チェック
        if user and check_password_hash(user.password, password):

            # ログイン状態にする（sessionにuser.id保存）
            login_user(user)

            # トップページへ
            return redirect('/')

        # ⚠️ 失敗時の処理がない（実務では必要）
        # return "ログイン失敗"


# ログアウト --- (※8)
@app.route('/logout')
def logout():
    # セッション削除（ログイン解除）
    logout_user()

    # トップへ
    return redirect('/')

@app.route("/")
def index():
    search_word: str = request.args.get("search_word")

    if search_word is None:
        message_list: list[Message] = Message.query.all()
    else:
        message_list: list[Message] = Message.query.filter(Message.contents.like(f"%{search_word}%")).all()

    return render_template(
        "top.html",
        login_user_name=login_user_name,
        message_list=message_list,
        search_word=search_word,
    )


@app.route("/write", methods=["GET", "POST"])
def write():
    if request.method == "GET":
        return render_template("write.html", login_user_name=login_user_name)

    elif request.method == "POST":
        contents: str = request.form.get("contents")
        user_name: str = request.form.get("user_name")
        new_message = Message(user_name=user_name, contents=contents)
        db.session.add(new_message)
        db.session.commit()

        return redirect(url_for("index"))

@app.route("/update/<int:message_id>", methods=["GET", "POST"])
def update(message_id: int):
    message: Message = Message.query.get(message_id)

    if request.method == "GET":
        return render_template("update.html", login_user_name=login_user_name, message=message)

    elif request.method == "POST":
        message.contents = request.form.get("contents")
        db.session.commit()

        return redirect(url_for("index"))

@app.route("/delete/<int:message_id>")
def delete(message_id: int):
    message: Message = Message.query.get(message_id)
    db.session.delete(message)
    db.session.commit()

    return redirect(url_for("index"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
