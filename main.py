#-----------------------------------------------------------------
#必要なライブラリのインポート
#-----------------------------------------------------------------
import streamlit as st
from PIL import Image
import os
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
API_KEY = st.secrets["API_KEY"]

#サービスアカウントキーの設定（羽藤のGoogle Cloudサービスアカウントキーを使用）
##Streamlit CloudのSecretsから"SERVICE_ACCOUNT_KEY"という名前の値を取得
encoded_key = st.secrets["SERVICE_ACCOUNT_KEY"] 
##不要な最初の2文字と最後の一文字を削除                                          
encoded_key = str(encoded_key)[2:-1]        
##Base64形式でエンコードしたデータをデコードし、バイナリデータ化＆UTF-8形式の文字列にし、Pythonのデータに変換                                          
original_service_key= json.loads(base64.b64decode(encoded_key).decode('utf-8')) 
##上記original_service_keyから認証情報を作成し、credentialsという変数に代入
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
    例「いぬ」「くるま」「みどりのはっぱ」「とり」「いし」「はな」「そら」「でんしゃ」「じてんしゃ」「むし」

    レベル2：
    対象者「小学生」
    表示形式「小学校で習う漢字のみ使用」
    例「赤い車」「黒い猫」「木のえだ」「青い空」「土の道」「公園の木」「満ちにある石」「空をとぶ鳥」「すべりだい」「花びら」

    レベル3：
    対象者「中学生以上」
    表示形式「日本語」
    例「緊急車両」「首輪をつけた黒い猫」「歩道の模様」「木々の間から見える空」「花壇の植物」「公園のベンチ」「道端の雑草」「鳥がとまっている電線」「夕日に照らされた建物」「郵便ポスト」

    回答は以下のJSON形式で返してください:
    {{"Thema": "生成されたお題"}}

    """
    #OpenAIの機能を呼び出す
    client = OpenAI(api_key=API_KEY)                                 
    response = client.chat.completions.create(                       
        model="gpt-4o-mini",
        messages=[
        {"role": "system", "content": "あなたは子供の成長を願う母親です。"},
        {'role': 'user', 'content': prompt }],

        #生成される回答のクリエイティビティのレベル（1に近づくほど質問に対して様々な回答をする）
        temperature=1.0          
        )
    
    #生成されたお題をJSON形式の文字列からPythonの辞書に変換
    result = json.loads(response.choices[0].message.content.strip())  

    return result 


# 画像解析結果をキャッシュする関数
def get_image_analysis(image_file):
    """Google Cloud Vision APIで画像を分析"""

    # Vision APIを使うためのクライアントを作成
    client = vision.ImageAnnotatorClient(credentials=credentials)  

    # 画像をコンピューターが扱えるバイト列の形式に変換
    content = image_file.getvalue()
    # Vision APIで扱える形式の画像オブジェクトを作成
    image = vision.Image(content=content)

    # 複数の分析を実行（画像の内容を表すラベルの検出、画像内のオブジェクトの位置を特定、画像の色合いなどの特徴）
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
    #OpenAI APIに対するプロンプト
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
            font-size: 1.2rem;               /* 標準サイズのフォント */
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

    #--------------------------------------
    #トップタブ
    #--------------------------------------

    with tab1:
        st.markdown('<h2 class="custom-subtitle">さあ、出かけよう！</h2>', unsafe_allow_html=True)
        st.markdown('<p class="custom-subtitle">新しい発見に出会えるかも？！</p>', unsafe_allow_html=True)

        # Walking man 画像を表示
        image_path = os.path.join("img", "walking_man.png") 
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.error("画像が見つかりません。ファイルパスを確認してください。")

        #--------------------------------------
        #データベース
        #--------------------------------------
        # データベースに接続し、image_albu.dbという名前のDBファイルを作成あるいは開く
        conn = sqlite3.connect('image_album.db')
        #データベースを操作するためのカーソルを作成
        c = conn.cursor()

        # テーブルの作成（存在しない場合）画像データはBLOB（バイナリデータ）、日付はテキスト型で保存

        c.execute('''CREATE TABLE IF NOT EXISTS images
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data BLOB,
                    date TEXT)''')

        # テーブルに 'user' カラムがない場合はテキスト型で追加
        try:
            c.execute("ALTER TABLE images ADD COLUMN user TEXT")
        # カラムがすでに存在する場合、SQLiteはエラーを発生させるが、
        except sqlite3.OperationalError:
            # 'user' カラムが既に存在している場合はスキップし、処理を継続
            pass  

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


        # セッション状態にauthenticatedが存在しない場合、初期値をNoneに設定
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = None

        # ユーザーが未ログインの場合
        if not st.session_state["authenticated"]:
            # ログインフォーム
            st.markdown('<h2 class="custom-title">ログイン</h2>', unsafe_allow_html=True)
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            
            
            if st.button("ログイン"):
                # 入力されたユーザー名とパスワードが正しいか確認（USERSは事前に定義された辞書型で、ユーザー名とパスワードのペアが格納） 
                if username in USERS and USERS[username] == password:
                    # 認証されるとセッション状態にユーザー名を保存し、処理成功を知らせるメッセージを表示
                    st.session_state["authenticated"] = username
                    st.success(f"やっほー！、{username} さん！")
                    # ログイン成功後、アプリのページを再描画
                    st.rerun()  
                else:
                    st.error("ユーザー名またはパスワードが間違っています")
            # ログイン前の状態では、以降のコードの処理停止
            st.stop()  


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
        #セッション状態にthema_dataがあるか確認し、なければ初期化
        if "thema_data" not in st.session_state:
            st.session_state.thema_data = None

        #セッション状態にuploaded_imageがあるか確認し、なければ初期化
        if "uploaded_image" not in st.session_state:
            st.session_state.uploaded_image = None

        # ボタンクリックでお題を生成
        if st.button("おだいをGET"):
            # ボタンが押されたらスピナー表示
            with st.spinner("かんがえちゅう…📷"):
                # 例外処理（レベルを引数として受けてお題を生成させてセッション状態に保持するが、例外が発生した場合はエラーを返す）
                try:
                    st.session_state.thema_data = topic_generation(level)
                    if "Thema" not in st.session_state.thema_data:
                        st.error("しっぱい！")                        
                except Exception as e:
                    st.error(f"エラーがはっせい！: {str(e)}")


        # お題の表示（セッションに保存されている場合は常に表示）
        if "thema_data" in st.session_state and st.session_state.thema_data and "Thema" in st.session_state.thema_data:
            st.success(f"きょうのおだい: **{st.session_state.thema_data['Thema']}**")


        #--------------------------------------
        #写真アップロード
        #--------------------------------------
        # ドラッグ＆ドロップで写真をアップロード
        uploaded_file = st.file_uploader("写真をアップロードしてね", type=['jpg', 'jpeg', 'png'])
    
        if uploaded_file is not None:

            # アップロードされたファイルを画像として表示
            image = Image.open(uploaded_file)
            # メモリ上にバイナリデータを一時的に保存するためのバッファを作成
            buf = io.BytesIO()
            # 画像をPNG形式でバッファに保存
            image.save(buf, format='PNG')
            # バッファから画像のバイナリデータを取得し、Pythonで扱えるように変換
            image_binary = buf.getvalue()
            st.image(image, use_container_width=True)

            # 変換された画像のバイナリデータをStreamlitのセッション状態に保存
            st.session_state["uploaded_image"] = image_binary

            st.success("写真がアップロードされたよ！")

        #--------------------------------------
        #お題と写真の合致度の判定
        #--------------------------------------
        # 判定ボタン
        if st.button("この写真にきめた！"):

            # お題が生成されていない場合は、お題を生成するように促すして、以降の処理を中止
            if "thema_data" not in st.session_state or st.session_state.thema_data is None:

                st.error("先に「おだいをGET」ボタンをおしておだいをみてね")
                st.stop()

            # 写真がアップされていない場合は、お題を生成するように促すして、以降の処理を中止
            if "uploaded_image" not in st.session_state or st.session_state["uploaded_image"] is None:
                st.error("写真をアップロードしてからボタンを押してね")
                st.stop()

            with st.spinner("AIが写真をかくにんちゅう..."):
                # Google Cloud Vision APIで写真のバイナリデータを分析
                gcv_results = get_image_analysis(io.BytesIO(st.session_state["uploaded_image"]))
         

                # GPTで採点とフィードバック生成し、JSON形式からPythonオブジェクトに変
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

                # 現在の日時を日本時間に変換して取得
                current_utc_time = datetime.now(pytz.utc)
                jst = pytz.timezone('Asia/Tokyo')
                current_jst_time = current_utc_time.astimezone(jst)

                # データベースにユーザー情報、画像データ、日時を保存
                c.execute("INSERT INTO images (user, data, date) VALUES (?, ?, ?)",
                        (st.session_state["authenticated"], st.session_state["uploaded_image"], current_jst_time))
                conn.commit()
                st.success("写真と点数が【思い出】に保存されたよ！")
                

                # アップロードされた画像をクリア   
                st.session_state["uploaded_image"] = None
        
                # データベース接続を終了
                conn.close()

                
                #--------------------------------------
                #画像解析結果の詳細を表示
                #--------------------------------------
                # 分析詳細を折りたたみメニューで表示
                with st.expander("写真のくわしいじょうほう"):

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

        st.markdown('<p class="custom-bold">お写んぽの思い出</p>', unsafe_allow_html=True)
        
        # ユーザーの画像を取得するための関数
        def fetch_images(user):
            # データベースに接続し、image_albu.dbという名前のDBファイルを作成あるいは開く
            conn = sqlite3.connect('image_album.db')
            #データベースを操作するためのカーソルを作成
            c = conn.cursor()    
            # userに一致する画像と日付を取得し、新しい日付順に並び変える
            c.execute("SELECT data, date FROM images WHERE user = ? ORDER BY date DESC", (user,))
            # 検索結果をすべて取得して返す
            return c.fetchall()

        # 現在ログインしているユーザーの画像を取得
        images = fetch_images(st.session_state["authenticated"])

        for img_data, date in images:
            # データベースの日付形式を読みやすい形式に変換
            formatted_date = datetime.fromisoformat(date).strftime("%Y-%m-%d %H:%M")
            # 画面を2つに分割し、左側に日付、右側に画像を表示

            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"日付: {formatted_date}")
            with col2:
                image = Image.open(io.BytesIO(img_data))
                st.image(image, use_container_width=True)

            # 各画像の間に仕切り線を入れる
            st.divider()

            # データベース接続を終了
            conn.close()

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