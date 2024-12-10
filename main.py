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


# API設定（羽藤のOpenai API Keyを使用）
load_dotenv(find_dotenv())  #ローカル環境用コード
#API_KEY = os.getenv("API_KEY")  #ローカル環境用コード
API_KEY = st.secrets["API_KEY"] #Streamlit Cloudデプロイ用コード

#サービスアカウントキーの設定（羽藤のGoogle Cloudサービスアカウントキーを使用）
##環境変数から"SERVICE_ACCOUNT_KEY"という名前の値を取得
encoded_key = st.secrets["SERVICE_ACCOUNT_KEY"]
##不要な最初の2文字と最後の一文字を削除
encoded_key = str(encoded_key)[2:-1]
##デコーディング
original_service_key= json.loads(base64.b64decode(encoded_key).decode('utf-8'))
##上記original_service_keyをcredentialsという変数に代入
credentials = service_account.Credentials.from_service_account_info(original_service_key)

def topic_generation(level):
    #お題生成がうまくいかなかったので変更してみました　request_to_gpt→promt(by羽藤)
    prompt = f"""
    以下の{level}の対象者が散歩中に撮影できる、シンプルなお題をランダムにひとつ生成してください。

    レベル1：
    対象者「未就学児」
    表示形式「ひらがな」
    例「くるま/ねこ」

    レベル2：
    対象者「小学生」
    表示形式「小学校で習う漢字のみ使用」
    例「赤い車/黒い猫」

    レベル3：
    対象者「中学生以上」
    表示形式「英語」
    例「緊急車両/首輪をつけた黒い猫」

    回答は以下のJSON形式で返してください:
    {{"Thema": "生成されたお題"}}

    """

    #以下、二行をOpenai API 1.0.0以上対応の記述に修正(by羽藤)
    client = OpenAI(api_key=API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  #モデルの選択要検討（一旦、安くて性能の高い小さなモデルを採用）(by羽藤)
        messages=[
        {"role": "system", "content": "あなたは子供の成長を願う母親です。"},
        {'role': 'user', 'content': prompt }],
        temperature=1.0
        )
    
    #応答
    result = response.choices[0].message.content
    # 以下、eval()はユーザーが任意のコードをプログラムに渡した場合に実行されてしまうため、セキュリティリスクがあるらしい。return resultでもよい？(by羽藤)
    return eval(result)  # JSON形式の文字列を辞書に変換 



def get_image_analysis(image_file):
    """Google Cloud Vision APIで画像を分析"""
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
        model="gpt-4o-mini",  #モデルの選択要検討（一旦、安くて性能の高い小さなモデルを採用）(by羽藤)
        messages=[
            {"role": "system", "content": "あなたは写真審査の専門家です。"},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )
    
    return response.choices[0].message.content



def main():

    st.title("📷 お写んぽアプリ")

    #セッション状態の初期化
    if "thema_data" not in st.session_state:
        st.session_state.thema_data = None

    # レベル選択
    level = st.selectbox(
    "レベルをえらんでね:",
    ["レベル1", "レベル2", "レベル3"],
    help="対象者のレベルを選択してください"
    )


    # ボタンクリックでお題を生成
    if st.button("おだい を GET"):
        with st.spinner("かんがえちゅう…📷"):
            try:
                st.session_state.thema_data = topic_generation(level)
                if "Thema" in st.session_state.thema_data:
                    st.success(f"きょう の おだい: **{st.session_state.thema_data['Thema']}**")
                else:
                    st.error("しっぱい！")
            except Exception as e:
                st.error(f"エラーがはっせい！: {str(e)}")

    
    # ファイルアップロード
    uploaded_file = st.file_uploader("画像をアップロードしてください", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        # 画像を表示
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた画像", use_container_width=True)
        
        # 判定ボタン
        if st.button("この写真を使う"):
            if st.session_state.thema_data is None:
                st.error("先に、「おだい を GET」ボタンをおして おだい をみてね")
                return
            
            with st.spinner("AIが画像を分析中..."):
                # Google Cloud Vision APIで分析
                gcv_results = get_image_analysis(uploaded_file)
                
                # GPTで採点とフィードバック生成
                result = eval(score_with_gpt(st.session_state.thema_data["Thema"], gcv_results))
                
                # 結果表示
                score = result['score']
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown(f"### 点数: {score} / 100")
                
                # スコアに応じて色を変える
                if score >= 80:
                    st.success(result['feedback'])
                elif score >= 60:
                    st.warning(result['feedback'])
                else:
                    st.error(result['feedback'])
                
                # 分析詳細を折りたたみメニューで表示
                with st.expander("AI分析の詳細"):
                    st.write("検出されたラベル:")
                    for label in gcv_results.label_annotations:
                        st.text(f"- {label.description} ({label.score:.2%})")

if __name__ == "__main__":
    main()