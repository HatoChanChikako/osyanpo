import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv, find_dotenv
from google.cloud import storage
from google.oauth2 import service_account
from google.cloud import vision
from openai import OpenAI
from datetime import datetime
import json
import base64
import io

# API設定
#load_dotenv(find_dotenv())
#os.environ["OPENAI_API_KEY"] = os.getenv("API_KEY")
API_KEY = st.secrets["API_KEY"]


#サービスアカウントキーの設定
##環境変数から"SERVICE_ACCOUNT_KEY"という名前の値を取得
encoded_key = os.getenv("SERVICE_ACCOUNT_KEY")
##不要な最初の2文字と最後の一文字を削除
encoded_key = str(encoded_key)[2:-1]
##デコーディング
original_service_key= json.loads(base64.b64decode(encoded_key).decode('utf-8'))
##上記original_service_keyをcredentialsという変数に代入
credentials = service_account.Credentials.from_service_account_info(original_service_key)


# 画像解析結果をキャッシュする関数
def analyze_image(image_content):
    # Vision APIクライアントを初期化
    client = vision.ImageAnnotatorClient()

    # Vision APIで解析する画像を作成
    image = vision.Image(content=image_content)

    # ラベル検出
    label_response = client.label_detection(image=image)
    labels = label_response.label_annotations

    # オブジェクト検出
    object_response = client.object_localization(image=image)
    objects = object_response.localized_object_annotations

    # ドミナントカラーの検出
    color_response = client.image_properties(image=image)
    colors = color_response.image_properties_annotation.dominant_colors.colors

    return labels, objects, colors

# Streamlit UI
st.title("Google Cloud Vision API Demo")
st.write("画像をアップロードして解析結果を確認できます。")

# 画像アップローダー
uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # アップロードされた画像を表示
    st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)

    # 「結果を表示する」ボタン
    if st.button("結果を表示する"):
        # 画像データを読み込む
        image_content = uploaded_file.read()

        # Vision APIで画像を解析
        labels, objects, colors = analyze_image(image_content)

        # ラベルを表示
        st.subheader("Labels (ラベル)")
        for label in labels:
            st.write(f"{label.description} (confidence: {label.score:.2f})")

        # オブジェクトを表示
        st.subheader("Objects (オブジェクト)")
        for obj in objects:
            st.write(f"{obj.name} (confidence: {obj.score:.2f})")

        # 色を表示
        st.subheader("Dominant Colors (割合の多い色)")
        for color_info in colors:
            color = color_info.color
            st.write(f"RGB: ({int(color.red)}, {int(color.green)}, {int(color.blue)}) (confidence: {color_info.pixel_fraction:.2f})")


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

def score_with_gpt(theme, gcv_results):
    """GPT-4で画像の採点とフィードバックを生成"""
    prompt = f"""
    以下の画像分析結果に基づいて、テーマ「{theme}」への適合度を100点満点で採点し、
    ユーザーがさらに散歩をしながら写真を撮りたくなるような、モチベーションが上がるポジティブなフィードバックを一文で付けてください。
    ユーザーが未就学児である可能性も考慮して、わかりやすい日本語で表現してください。
    
    画像分析結果:
    ラベル: {', '.join([label.description for label in gcv_results.label_annotations])}
    検出オブジェクト: {', '.join([obj.name for obj in gcv_results.localized_object_annotations])}
    ドミナントカラー: {', '.join([colors.name for color in gcv_results.localized_object_annotations])}
    
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
    
    return response.choices[0].message.content

def main():
    st.title("📸 お題チェッカー Pro")
    
    # 現在のお題を設定
    current_theme = "海辺の風景"
    st.info(f"📝 今日のお題: {current_theme}")
    
    # ファイルアップロード
    uploaded_file = st.file_uploader("画像をアップロードしてください", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        # 画像を表示
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた画像", use_container_width=True)
        
        # 判定ボタン
        if st.button("この写真を使う"):
            with st.spinner("AIが画像を分析中..."):
                # Google Cloud Vision APIで分析
                gcv_results = get_image_analysis(uploaded_file)
                
                # GPTで採点とフィードバック生成
                result = eval(score_with_gpt(current_theme, gcv_results))
                
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