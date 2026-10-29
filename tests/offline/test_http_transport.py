"""Offline transport regression suite. Does not access Freshservice."""
import asyncio
import socket
import threading
import unittest
from unittest.mock import patch

import h11
import httpx


class TransportSecurityTests(unittest.TestCase):
    def test_mcp_registers_tools_without_external_requests(self):
        with patch.dict('os.environ', {
            'FRESHSERVICE_DOMAIN': 'example.invalid',
            'FRESHSERVICE_APIKEY': 'offline-test-only',
        }), patch('socket.create_connection', side_effect=AssertionError('External connection attempted')):
            from freshservice_mcp.server import mcp
            tools = asyncio.run(mcp.list_tools())
            names = {tool.name for tool in tools}
            self.assertIn('create_ticket', names)
            self.assertIn('get_ticket_by_id', names)

    def test_malformed_chunk_terminator_is_rejected(self):
        connection = h11.Connection(h11.SERVER)
        connection.receive_data(b'POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhelloXX0\r\n\r\n')
        with self.assertRaises(h11.RemoteProtocolError):
            while True:
                event = connection.next_event()
                if isinstance(event, h11.EndOfMessage) or event is h11.NEED_DATA:
                    break

    def test_httpx_async_chunked_response_roundtrip(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]
            errors = []
            def serve():
                try:
                    conn, _ = listener.accept()
                    with conn:
                        conn.settimeout(5)
                        received = b''
                        while b'\r\n\r\n' not in received:
                            part = conn.recv(4096)
                            if not part:
                                raise RuntimeError('Client closed without request headers')
                            received += part
                        conn.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n5\r\nhello\r\n0\r\n\r\n')
                except Exception as exc:
                    errors.append(exc)
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            async def request():
                async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
                    response = await client.get(f'http://127.0.0.1:{port}/')
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.text, 'hello')
            asyncio.run(request())
            thread.join(timeout=6)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
