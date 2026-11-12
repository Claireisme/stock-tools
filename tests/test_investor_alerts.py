import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

import investor_tracker as tracker
import server


class AlertFeedTest(unittest.TestCase):
    def test_cursor_only_reports_new_records_once(self):
        with tempfile.TemporaryDirectory() as path:
            original = tracker.DB_PATH
            tracker.DB_PATH = Path(path) / 'events.sqlite3'
            http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{http.server_port}/api/investors/alerts'
            def get(suffix=''):
                with urlopen(base + suffix) as response:
                    return json.load(response)
            try:
                tracker.save_events([{'id': 'old', 'observed_at': '2026-01-01'}])
                initial = get()
                self.assertEqual(initial['events'], [])
                tracker.save_events([{'id': 'new', 'observed_at': '2026-01-02'}])
                updates = get('?after=' + str(initial['cursor']))
                self.assertEqual([e['id'] for e in updates['events']], ['new'])
                tracker.save_events([{'id': 'new', 'observed_at': '2026-01-03'}])
                self.assertEqual(get('?after=' + str(updates['cursor']))['events'], [])
            finally:
                http.shutdown()
                http.server_close()
                thread.join()
                tracker.DB_PATH = original


if __name__ == '__main__':
    unittest.main()
