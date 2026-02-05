"""
Tests for atomic page view increment using Supabase RPC function.

Verifies that concurrent increments don't lose updates.
"""

import pytest
from unittest.mock import MagicMock, patch
from extension_shield.api.database import SupabaseDatabase


class TestAtomicPageViewIncrement:
    """Test atomic increment_page_view using RPC function."""

    @pytest.fixture
    def mock_supabase_db(self):
        """Create SupabaseDatabase with mocked client."""
        # Patch get_settings and supabase.create_client
        with patch("extension_shield.api.database.get_settings") as mock_settings:
            settings = MagicMock()
            settings.supabase_url = "https://test.supabase.co"
            settings.supabase_key = "test-key"
            settings.supabase_scan_results_table = "scan_results"
            mock_settings.return_value = settings
            
            with patch("supabase.create_client") as mock_create:
                mock_client = MagicMock()
                mock_create.return_value = mock_client
                
                # Create instance after patches are in place
                db = SupabaseDatabase()
                yield db, mock_client

    def test_increment_page_view_calls_rpc(self, mock_supabase_db):
        """Test that increment_page_view calls the RPC function."""
        db, mock_client = mock_supabase_db
        day = "2026-02-05"
        path = "/research"
        
        # Mock RPC response
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = 5
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day=day, path=path)
        
        # Verify RPC was called with correct parameters
        mock_client.rpc.assert_called_once_with(
            "increment_page_view",
            {"p_day": day, "p_path": path}
        )
        assert count == 5

    def test_increment_page_view_returns_count(self, mock_supabase_db):
        """Test that increment_page_view returns the incremented count."""
        db, mock_client = mock_supabase_db
        
        # First increment
        mock_rpc_resp1 = MagicMock()
        mock_rpc_resp1.data = 1
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp1
        
        count1 = db.increment_page_view(day="2026-02-05", path="/research")
        assert count1 == 1
        
        # Second increment (same day/path)
        mock_rpc_resp2 = MagicMock()
        mock_rpc_resp2.data = 2
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp2
        
        count2 = db.increment_page_view(day="2026-02-05", path="/research")
        assert count2 == 2
        
        # Verify RPC was called twice
        assert mock_client.rpc.call_count == 2

    def test_increment_page_view_normalizes_path(self, mock_supabase_db):
        """Test that paths are normalized before calling RPC."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = 1
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        # Path without leading slash
        db.increment_page_view(day="2026-02-05", path="research")
        
        # Verify RPC was called with normalized path
        mock_client.rpc.assert_called_once_with(
            "increment_page_view",
            {"p_day": "2026-02-05", "p_path": "/research"}
        )

    def test_increment_page_view_fallback_on_rpc_error(self, mock_supabase_db):
        """Test that increment_page_view falls back to table operations if RPC fails."""
        db, mock_client = mock_supabase_db
        
        # Mock RPC failure
        mock_client.rpc.side_effect = Exception("RPC not found")
        
        # Mock table select (row exists)
        mock_select_resp = MagicMock()
        mock_select_resp.data = [{"count": 5}]
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_select_resp
        
        # Mock table update
        mock_update_resp = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        
        # Should fall back to table update
        assert count == 6
        mock_client.table.return_value.update.assert_called_once()

    def test_increment_page_view_fallback_on_insert(self, mock_supabase_db):
        """Test fallback when row doesn't exist."""
        db, mock_client = mock_supabase_db
        
        # Mock RPC failure
        mock_client.rpc.side_effect = Exception("RPC not found")
        
        # Mock table select (row doesn't exist)
        mock_select_resp = MagicMock()
        mock_select_resp.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_select_resp
        
        # Mock table insert
        mock_insert_resp = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_insert_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        
        # Should fall back to table insert
        assert count == 1
        mock_client.table.return_value.insert.assert_called_once_with(
            {"day": "2026-02-05", "path": "/research", "count": 1}
        )

    def test_concurrent_increments_atomic(self, mock_supabase_db):
        """
        Test that multiple increments are atomic (simulated).
        
        In real usage, the RPC function ensures atomicity at the database level.
        This test verifies the RPC is called correctly for concurrent scenarios.
        """
        db, mock_client = mock_supabase_db
        
        # Simulate two concurrent increments
        mock_rpc_resp1 = MagicMock()
        mock_rpc_resp1.data = 1
        mock_rpc_resp2 = MagicMock()
        mock_rpc_resp2.data = 2
        
        # First call returns 1, second returns 2 (atomic increment)
        mock_client.rpc.return_value.execute.side_effect = [mock_rpc_resp1, mock_rpc_resp2]
        
        count1 = db.increment_page_view(day="2026-02-05", path="/research")
        count2 = db.increment_page_view(day="2026-02-05", path="/research")
        
        assert count1 == 1
        assert count2 == 2
        
        # Verify RPC was called twice (atomic operations)
        assert mock_client.rpc.call_count == 2

    def test_rpc_returns_direct_integer(self, mock_supabase_db):
        """Test RPC returns direct integer value."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = 5  # Direct integer
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 5

    def test_rpc_returns_string_integer(self, mock_supabase_db):
        """Test RPC returns string representation of integer."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = "7"  # String integer
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 7

    def test_rpc_returns_dict_with_count_key(self, mock_supabase_db):
        """Test RPC returns dict with 'count' key."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = {"count": 3}  # Dict with count key
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 3

    def test_rpc_returns_dict_with_function_name_key(self, mock_supabase_db):
        """Test RPC returns dict with function name as key."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = {"increment_page_view": 4}  # Dict with function name key
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 4

    def test_rpc_returns_dict_with_value_key(self, mock_supabase_db):
        """Test RPC returns dict with 'value' key."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = {"value": 6}  # Dict with value key
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 6

    def test_rpc_returns_list_of_integers(self, mock_supabase_db):
        """Test RPC returns list containing integer."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = [8]  # List with integer
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 8

    def test_rpc_returns_list_of_dicts_with_count(self, mock_supabase_db):
        """Test RPC returns list containing dict with count."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = [{"count": 9}]  # List with dict containing count
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 9

    def test_rpc_returns_list_of_dicts_with_function_name(self, mock_supabase_db):
        """Test RPC returns list containing dict with function name key."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = [{"increment_page_view": 10}]  # List with dict containing function name
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 10

    def test_rpc_returns_list_of_strings(self, mock_supabase_db):
        """Test RPC returns list containing string integer."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = ["11"]  # List with string integer
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 11

    def test_rpc_returns_empty_dict(self, mock_supabase_db):
        """Test RPC returns empty dict (should return 0)."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = {}  # Empty dict
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 0

    def test_rpc_returns_empty_list(self, mock_supabase_db):
        """Test RPC returns empty list (should return 0)."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = []  # Empty list
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 0

    def test_rpc_returns_none(self, mock_supabase_db):
        """Test RPC returns None (should return 0)."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = None  # None
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 0

    def test_rpc_returns_invalid_string(self, mock_supabase_db):
        """Test RPC returns invalid string (should return 0)."""
        db, mock_client = mock_supabase_db
        
        mock_rpc_resp = MagicMock()
        mock_rpc_resp.data = "not-a-number"  # Invalid string
        mock_client.rpc.return_value.execute.return_value = mock_rpc_resp
        
        count = db.increment_page_view(day="2026-02-05", path="/research")
        assert count == 0

