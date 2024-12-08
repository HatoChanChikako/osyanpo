import streamlit as st
from google.cloud import vision
import io
import os 

# 環境変数の設定
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/osyanpo-app-service-account.json'

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