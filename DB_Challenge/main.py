import streamlit as st
import sqlite3
from PIL import Image
import io
from datetime import datetime
import pytz

# ユーザー認証情報
USERS = {
    "hato": "hato",
    "fuku": "fuku",
    "ito": "ito",
    "kasa": "kasa"
}

# データベース接続
conn = sqlite3.connect('image_album.db')
c = conn.cursor()

# テーブルの作成（存在しない場合）
c.execute('''CREATE TABLE IF NOT EXISTS images
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              data BLOB,
              date TEXT)''')

# テーブルに 'user' カラムがない場合は追加
try:
    c.execute("ALTER TABLE images ADD COLUMN user TEXT")
except sqlite3.OperationalError:
    pass  # 'user' カラムが既に存在している場合はスキップ

# ログイン機能
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = None

if not st.session_state["authenticated"]:
    # ログインフォーム
    st.title("ログイン")
    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        if username in USERS and USERS[username] == password:
            st.session_state["authenticated"] = username
            st.success(f"やっほー！、{username} さん！")
            st.rerun()  # ログイン成功後、再描画
        else:
            st.error("ユーザー名またはパスワードが間違っています")
    st.stop()  # ログイン前は止めておく

# ログイン後の処理
if st.session_state["authenticated"]:
    st.title("お写んぽ思い出")
    st.write(f"現在ログイン中のユーザー: {st.session_state['authenticated']}")

    # 画像アップロード、表示の処理を記載
    uploaded_file = st.file_uploader("画像をアップロードしてください", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_binary = buf.getvalue()

        # 現在の日時を取得
        current_utc_time = datetime.now(pytz.utc)
        jst = pytz.timezone('Asia/Tokyo')
        current_jst_time = current_utc_time.astimezone(jst)
        formatted_jst_time = current_jst_time.strftime("%Y-%m-%d %H:%M")

        # データベースに保存
        c.execute("INSERT INTO images (user, data, date) VALUES (?, ?, ?)",
                  (st.session_state["authenticated"], image_binary, current_jst_time))
        conn.commit()
        st.success("画像がアップロードされました！")

    # アルバムの表示
    def fetch_images(user):
        c.execute("SELECT data, date FROM images WHERE user = ? ORDER BY date DESC", (user,))
        return c.fetchall()

    images = fetch_images(st.session_state["authenticated"])

    for img_data, date in images:
        formatted_date = datetime.fromisoformat(date).strftime("%Y-%m-%d %H:%M")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.write(f"日付: {date}")
        with col2:
            image = Image.open(io.BytesIO(img_data))
            st.image(image, use_container_width=True)
        st.divider()

conn.close()