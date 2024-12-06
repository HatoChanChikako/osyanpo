import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv
from google.cloud import vision
from openai import OpenAI
from datetime import datetime

# API設定
load_dotenv()
api_key = os.environ.get("API_KEY")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./osyanpo-f210ffd2f0e0.json"

def get_image_analysis(image_file):
    """Google Cloud Vision APIで画像を分析"""
    client = vision.ImageAnnotatorClient()
    
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
    ユーザーのモチベーションが上がるポジティブなフィードバックを一文で付けてください。
    
    画像分析結果:
    ラベル: {', '.join([label.description for label in gcv_results.label_annotations])}
    検出オブジェクト: {', '.join([obj.name for obj in gcv_results.localized_object_annotations])}
    
    回答は以下のJSON形式で返してください:
    {{"score": 数値, "feedback": "メッセージ"}}
    """
    
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは画像審査の専門家です。"},
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