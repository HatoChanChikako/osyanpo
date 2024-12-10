import streamlit as st
import sqlite3
from PIL import Image
import io
from datetime import datetime

# データベース接続
conn = sqlite3.connect('image_album.db')
c = conn.cursor()

# テーブルの作成（存在しない場合）
c.execute('''CREATE TABLE IF NOT EXISTS images
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              data BLOB,
              date TEXT)''')

# 最終更新時刻を取得する関数
def get_last_update_time():
    c.execute("SELECT MAX(date) FROM images")
    return c.fetchone()[0]

# 画像のアップロードと保存
uploaded_file = st.file_uploader("画像をアップロードしてください", type=["png", "jpg", "jpeg"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    image_binary = buf.getvalue()
    
    # 現在の日時を取得
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # データベースに保存
    c.execute("INSERT INTO images (data, date) VALUES (?, ?)",
              (image_binary, current_date))
    conn.commit()
    st.success("画像がアップロードされました！")

# アルバムの表示
st.title("お写んぽ思い出")

@st.cache_data
def fetch_images(_last_update):
    c.execute("SELECT data, date FROM images ORDER BY date DESC")
    return c.fetchall()

# 最終更新時刻を取得
last_update = get_last_update_time()

# データベースから画像を取得
images = fetch_images(last_update)

# 画像を表示
for img_data, date in images:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write(f"日付: {date}")
    with col2:
        image = Image.open(io.BytesIO(img_data))
        st.image(image, use_container_width=True)
    st.divider()

conn.close()