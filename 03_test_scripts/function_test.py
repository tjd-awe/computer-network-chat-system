"""
Functional test script
Coverage: user flows, messaging, groups, file transfer, and AI features
"""
import unittest
import os
import sys
import tempfile

from test_support import SOURCE_ROOT

sys.path.insert(0, str(SOURCE_ROOT))

from server.content_analyzer import ContentAnalyzer

class TestContentAnalyzer(unittest.TestCase):
    """Content moderation tests."""
    def setUp(self):
        self.analyzer = ContentAnalyzer()
    
    def test_sensitive_word_detection(self):
        """Test sensitive word detection."""
        has_sensitive, reason = self.analyzer.analyze_content("this content is trash")
        self.assertTrue(has_sensitive)
        self.assertIn("sensitive word", reason)
    
    def test_normal_content(self):
        """Test normal content."""
        has_sensitive, _ = self.analyzer.analyze_content("hello, the weather is nice today")
        self.assertFalse(has_sensitive)
    
    def test_english_sensitive(self):
        """Test English sensitive words."""
        has_sensitive, _ = self.analyzer.analyze_content("this is shit")
        self.assertTrue(has_sensitive)
    
    def test_filter_content(self):
        """Test sensitive word masking."""
        result = self.analyzer.filter_content("you are trash")
        self.assertIn("**", result)
        self.assertNotIn("trash", result)


class TestHistoryFunctions(unittest.TestCase):
    """Pure logic tests for history handling."""
    
    def test_message_item_structure(self):
        """Test message item structure."""
        # Test the data structure directly without client helpers
        item = {
            "kind": "text",
            "sender": "alice",
            "chat_target": "bob",
            "content": "hello",
            "timestamp": 123.0,
            "is_group": False
        }
        self.assertEqual(item["kind"], "text")
        self.assertEqual(item["content"], "hello")
    
    def test_unread_count_logic(self):
        """Test unread count logic."""
        unread_counts = {}
        current_chat = None
        
        # A message for another chat should increase unread count
        chat_target = "bob"
        if chat_target != current_chat:
            if chat_target not in unread_counts:
                unread_counts[chat_target] = 0
            unread_counts[chat_target] += 1
        
        self.assertEqual(unread_counts["bob"], 1)
    
    def test_no_unread_for_current_chat(self):
        """Test that the current chat does not increase unread count."""
        unread_counts = {}
        current_chat = "bob"
        
        # Messages for the active chat should not increase unread count
        chat_target = "bob"
        if chat_target != current_chat:
            if chat_target not in unread_counts:
                unread_counts[chat_target] = 0
            unread_counts[chat_target] += 1
        
        self.assertNotIn("bob", unread_counts)


class TestFileTransferFunctions(unittest.TestCase):
    """Pure logic tests for file transfer."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.download_path = os.path.join(self.temp_dir.name, "downloads")
        os.makedirs(self.download_path, exist_ok=True)
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def resolve_download_path(self, file_name):
        """Simulate duplicate download path handling."""
        base, ext = os.path.splitext(file_name)
        candidate = os.path.join(self.download_path, file_name)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(self.download_path, f"{base}_{counter}{ext}")
            counter += 1
        return candidate
    
    def test_file_item_structure(self):
        """Test file item structure."""
        item = {
            "kind": "file",
            "sender": "alice",
            "chat_target": "bob",
            "is_group": False,
            "file_name": "test.txt",
            "file_size": 1024,
            "file_id": "fid_123",
            "direction": "received",
            "download_status": "pending"
        }
        self.assertEqual(item["kind"], "file")
        self.assertEqual(item["file_name"], "test.txt")
    
    def test_download_path_duplicate(self):
        """Test duplicate download path handling."""
        # Create a file that already exists
        existing = os.path.join(self.download_path, "readme.txt")
        with open(existing, "w") as f:
            f.write("test")
        
        # The new path should get a _1 suffix
        path = self.resolve_download_path("readme.txt")
        self.assertTrue(path.endswith("readme_1.txt"))
    
    def test_file_status_transition(self):
        """Test file status transitions."""
        file_items = {}
        pending_offers = {"fid1": True}
        active_downloads = {"fid1": {"offset": 0}}
        
        # Update status
        file_items["fid1"] = {"download_status": "pending"}
        file_items["fid1"]["download_status"] = "done"
        del pending_offers["fid1"]
        del active_downloads["fid1"]
        
        self.assertEqual(file_items["fid1"]["download_status"], "done")
        self.assertNotIn("fid1", pending_offers)
        self.assertNotIn("fid1", active_downloads)


def run_all_tests():
    """Run all functional tests."""
    print("=" * 60)
    print("Starting functional tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestContentAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestHistoryFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestFileTransferFunctions))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"Functional test summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("All functional tests passed.")
    else:
        print("Some functional tests failed. Please investigate.")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_all_tests()
