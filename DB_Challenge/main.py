import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv, find_dotenv
from google.cloud import storage, vision
from google.oauth2 import service_account
from openai import OpenAI
from datetime import datetime
import json
import base64
import io
import sqlite3
from datetime import datetime
import pytz


#-----------------------------------------------------------------
#環境変数の設定
#-----------------------------------------------------------------

# API設定（羽藤のOpenai API Keyを使用）
load_dotenv(find_dotenv())
API_KEY = st.secrets["API_KEY"]

#サービスアカウントキーの設定（羽藤のGoogle Cloudサービスアカウントキーを使用）
##環境変数から"SERVICE_ACCOUNT_KEY"という名前の値を取得
encoded_key = st.secrets["SERVICE_ACCOUNT_KEY"] 
##不要な最初の2文字と最後の一文字を削除                                          
encoded_key = str(encoded_key)[2:-1]        
##TOML形式をJSON形式に変換                                            
original_service_key= json.loads(base64.b64decode(encoded_key).decode('utf-8')) 
##上記original_service_keyをcredentialsという変数に代入          
credentials = service_account.Credentials.from_service_account_info(original_service_key) 

#-----------------------------------------------------------------
#定義された関数群
#-----------------------------------------------------------------

#お題を生成する関数
def topic_generation(level):
    prompt = f"""
    以下の{level}の対象者が散歩中に撮影できる、シンプルなお題をランダムにひとつ生成してください。

    レベル1：
    対象者「未就学児」
    表示形式「ひらがな」
    例「くるま」「ねこ」

    レベル2：
    対象者「小学生」
    表示形式「小学校で習う漢字のみ使用」
    例「赤い車」「黒い猫」

    レベル3：
    対象者「中学生以上」
    表示形式「日本語」
    例「緊急車両」「首輪をつけた黒い猫」

    回答は以下のJSON形式で返してください:
    {{"Thema": "生成されたお題"}}

    """
    #OpenAIの機能を呼び出す
    client = OpenAI(api_key=API_KEY)                                 
    response = client.chat.completions.create(                       #生成されたお題をJSON形式の文字列からPythonの辞書に変換
        model="gpt-4o-mini",
        messages=[
        {"role": "system", "content": "あなたは子供の成長を願う母親です。"},
        {'role': 'user', 'content': prompt }],
        temperature=1.0                   #生成される回答のクリエイティビティのレベル（1に近づくほど質問に対して様々な回答をする）
        )
    
    result = json.loads(response.choices[0].message.content.strip())  #生成されたお題をJSON形式の文字列からPythonの辞書に変換
    return result 


# 画像解析結果をキャッシュする関数
def get_image_analysis(image_file):
    """Google Cloud Vision APIで画像を分析"""
    # Vision APIクライアントを初期化
    client = vision.ImageAnnotatorClient(credentials=credentials)  

    # 画像をバイト列に変換
    content = image_file.getvalue()
    image = vision.Image(content=content)

    # 複数の分析を実行
    response = client.annotate_image({
        'image': image,
        'features': [
            {'type_': vision.Feature.Type.LABEL_DETECTION},
            {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
            {'type_': vision.Feature.Type.IMAGE_PROPERTIES},
        ]
    })
    
    return response


# お題と写真の合致度を点数化し、フィードバックコメントを返す関数
def score_with_gpt(thema_data, gcv_results):
    """GPT-4で画像の採点とフィードバックを生成"""
    prompt = f"""
    以下の画像分析結果に基づいて、テーマ「{thema_data}」への適合度を100点満点で採点し、
    ユーザーがさらに散歩をしながら写真を撮りたくなるような、モチベーションが上がるポジティブなフィードバックを一文で付けてください。
    ユーザーが未就学児である可能性も考慮して、わかりやすい日本語で表現してください。
    
    画像分析結果:
    ラベル: {', '.join([label.description for label in gcv_results.label_annotations])}
    検出オブジェクト: {', '.join([obj.name for obj in gcv_results.localized_object_annotations])}
    
    回答は以下のJSON形式で返してください:
    {{"score": 数値, "feedback": "メッセージ"}}
    """

    client = OpenAI(api_key=API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは写真審査の専門家です。"},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )
    
    return response.choices[0].message.content.strip()


#-----------------------------------------------------------------
#フロントエンドを含むmain関数
#-----------------------------------------------------------------

def main():

    #-----------------------------
    #CSSスタイルの定義
    #-----------------------------
    st.markdown(
        """       
        <style>

        body {
            background-color: ivory;   /* アプリ全体の背景色をivoryに設定 */
        }
        [data-testid="stAppViewContainer"] {
            background-color: ivory;   /* Streamlitのメインコンテナの背景色も同じivoryに設定 */
        }
        [data-testid="stHeader"] {
            background: rgba(0, 0, 0, 0); /*Streamlitのヘッダー部分を透明に設定（rgba(0,0,0,0)は完全な透明）*/
        }
        .custom-title {
            font-size: 2.5rem;               /* フォントサイズを2.5倍に */
            font-family: Arial, sans-serif;  /* フォントをArialに、なければsans-serif */
            color: peru !important;          /* 文字色をperuに */
            text-align: center;              /* 文字を中央揃えに */
        }
        .custom-subtitle {
            font-size: 1.5rem;               /* 標準サイズのフォント */
            color: peru !important;          /* 文字色をperuに */
            text-align: center;              /* 文字を中央揃えに */
            margin-top: -10px;               /* 上の余白を-10px（上の要素に近づける） */
        }
        .custom-bold {
            font-weight: bold;               /* 文字を太字に */
            font-size: 1.2rem;               /* フォントサイズを1.5倍に */
            margin-bottom: 10px;             /* 下に10pxの余白 */
        }
        .custom-list {
            line-height: 1.4;                /* 行の高さを1.4倍に */
            padding-left: 20px;              /* 左側に20pxの余白 */
        }
        footer {
            text-align: center;              /* フッターのテキストを中央揃え */
            margin-top: 2rem;                /* 上に2remの余白 */
            font-size: 0.8rem;               /* フォントサイズを0.8倍に */
            color: gray !important;          /* 文字色をグレーに */
        }
        /* タブを中央揃えにする */
        div[data-testid="stHorizontalBlock"] {
            display: flex;                   /* フレックスボックスレイアウトを使用 */
            justify-content: center;         /* 中央揃えに */
        }
        /* タブの選択時の色を変更 */
        div[data-testid="stHorizontalBlock"] button:focus {
            background-color: #20b2aa;       /* 選択時の背景色を青緑に */
            color: red !important;           /* 文字色を赤に（強制的に）*/
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    #--------------------------------------
    #タイトル、タブの設定とセッションの初期化
    #--------------------------------------

    # アプリのタイトル画像の表示
    title_image = "./img/title.png"
    st.image(title_image) 

    # タブを作成
    tab1, tab2, tab3, tab4 = st.tabs(["トップ", "使い方", "思い出", "お問い合わせ"])

    #セッション状態の初期化
    if "thema_data" not in st.session_state:
        st.session_state.thema_data = None

    #--------------------------------------
    #トップタブ
    #--------------------------------------

    with tab1:
        st.markdown('<h2 class="custom-subtitle">さあ、探しに出かけよう！</h2>', unsafe_allow_html=True)
        st.markdown('<p class="custom-subtitle">あなたが気付いていない新しい発見に出会えるかも？！</p>', unsafe_allow_html=True)

        # Walking man 画像を表示
        image_path = os.path.join("img", "walking_man.png") 
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.error("画像が見つかりません。ファイルパスを確認してください。")


        #--------------------------------------
        #データベース
        #--------------------------------------
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


        #--------------------------------------
        #ログイン
        #--------------------------------------
        # ユーザー認証情報
        USERS = {
            "hato": "hato",
            "fuku": "fuku",
            "ito": "ito",
            "kasa": "kasa"
        }

        # ログイン機能
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = None

        if not st.session_state["authenticated"]:
            # ログインフォーム
            st.markdown('<h2 class="custom-title">ログイン</h2>', unsafe_allow_html=True)
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
            st.markdown(f'<h2 class="custom-subtitle">やっほー！  {st.session_state["authenticated"]}さん！</h2>', unsafe_allow_html=True)

        #--------------------------------------
        #レベルの選択
        #--------------------------------------
        # セレクトボックスからレベルを選択
        level = st.selectbox(
        label="レベルをえらんでね",
        options= ["レベル1（ちいさなこども）", "レベル2（しょうがくせい）", "レベル3（中学生以上）"],
        help='このアプリを使う人のレベルを選択してください',
        )

        #--------------------------------------
        #お題生成
        #--------------------------------------
        # ボタンクリックでお題を生成
        if st.button("おだいをGET"):
            with st.spinner("かんがえちゅう…📷"):
                try:
                    st.session_state.thema_data = topic_generation(level)
                    if "Thema" in st.session_state.thema_data:
                        st.success(f"きょうのおだい: **{st.session_state.thema_data['Thema']}**")
                    else:
                        st.error("しっぱい！")
                except Exception as e:
                    st.error(f"エラーがはっせい！: {str(e)}")

        #--------------------------------------
        #写真アップロード
        #--------------------------------------
        # ドラッグ＆ドロップで写真をアップロード
        uploaded_file = st.file_uploader("写真をアップロードしてね", type=['jpg', 'jpeg', 'png'])

        if uploaded_file is not None:
            # 画像を表示
            image = Image.open(uploaded_file)
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            image_binary = buf.getvalue()
            st.image(image, use_container_width=True)

            st.session_state["uploaded_image"] = image_binary
            st.success("写真がアップロードされたよ！")

        #--------------------------------------
        #お題と写真の合致度の判定
        #--------------------------------------
        # 判定ボタン
        if st.button("この写真にきめた！"):
            if "thema_data" not in st.session_state or st.session_state.thema_data is None:
                st.error("先に「おだいをGET」ボタンをおしておだいをみてね")
                st.stop()

            if "uploaded_image" not in st.session_state or st.session_state["uploaded_image"] is None:
                st.error("写真をアップロードしてからボタンを押してね")
                st.stop()

            with st.spinner("AIが写真をかくにんちゅう..."):
                # Google Cloud Vision APIで分析
                gcv_results = get_image_analysis(io.BytesIO(st.session_state["uploaded_image"]))

                # GPTで採点とフィードバック生成
                result = json.loads(score_with_gpt(st.session_state.thema_data["Thema"], gcv_results))

                # 結果表示
                score = result['score']
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown(f"### 点数: {score} / 100")

                # スコアに応じて色を変える
                if score >= 80:
                    st.balloons()
                    st.success(result['feedback'])
                elif score >= 60:
                    st.warning(result['feedback'])
                else:
                    st.error(result['feedback'])

                current_utc_time = datetime.now(pytz.utc)
                jst = pytz.timezone('Asia/Tokyo')
                current_jst_time = current_utc_time.astimezone(jst)

                c.execute("INSERT INTO images (user, data, date) VALUES (?, ?, ?)",
                          (st.session_state["authenticated"], st.session_state["uploaded_image"], current_jst_time))
                conn.commit()
                st.success("写真と結果が保存されました！")

                st.session_state["uploaded_image"] = None

        conn.close()
                
                #--------------------------------------
                #画像解析結果の詳細を表示
                #--------------------------------------
                # 分析詳細を折りたたみメニューで表示
                with st.expander("AIがかくにんしたくわしい写真のないよう"):
                    # ラベルを表示
                    st.write("Labels (ラベル)")
                    labels = gcv_results.label_annotations
                    if labels:
                        for label in labels:
                            st.write(f"{label.description} (confidence: {label.score:.2f})")
                    else:
                        st.write("ラベルが検出されませんでした。")

                    # オブジェクトを表示
                    st.write("Objects (オブジェクト)")
                    objects = gcv_results.localized_object_annotations
                    if objects:
                        for obj in objects:
                            st.write(f"{obj.name} (confidence: {obj.score:.2f})")
                    else:
                        st.write("オブジェクトが検出されませんでした。")

                    # 色を表示
                    st.write("Dominant Colors (割合の多い色)")
                    colors = gcv_results.image_properties_annotation.dominant_colors.colors
                    if colors:
                        for color_info in colors:
                            color = color_info.color
                            st.write(
                                f"RGB: ({int(color.red)}, {int(color.green)}, {int(color.blue)}) "
                                f"(confidence: {color_info.pixel_fraction:.2f})"
                            )
                    else:
                        st.write("色の情報がありませんでした。")

    #--------------------------------------
    #使い方タブ
    #--------------------------------------
    with tab2:
        st.markdown('<p class="custom-bold">使い方</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <ul class="custom-list">
            <li>1. おだいをGET！  </li>
            <li>2. お写んぽへ出発！  </li>
            <li>3. おだいを探して、写真をとろう！ </li>  
            <li>4. おだいと同じ写真をアップロードできたら、お写んぽ成功！ </li>
            </ul>
            """,
            unsafe_allow_html=True
        )

        # もちもの
        st.markdown('<p class="custom-bold">持ち物</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <ul class="custom-list">
                <li>お写んぽアプリが入ったスマホ</li>
                <li>新しい発見を見つけるための好奇心</li>
            </ul>
            """,
            unsafe_allow_html=True
        )

    #--------------------------------------
    #思い出タブ（過去の写真の履歴表示）
    #--------------------------------------
    with tab3:
        st.markdown('<p class="custom-bold">おさんぽの思い出</p>', unsafe_allow_html=True)
        # アルバムの表示
        def fetch_images(user):
            c.execute("SELECT data, date FROM images WHERE user = ? ORDER BY date DESC", (user,))
            return c.fetchall()

        images = fetch_images(st.session_state["authenticated"])

        for img_data, date in images:
            formatted_date = datetime.fromisoformat(date).strftime("%Y-%m-%d %H:%M")
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"日付: {formatted_date}")
            with col2:
                image = Image.open(io.BytesIO(img_data))
                st.image(image, use_container_width=True)
            st.divider()

    #--------------------------------------
    #お問い合わせタブタブ
    #--------------------------------------
    with tab4:
        st.markdown('<p class="custom-bold">お問い合わせ</p>', unsafe_allow_html=True)
        st.markdown("以下のフォームに記入してください。")
        with st.form("contact_form"):
            name = st.text_input("名前", "")
            email = st.text_input("メールアドレス", "")
            message = st.text_area("メッセージ", "")
            submitted = st.form_submit_button("送信")
            if submitted:
                if not name or not email:
                    st.error("名前とメールアドレスは必ず書いてください。")
                else:
                    st.success(f"{name} さん、お問い合わせありがとうございます！")

    #--------------------------------------
    #フッター
    #--------------------------------------
    st.markdown(
        """
        <footer>
        © 2024 うなぎのぼり～ず
        </footer>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()