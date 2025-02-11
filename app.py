from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from urllib.parse import quote_plus #追加

# FastAPI アプリの初期化
app = FastAPI()

# 環境変数をロード
load_dotenv()

# DB 接続情報の設定
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USERNAME"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "ssl_ca": os.getenv("DB_SSL_CERT", "/home/site/wwwroot/DigiCertGlobalRootCA.crt.pem"), 
}

# SQLAlchemy 用の DATABASE_URL
DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('DB_USERNAME')}:{quote_plus(os.getenv('DB_PASSWORD'))}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# CORS の設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース接続を作成
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ DB接続エラー: {err}")
        raise HTTPException(status_code=500, detail=f"データベースに接続できません: {err}")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/product/{code}")
async def get_product(code: str):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM m_product_oyaken WHERE CODE = %s"
        cursor.execute(query, (code,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                "PRD_ID": result["PRD_ID"],
                "CODE": result["CODE"],
                "NAME": result["NAME"],
                "PRICE": result["PRICE"]
            }
        else:
            raise HTTPException(status_code=404, detail="商品がマスタ未登録です")

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"データベースエラー: {err}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {e}")

    finally:
        if conn:
            conn.close()

# ここに新しいtransaction_detailのエンドポイントを追加
@app.get("/transaction/{transaction_id}")
async def get_transaction(transaction_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # トランザクション情報を取得
        query = "SELECT * FROM m_transaction_oyaken WHERE TRD_ID = %s"
        cursor.execute(query, (transaction_id,))
        transaction = cursor.fetchone()

        if not transaction:
            raise HTTPException(status_code=404, detail="トランザクションが見つかりません")

        # トランザクション詳細情報を取得
        query_detail = "SELECT * FROM m_transaction_detail_oyaken WHERE TRD_ID = %s"
        cursor.execute(query_detail, (transaction_id,))
        details = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "transaction": transaction,
            "details": details
        }

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"データベースエラー: {err}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {e}")

    finally:
        if conn:
            conn.close() 

# Pydanticモデルを定義（リクエストデータのバリデーション用）
class TransactionDetail(BaseModel):
    PRD_ID: int
    PRD_CODE: str
    PRD_NAME: str
    PRD_PRICE: int

class TransactionCreate(BaseModel):
    EMP_CD: str
    STORE_CD: str
    POS_NO: str
    TOTAL_AMT: int
    details: List[TransactionDetail]

# 購入処理のエンドポイント
@app.post("/transaction")
async def create_transaction(transaction: TransactionCreate):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # `m_transaction_oyaken` に取引情報を追加
        insert_transaction = """
        INSERT INTO m_transaction_oyaken (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT)
        VALUES (NOW(), %s, %s, %s, %s)
        """
        cursor.execute(insert_transaction, (transaction.EMP_CD, transaction.STORE_CD, transaction.POS_NO, transaction.TOTAL_AMT))
        trd_id = cursor.lastrowid  # 挿入されたTRD_IDを取得

        # `m_transaction_detail_oyaken` に購入した商品情報を追加
        insert_detail = """
        INSERT INTO m_transaction_detail_oyaken (TRD_ID, PRD_ID, PRD_CODE, PRD_NAME, PRD_PRICE)
        VALUES (%s, %s, %s, %s, %s)
        """
        for detail in transaction.details:
            cursor.execute(insert_detail, (trd_id, detail.PRD_ID, detail.PRD_CODE, detail.PRD_NAME, detail.PRD_PRICE))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "購入が完了しました", "transaction_id": trd_id}

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"データベースエラー: {err}")

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {e}")

    finally:
        if conn:
            conn.close()            
