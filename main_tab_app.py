import streamlit as st
import os

# CSSスタイルの追加
st.markdown(
    """
    <style>
    body {
        background-color: #e0ffff;   /* アプリ全体の背景色を薄い水色（#e0ffff）に設定 */
    }
    [data-testid="stAppViewContainer"] {
        background-color: #e0ffff;   /* Streamlitのメインコンテナの背景色も同じ薄い水色に設定 */
    }
    [data-testid="stHeader"] {
        background: rgba(0, 0, 0, 0); /*Streamlitのヘッダー部分を透明に設定（rgba(0,0,0,0)は完全な透明）*/
    }
    .custom-title {
        font-size: 2.5rem;               /* フォントサイズを2.5倍に */
        font-family: Arial, sans-serif;  /* フォントをArialに、なければsans-serif */
        color: #20b2aa !important;         /* 文字色を青緑色に */
        text-align: center;              /* 文字を中央揃えに */
    }
    .custom-subtitle {
        font-size: 1rem;                 /* 標準サイズのフォント */
        color: #333333 !important;       /* 文字色を暗めのグレーに */
        text-align: center;              /* 文字を中央揃えに */
        margin-top: -10px;               /* 上の余白を-10px（上の要素に近づける） */
    }
    .custom-bold {
        font-weight: bold;               /* 文字を太字に */
        font-size: 1.2rem;               /* フォントサイズを1.2倍に */
        margin-bottom: 10px;             /* 下に10pxの余白 */
        color: black !important;         /* 通常時の文字色を黒に（強制的に）*/
    }
    .custom-list {
        line-height: 1.4;                /* 行の高さを1.4倍に */
        padding-left: 20px;              /* 左側に20pxの余白 */
        color: black !important;         /* 通常時の文字色を黒に（強制的に）*/
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
    div[data-testid="stHorizontalBlock"] button {
        color: black !important;         /* 通常時の文字色を黒に（強制的に）*/
    }
    </style>
    """,
    unsafe_allow_html=True
)

# タイトル
st.markdown('<h1 class="custom-title">お写んぽアプリ</h1>', unsafe_allow_html=True)

# 画像のパスを設定
image_path = os.path.join("img", "walking_man.png")

# タブを作成
tab1, tab2, tab3, tab4 = st.tabs(["トップ", "つかいかた", "きろく", "お問い合わせ"])


# Topタブの内容
with tab1:
    st.markdown('<h2 class="custom-subtitle">さあ、探しに出かけよう！</h2>', unsafe_allow_html=True)
    st.markdown('<p class="custom-subtitle">あなたが気付いていない新しい発見に出会えるかも？！</p>', unsafe_allow_html=True)

    # Walking man 画像を表示
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)

    else:
        st.error("画像が見つかりません。ファイルパスを確認してください。")

  
    st.markdown('<p class="custom-bold">お題を決めよう！</p>', unsafe_allow_html=True)
    st.markdown(
        """
        例：  
        - 赤いコーン  
        - 猫のマーク  
        - ハート形の葉っぱ  
        """,
        unsafe_allow_html=True
    )
    
    # お題自動表示ボタン
    if st.button("お題を表示する"):
        import random
        topics = ["赤いコーン", "猫のマーク", "ハート形の葉っぱ", "面白い形の雲", "道路標識", "自転車", "街灯"]
        selected_topic = random.choice(topics)
        st.session_state.selected_topic = selected_topic  # 選んだお題をセッション状態に保存
        st.success(f"お題: {selected_topic}")

    # 写真アップロード   
    st.markdown('<p class="custom-bold">撮影＆アップロード！</p>', unsafe_allow_html=True)
    st.markdown("以下の写真アップロード機能を使用して、お写んぽで撮影した写真を共有してください。")

    # Tab3で選んだお題を表示
    if "selected_topic" in st.session_state:
        st.info(f"選択されたお題: {st.session_state.selected_topic}")
    else:
        st.warning("お題が選択されていません。Tab3でお題を選んでください。")

    # ファイルアップロード機能
    uploaded_file = st.file_uploader("写真をアップロードしてください", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # アップロードされた写真を表示
        st.image(uploaded_file, caption="アップロードした写真", use_container_width=True)
        st.success("写真がアップロードされました！")
        
        # 判定ボタンとマッチ度
        if st.button("判定する"):
            import random
            match_score = random.randint(0, 100)
            st.info(f"マッチ度: {match_score}%")
    else:
        st.info("アップロードする写真を選択してください。")


# 使い方タブの内容
with tab2:
    st.markdown('<p class="custom-bold">使い方</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <ul class="custom-list">
        <li>1. お題を決定！  </li>
        <li>2. お写んぽへ出発！  </li>
        <li>3. お題を探して、写真を撮ろう！ </li>  
        <li>4. 写真をアップして写真と一致したら、お写んぽ成功！ </li>
        </ul>
        """,
        unsafe_allow_html=True
    )

    # もちもの
    st.markdown('<p class="custom-bold">もちもの</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <ul class="custom-list">
            <li>お写んぽアプリが入ったスマホ</li>
            <li>新しい発見を見つけるための好奇心</li>
        </ul>
        """,
        unsafe_allow_html=True
    )


# お問い合わせタブの内容
with tab3:
    st.markdown('<p class="custom-bold">お問い合わせ</p>', unsafe_allow_html=True)
    st.markdown("以下のフォームに必要事項を記入してください。")
    with st.form("contact_form"):
        name = st.text_input("名前", "")
        email = st.text_input("メールアドレス", "")
        message = st.text_area("メッセージ", "")
        submitted = st.form_submit_button("送信")
        if submitted:
            if not name or not email:
                st.error("名前とメールアドレスは必須項目です。")
            else:
                st.success(f"{name} さん、お問い合わせありがとうございます！")

# フッター
st.markdown(
    """
    <footer>
    © 2024 うなぎのぼり～ず
    </footer>
    """,
    unsafe_allow_html=True
)
