import os
import pytest
from unittest.mock import patch, MagicMock

import main


@pytest.fixture(autouse=True)
def set_env():
    os.environ["DB_HOST"] = "test-host"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_USER"] = "test-user"
    os.environ["DB_PASS"] = "test-pass"
    os.environ["DB_NAME"] = "test-db"
    yield


#
# Test: Missing status or item
#
def test_missing_fields():
    event = {"status": "deactivate"}  # missing item
    response = main.lambda_handler(event, None)
    assert response["error"] == "Missing 'status' or 'item' in event"


#
# Test: Status != deactivate
#
def test_status_not_deactivate():
    event = {"status": "activated", "item": 123}
    response = main.lambda_handler(event, None)
    assert response["message"] == "No action taken"


#
# Test: Deactivate flow with internal recipients only
#
@patch("main.ses.send_email")
@patch("main.email_table.get_item")
@patch("main.psycopg2.connect")
def test_deactivate_no_customer(mock_connect, mock_get_item, mock_send_email):
    # Mock DynamoDB response
    mock_get_item.return_value = {
        "Item": {"emails": ["admin@example.com", "ops@example.com"]}
    }

    # Mock psycopg2 connection + cursor context managers
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    event = {"status": "deactivate", "item": 42}
    response = main.lambda_handler(event, None)

    # Assertions
    assert response["message"] == "OK"
    mock_get_item.assert_called_once()

    # Ensure DB update was executed
    mock_cursor.execute.assert_called_once()
    executed_query, params = mock_cursor.execute.call_args[0]
    assert "UPDATE inventory" in executed_query
    assert params == (42,)

    # Ensure SES email called with internal recipients
    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    assert kwargs["Destination"]["ToAddresses"] == [
        "admin@example.com",
        "ops@example.com",
    ]


#
# Test: Deactivate flow with customer email
#
@patch("main.ses.send_email")
@patch("main.email_table.get_item")
@patch("main.psycopg2.connect")
def test_deactivate_with_customer(mock_connect, mock_get_item, mock_send_email):
    mock_get_item.return_value = {
        "Item": {"emails": ["admin@example.com"]}
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    event = {
        "status": "deactivate",
        "item": 77,
        "customer": "customer@example.com",
    }

    response = main.lambda_handler(event, None)

    assert response["message"] == "OK"

    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args

    # Combined list = internal + customer
    assert kwargs["Destination"]["ToAddresses"] == [
        "admin@example.com",
        "customer@example.com",
    ]
