# Python 3.12の軽量イメージを使用
FROM python:3.12-slim

# 作業ディレクトリを作成
WORKDIR /app

# 依存関係をコピー
COPY requirements.txt ./

# 依存関係をインストール（キャッシュを最小化）
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# コンテナ起動時のコマンド（8000ポートで FastAPI 実行）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

