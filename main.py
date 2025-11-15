import os
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import boto3
import psycopg2
from psycopg2.extensions import connection as PGConnection
from botocore.exceptions import ClientError

# git config
# git config --global push.autoSetupRemote true

load_dotenv()

# DynamoDB
dynamodb = boto3.resource("dynamodb")
email_table = dynamodb.Table("notification_emails")

# SES
ses = boto3.client("ses")
EMAIL_FROM: str = "warren@testing.com"

# Postgres RDS connection details
DB_HOST: str = os.environ["DB_HOST"]
DB_PORT: str = os.environ.get("DB_PORT", "5432")
DB_USER: str = os.environ["DB_USER"]
DB_PASS: str = os.environ["DB_PASS"]
DB_NAME: str = os.environ["DB_NAME"]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, str]:
    status: Optional[str] = event.get("status")
    item_number: Optional[int] = event.get("item")
    customer_email: Optional[str] = event.get("customer")

    if not status or item_number is None:
        return {"error": "Missing 'status' or 'item' in event"}

    if status != "deactivate":
        return {"message": "No action taken"}

    update_postgres(item_number)

    recipients: List[str] = get_internal_recipients()

    if customer_email:
        recipients.append(customer_email)

    send_email(item_number, recipients)

    return {"message": "OK"}


def update_postgres(item_number: int) -> None:
    conn: PGConnection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE inventory
                    SET status = 'deactivated'
                    WHERE inventory_number = %s
                    """,
                    (item_number,),
                )
    finally:
        conn.close()


def get_internal_recipients() -> List[str]:
    resp: Dict[str, Any] = email_table.get_item(
        Key={"group": "inventory_deactivated"}
    )
    return resp["Item"]["emails"]


def send_email(item_number: int, recipients: List[str]) -> None:
    subject: str = f"Item {item_number} Deactivated"
    body: str = f"Inventory item {item_number} has been deactivated."

    ses.send_email(
        Source=EMAIL_FROM,
        Destination={"ToAddresses": recipients},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )
