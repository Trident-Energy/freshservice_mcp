"""Dependency security regressions; synthetic inputs only, all sockets blocked."""

import base64
import socket
import unittest
from unittest.mock import patch

import jwt


class JWTDependencyTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(
            socket.socket, "connect", side_effect=AssertionError("Network blocked")
        )
        self.network.start()
        self.addCleanup(self.network.stop)
        for name in ("connect_ex",):
            blocker = patch.object(
                socket.socket, name, side_effect=AssertionError("Network blocked")
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        dns = patch("socket.getaddrinfo", side_effect=AssertionError("DNS blocked"))
        dns.start()
        self.addCleanup(dns.stop)

    def test_nested_unverified_payload_uses_documented_error(self):
        def encode(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=")

        token = b".".join(
            [
                encode(b'{"alg":"HS256"}'),
                encode(b"[" * 2000 + b"]" * 2000),
                encode(b"fake-signature"),
            ]
        )
        with self.assertRaises(jwt.DecodeError):
            jwt.decode(token, options={"verify_signature": False})

    def test_unverified_decode_does_not_mutate_reused_options(self):
        options = {"verify_signature": False}
        secret = "offline-test-secret-with-at-least-32-bytes"
        token = jwt.encode({"exp": 1}, secret, algorithm="HS256")
        jwt.decode(token, options=options)
        self.assertEqual(options, {"verify_signature": False})
        options["verify_signature"] = True
        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"], options=options)

    def test_empty_hmac_jwk_is_rejected(self):
        with self.assertRaises(jwt.InvalidKeyError):
            jwt.PyJWK.from_dict({"kty": "oct", "k": "", "alg": "HS256"})

    def test_unknown_critical_header_is_rejected(self):
        secret = "offline-test-secret-with-at-least-32-bytes"
        token = jwt.encode(
            {"sub": "offline-user"},
            secret,
            algorithm="HS256",
            headers={"crit": ["offline-unsupported"], "offline-unsupported": True},
        )
        with self.assertRaises(jwt.InvalidTokenError):
            jwt.decode(token, secret, algorithms=["HS256"])


class FreshserviceDependencyTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(
            socket.socket, "connect", side_effect=AssertionError("Network blocked")
        )
        self.network.start()
        self.addCleanup(self.network.stop)
        for name in ("connect_ex",):
            blocker = patch.object(
                socket.socket, name, side_effect=AssertionError("Network blocked")
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        dns = patch("socket.getaddrinfo", side_effect=AssertionError("DNS blocked"))
        dns.start()
        self.addCleanup(dns.stop)

    def test_anyio_tls_uses_idna2008_hostname(self):
        import asyncio
        import ssl
        from unittest.mock import AsyncMock, Mock
        from anyio.streams.tls import TLSStream

        async def probe():
            with patch.object(
                TLSStream, "_call_sslobject_method", new_callable=AsyncMock
            ):
                stream = await TLSStream.wrap(
                    Mock(), hostname="faß.de", ssl_context=ssl.create_default_context()
                )
            self.assertEqual(stream._ssl_object.server_hostname, "xn--fa-hia.de")

        asyncio.run(probe())

    def test_urlencoded_semicolon_stays_in_value(self):
        from python_multipart import QuerystringParser

        fields = []
        parser = QuerystringParser(
            {"on_field_data": lambda data, start, end: fields.append(data[start:end])}
        )
        parser.write(b"name=one;two")
        parser.finalize()
        self.assertEqual(fields, [b"one;two"])

    def test_idna_rejects_oversized_label_before_context_rules(self):
        import idna

        with patch(
            "idna.core.valid_contextj",
            side_effect=AssertionError("Oversized input reached contextual processing"),
        ):
            with self.assertRaises(idna.IDNAError):
                idna.check_label("a" * 254 + "\u200c")

    def test_mcp_tool_registration_and_mocked_read(self):
        import asyncio
        import httpx

        with (
            patch.dict(
                "os.environ",
                {
                    "FRESHSERVICE_DOMAIN": "example.invalid",
                    "FRESHSERVICE_APIKEY": "offline-test-only",
                },
                clear=True,
            ),
            patch("dotenv.load_dotenv", return_value=False),
        ):
            from freshservice_mcp import server
        requests = []

        def respond(request):
            requests.append(request)
            self.assertEqual(request.url.host, "example.invalid")
            self.assertEqual(request.url.path, "/api/v2/tickets")
            return httpx.Response(
                200,
                json={"tickets": [{"id": 1, "subject": "Synthetic ticket"}]},
                headers={
                    "Link": '<https://example.invalid/api/v2/tickets?page=2>; rel="next"'
                },
            )

        client = httpx.AsyncClient

        async def probe():
            names = {tool.name for tool in await server.mcp.list_tools()}
            self.assertTrue(
                {"create_ticket", "get_ticket_by_id", "get_tickets"} <= names
            )
            with patch.object(
                server.httpx,
                "AsyncClient",
                side_effect=lambda **kwargs: client(
                    transport=httpx.MockTransport(respond), trust_env=False, **kwargs
                ),
            ):
                result = await server.get_tickets(page=1, per_page=10)
            self.assertEqual(result["pagination"]["next_page"], 2)
            self.assertEqual(result["tickets"]["tickets"][0]["id"], 1)

        asyncio.run(probe())
        self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()
