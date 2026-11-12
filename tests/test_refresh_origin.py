import http.client
import os
import threading
import unittest
from unittest.mock import patch

import server


class RefreshOriginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()

    def post(self, host, origin, **extra):
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        conn.putrequest('POST', '/api/investors/refresh', skip_host=True)
        conn.putheader('Host', host)
        if origin is not None:
            conn.putheader('Origin', origin)
        for k, v in extra.items():
            conn.putheader(k.replace('_', '-'), v)
        conn.endheaders()
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status

    def test_direct_same_origin_and_cross_site_rejection(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(server.investor_tracker, 'start_refresh', return_value=True) as refresh:
            self.assertEqual(self.post('localhost:8001', 'http://localhost:8001', Sec_Fetch_Site='same-origin'), 202)
            self.assertEqual(self.post('localhost:8001', 'http://localhost:8002', Sec_Fetch_Site='cross-site'), 403)
            self.assertEqual(self.post('localhost:8001', 'null'), 403)
            self.assertEqual(refresh.call_count, 1)

    def test_configured_public_origin_handles_proxy_rewritten_host(self):
        with patch.dict(os.environ, {'PUBLIC_ORIGIN': 'https://tools.example.com:8443/'}, clear=True), patch.object(server.investor_tracker, 'start_refresh', return_value=True) as refresh:
            self.assertEqual(self.post('127.0.0.1:8001', 'https://tools.example.com:8443', Sec_Fetch_Site='same-origin'), 202)
            self.assertEqual(self.post('127.0.0.1:8001', 'https://tools.example.com:8444'), 403)
            self.assertEqual(self.post('127.0.0.1:8001', 'http://127.0.0.1:8001'), 403)
            self.assertEqual(self.post('127.0.0.1:8001', 'https://attacker.example', X_Forwarded_Host='attacker.example', X_Forwarded_Proto='https'), 403)
            self.assertEqual(self.post('127.0.0.1:8001', 'https://tools.example.com:8443', Sec_Fetch_Site='cross-site'), 403)
            self.assertEqual(refresh.call_count, 1)

    def test_configured_origin_must_be_valid(self):
        with patch.dict(os.environ, {'PUBLIC_ORIGIN': 'https://tools.example.com/path'}, clear=True), patch.object(server.investor_tracker, 'start_refresh', return_value=True) as refresh:
            self.assertEqual(self.post('127.0.0.1:8001', 'https://tools.example.com'), 403)
            self.assertEqual(refresh.call_count, 0)


if __name__ == '__main__':
    unittest.main()
