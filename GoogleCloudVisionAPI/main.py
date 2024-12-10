import streamlit as st
from google.cloud import vision
import io
import os 

# 環境変数の設定
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/osyanpo-app-service-account.json'

# 画像解析結果をキャッシュする関数
def get_image_analysis(image_file):
    """Google Cloud Vision APIで画像を分析"""
    # Vision APIクライアントを初期化
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
        # Vision APIで画像を解析
        response = get_image_analysis(uploaded_file)

        # ラベルを表示
        st.subheader("Labels (ラベル)")
        labels = response.label_annotations
        if labels:
            for label in labels:
                st.write(f"{label.description} (confidence: {label.score:.2f})")
        else:
            st.write("ラベルが検出されませんでした。")

        # オブジェクトを表示
        st.subheader("Objects (オブジェクト)")
        objects = response.localized_object_annotations
        if objects:
            for obj in objects:
                st.write(f"{obj.name} (confidence: {obj.score:.2f})")
        else:
            st.write("オブジェクトが検出されませんでした。")

        # 色を表示
        st.subheader("Dominant Colors (割合の多い色)")
        colors = response.image_properties_annotation.dominant_colors.colors
        if colors:
            for color_info in colors:
                color = color_info.color
                st.write(
                    f"RGB: ({int(color.red)}, {int(color.green)}, {int(color.blue)}) "
                    f"(confidence: {color_info.pixel_fraction:.2f})"
                )
        else:
            st.write("色の情報がありませんでした。")