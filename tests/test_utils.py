"""
Tests for pure-logic utility functions in utils/utils.py.

These tests validate core logic without requiring Windows-specific APIs
or running game-dependent code. We mock cfg for time-dependent tests.
"""

import time
from datetime import datetime, time as dtime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# Must import after conftest.py has set up sys.modules mocks
from utils.utils import (
    calculate_the_teams,
    check_hard_mirror_time,
    check_teams_order,
    get_day_of_week,
)


# =========================================================================
# check_teams_order
# =========================================================================

class TestCheckTeamsOrder:
    """Tests for the team ordering function (pure list transformation).

    Logic: collect non-zero (value, index) pairs, sort by (-value, index),
    assign ranks: largest value gets highest rank (n), ties broken by index.
    """

    @pytest.mark.parametrize(
        "input_list,expected",
        [
            ([3, 0, 2, 0, 1], [3, 0, 2, 0, 1]),  # desc values
            ([5, 4, 3, 2, 1], [5, 4, 3, 2, 1]),  # all desc
            ([0, 0, 0], [0, 0, 0]),                # all zero
            ([0, 5, 0], [0, 1, 0]),                # single non-zero: gets rank 1
            ([2, 2, 1], [3, 2, 1]),                # tie: highest value → highest rank
            ([10, 8, 6], [3, 2, 1]),               # strict desc
            ([], []),                               # empty
            ([-1, 3, -2], [0, 1, 0]),              # negatives treated as zeros
            ([4, -1, 3, 0], [2, 0, 1, 0]),         # mix
        ],
    )
    def test_basic_ordering(self, input_list, expected):
        assert check_teams_order(input_list) == expected

    def test_large_values(self):
        """Check with large values doesn't overflow."""
        result = check_teams_order([1000, 500, 2000])
        assert result == [2, 1, 3]

    def test_all_same_nonzero(self):
        """All non-zero values equal should order by original index."""
        # [5(idx0), 5(idx1), 5(idx2)] → ranks: idx0=3, idx1=2, idx2=1
        assert check_teams_order([5, 5, 5]) == [3, 2, 1]

    def test_preserves_length(self):
        """Result list should match input length."""
        for length in [0, 1, 5, 10]:
            assert len(check_teams_order([0] * length)) == length


# =========================================================================
# get_day_of_week  (timezone-dependent)
# =========================================================================

class TestGetDayOfWeek:
    """Tests for get_day_of_week which returns KST-based weekday (1=Mon..7=Sun).

    Key behavior:
    - Returns isoweekday() of Seoul time
    - If hour < 6 (midnight to 6am), counts as PREVIOUS day
    - Special case: Monday before 6am → returns 7 (Sunday)
    """

    def _run_test(self, mock_now: datetime) -> int:
        """Helper: patch utils.utils.datetime and run get_day_of_week."""
        from utils import utils as uu

        class MockDateTime(type(mock_now)):
            @classmethod
            def now(cls, tz=None):
                return mock_now

        with patch.object(uu, "datetime", MockDateTime):
            return get_day_of_week()

    def test_normal_hours_monday(self):
        """Monday 10am → returns 1."""
        assert self._run_test(
            datetime(2026, 7, 6, 10, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Mon
        ) == 1

    def test_monday_before_6am(self):
        """Monday 5am (KST) → still Sunday (7)."""
        assert self._run_test(
            datetime(2026, 7, 6, 5, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Mon 5am
        ) == 7

    def test_monday_6am(self):
        """Monday 6am exactly → Monday (1)."""
        assert self._run_test(
            datetime(2026, 7, 6, 6, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Mon 6am
        ) == 1

    def test_tuesday_before_6am(self):
        """Tuesday 3am → Monday (1)."""
        assert self._run_test(
            datetime(2026, 7, 7, 3, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Tue 3am
        ) == 1

    def test_wednesday_after_6am(self):
        """Wednesday 12pm → Wednesday (3)."""
        assert self._run_test(
            datetime(2026, 7, 8, 12, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Wed
        ) == 3

    def test_sunday_before_6am(self):
        """Sunday 4am → Saturday (6)."""
        assert self._run_test(
            datetime(2026, 7, 12, 4, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Sun 4am
        ) == 6

    def test_sunday_after_6am(self):
        """Sunday 10am → Sunday (7)."""
        assert self._run_test(
            datetime(2026, 7, 12, 10, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Sun 10am
        ) == 7

    def test_thursday_before_6am(self):
        """Thursday 5:30am → Wednesday (3)."""
        assert self._run_test(
            datetime(2026, 7, 9, 5, 30, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # Thu 5:30am
        ) == 3


# =========================================================================
# check_hard_mirror_time  (cfg-dependent)
# =========================================================================

class TestCheckHardMirrorTime:
    """Tests for check_hard_mirror_time.

    Logic: returns True if current time falls between last_auto_change
    and the next Thursday 05:00 KST after last_auto_change.
    """

    # We patch the function's cfg reference as well as datetime
    # to avoid real dependency on module.config

    def _run_test(self, last_change_dt: datetime, now_dt: datetime) -> bool:
        """Helper: patch cfg + datetime and run check_hard_mirror_time."""
        from utils import utils as uu

        class MockDateTime(type(last_change_dt)):
            """Subclass of datetime, only overrides now()."""

            @classmethod
            def now(cls, tz=None):
                return now_dt

        with patch.object(uu, "cfg") as mock_cfg:
            mock_cfg.last_auto_change = last_change_dt.timestamp()
            with patch.object(uu, "datetime", MockDateTime):
                return check_hard_mirror_time()

    def test_exact_threshold_triggered(self):
        """last_change = Wednesday, now = Friday → True (Thursday reset happened)"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 8, 12, 0, 0, tzinfo=seoul),   # Wed
            now_dt=datetime(2026, 7, 10, 12, 0, 0, tzinfo=seoul),          # Fri
        ) is True

    def test_before_thursday_window(self):
        """last_change = Tuesday, now = Wednesday → False (Thursday hasn't passed)"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 7, 12, 0, 0, tzinfo=seoul),   # Tue
            now_dt=datetime(2026, 7, 8, 12, 0, 0, tzinfo=seoul),           # Wed
        ) is False

    def test_after_window_expired(self):
        """last_change = Thursday, now = 3 days later (Sat) → False
        (next Thursday hasn't come yet when last was Thursday itself)"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 9, 12, 0, 0, tzinfo=seoul),   # Thu
            now_dt=datetime(2026, 7, 12, 12, 0, 0, tzinfo=seoul),          # Sat (3 days later)
        ) is False

    def test_last_change_in_future(self):
        """If last_auto_change is in the future → False"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 20, 12, 0, 0, tzinfo=seoul),  # Mon
            now_dt=datetime(2026, 7, 15, 12, 0, 0, tzinfo=seoul),          # Wed
        ) is False

    def test_exact_thursday_after_reset(self):
        """last_change = Wednesday, now = Thursday 05:01 KST → True"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 8, 12, 0, 0, tzinfo=seoul),   # Wed
            now_dt=datetime(2026, 7, 9, 5, 1, 0, tzinfo=seoul),            # Thu 05:01
        ) is True

    def test_exact_thursday_before_reset(self):
        """last_change = Wednesday, now = Thursday 04:59 KST → False"""
        seoul = ZoneInfo("Asia/Seoul")
        assert self._run_test(
            last_change_dt=datetime(2026, 7, 8, 12, 0, 0, tzinfo=seoul),   # Wed
            now_dt=datetime(2026, 7, 9, 4, 59, 0, tzinfo=seoul),           # Thu 04:59
        ) is False


# =========================================================================
# calculate_the_teams  (depends on get_day_of_week)
# =========================================================================

class TestCalculateTheTeams:
    """Tests for calculate_the_teams which returns day-grouped team labels."""

    @patch("utils.utils.get_day_of_week")
    def test_mon_tue(self, mock_get_dow):
        """Monday or Tuesday → '1_2'"""
        for day in [1, 2]:
            mock_get_dow.return_value = day
            assert calculate_the_teams() == "1_2"

    @patch("utils.utils.get_day_of_week")
    def test_wed_thu(self, mock_get_dow):
        """Wednesday or Thursday → '3_4'"""
        for day in [3, 4]:
            mock_get_dow.return_value = day
            assert calculate_the_teams() == "3_4"

    @patch("utils.utils.get_day_of_week")
    def test_fri_sat(self, mock_get_dow):
        """Friday or Saturday → '5_6'"""
        for day in [5, 6]:
            mock_get_dow.return_value = day
            assert calculate_the_teams() == "5_6"

    @patch("utils.utils.get_day_of_week")
    def test_sun(self, mock_get_dow):
        """Sunday → '7'"""
        mock_get_dow.return_value = 7
        assert calculate_the_teams() == "7"

    @patch("utils.utils.get_day_of_week")
    def test_edge_day_8(self, mock_get_dow):
        """Day 8 (if ever returned) → '7'"""
        mock_get_dow.return_value = 8
        assert calculate_the_teams() == "7"
