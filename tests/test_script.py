import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import script


@patch('script.requests.get')
def test_init_glpi_session_success(mock_get, monkeypatch):
    monkeypatch.setattr(script, 'GLPI_API_URL', 'http://glpi')
    monkeypatch.setattr(script, 'GLPI_APP_TOKEN', 'token')
    monkeypatch.setattr(script, 'GLPI_USERNAME', 'user')
    monkeypatch.setattr(script, 'GLPI_PASSWORD', 'pass')

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {'session_token': 'abc123'}
    mock_get.return_value = mock_resp

    token = script.init_glpi_session()
    assert token == 'abc123'


@patch('script.aiohttp.ClientSession')
def test_send_matrix_message_success(mock_client_session, monkeypatch):
    monkeypatch.setattr(script, 'MATRIX_HOMESERVER', 'http://matrix')
    monkeypatch.setattr(script, 'MATRIX_TOKEN', 'token')
    monkeypatch.setattr(script, 'ROOM_ID', 'room')

    session_instance = MagicMock()
    response_mock = AsyncMock()
    response_mock.__aenter__.return_value = response_mock
    response_mock.__aexit__.return_value = False
    response_mock.status = 200
    session_instance.put = MagicMock(return_value=response_mock)
    mock_client_session.return_value.__aenter__.return_value = session_instance

    result = asyncio.run(script.send_matrix_message('hi'))
    assert result is True


@patch('script.aiohttp.ClientSession')
def test_send_matrix_message_failure(mock_client_session, monkeypatch):
    monkeypatch.setattr(script, 'MATRIX_HOMESERVER', 'http://matrix')
    monkeypatch.setattr(script, 'MATRIX_TOKEN', 'token')
    monkeypatch.setattr(script, 'ROOM_ID', 'room')

    session_instance = MagicMock()
    response_mock = AsyncMock()
    response_mock.__aenter__.return_value = response_mock
    response_mock.__aexit__.return_value = False
    response_mock.status = 400
    response_mock.text = AsyncMock(return_value='error')
    session_instance.put = MagicMock(return_value=response_mock)
    mock_client_session.return_value.__aenter__.return_value = session_instance

    result = asyncio.run(script.send_matrix_message('hi'))
    assert result is False
