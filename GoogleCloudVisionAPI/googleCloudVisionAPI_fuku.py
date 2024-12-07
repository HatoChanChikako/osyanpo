# Google Cloud Vision API の実装
# アップロードされた画像をVISION APIで読み込み解析するところまでを実装する
# まずはフォルダ内に画像を置いてそれを読み込む
# 無事に動作確認ができたらユーザーからアップロードされた画像を読み込みにいく実装をする


import os
from google.cloud import vision
import io


# 環境変数の設定
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/fukushimanaoki/Downloads/osyanpo-app-service-account.json'

def analyze_image():
    # Vision APIクライアントを初期化
    client = vision.ImageAnnotatorClient()

    # 画像ファイルを開く
    with io.open('/Users/fukushimanaoki/repos/osyanpo/GoogleCloudVisionAPI/yellow_post.png', 'rb') as image_file:
        content = image_file.read()

    # Vision APIで分析する画像を作成
    image = vision.Image(content=content)

    # ラベル検出を実行
    response = client.label_detection(image=image)
    labels = response.label_annotations

    # 結果を表示
    print('Labels:')
    for label in labels:
        print(f'{label.description} (confidence: {label.score})')

# 関数を実行
analyze_image()