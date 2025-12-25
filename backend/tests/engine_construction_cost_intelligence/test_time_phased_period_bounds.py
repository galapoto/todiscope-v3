"""
Tests for time-phased reporting period boundary calculations.

Tests edge cases for weekly, monthly, and quarterly period boundaries to ensure
correct handling of month/year transitions and boundary conditions.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.app.engines.construction_cost_intelligence.time_phased.reporter import _get_period_bounds


class TestWeeklyPeriodBounds:
    """Test weekly period boundary calculations."""

    def test_weekly_start_of_week_monday(self) -> None:
        """Test weekly period starting on Monday."""
        date = datetime(2024, 1, 1, 10, 30, 45)  # Monday, Jan 1, 2024
        start, end = _get_period_bounds(date, "weekly")
        
        assert start.weekday() == 0  # Monday
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        
        assert end.weekday() == 6  # Sunday
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59
        
        # Verify start is Monday of the week
        assert start.date() == datetime(2024, 1, 1).date()
        # Verify end is Sunday of the week
        assert end.date() == datetime(2024, 1, 7).date()

    def test_weekly_end_of_week_sunday(self) -> None:
        """Test weekly period ending on Sunday."""
        date = datetime(2024, 1, 7, 15, 20, 30)  # Sunday, Jan 7, 2024
        start, end = _get_period_bounds(date, "weekly")
        
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert start.date() == datetime(2024, 1, 1).date()
        assert end.date() == datetime(2024, 1, 7).date()

    def test_weekly_mid_week(self) -> None:
        """Test weekly period in middle of week."""
        date = datetime(2024, 1, 3, 12, 0, 0)  # Wednesday, Jan 3, 2024
        start, end = _get_period_bounds(date, "weekly")
        
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert start.date() == datetime(2024, 1, 1).date()
        assert end.date() == datetime(2024, 1, 7).date()

    def test_weekly_cross_month_boundary(self) -> None:
        """Test weekly period crossing month boundary."""
        # January 29, 2024 is a Monday, week ends Feb 4
        date = datetime(2024, 1, 31, 10, 0, 0)  # Wednesday, Jan 31, 2024
        start, end = _get_period_bounds(date, "weekly")
        
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert start.date() == datetime(2024, 1, 29).date()  # Monday, Jan 29
        assert end.date() == datetime(2024, 2, 4).date()  # Sunday, Feb 4

    def test_weekly_cross_year_boundary(self) -> None:
        """Test weekly period crossing year boundary."""
        # December 30, 2024 is a Monday, week ends Jan 5, 2025
        date = datetime(2024, 12, 31, 10, 0, 0)  # Tuesday, Dec 31, 2024
        start, end = _get_period_bounds(date, "weekly")
        
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert start.date() == datetime(2024, 12, 30).date()  # Monday, Dec 30
        assert end.date() == datetime(2025, 1, 5).date()  # Sunday, Jan 5, 2025


class TestMonthlyPeriodBounds:
    """Test monthly period boundary calculations."""

    def test_monthly_start_of_month(self) -> None:
        """Test monthly period starting on first day."""
        date = datetime(2024, 1, 1, 10, 30, 45)
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert start.month == 1
        assert start.year == 2024
        assert start.hour == 0
        assert start.minute == 0
        
        assert end.day == 31  # January has 31 days
        assert end.month == 1
        assert end.year == 2024
        assert end.hour == 23
        assert end.minute == 59

    def test_monthly_end_of_month(self) -> None:
        """Test monthly period ending on last day."""
        date = datetime(2024, 1, 31, 15, 20, 30)
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert end.day == 31
        assert end.month == 1

    def test_monthly_mid_month(self) -> None:
        """Test monthly period in middle of month."""
        date = datetime(2024, 1, 15, 12, 0, 0)
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert end.day == 31
        assert end.month == 1

    def test_monthly_february_leap_year(self) -> None:
        """Test monthly period for February in leap year."""
        date = datetime(2024, 2, 15, 10, 0, 0)  # 2024 is a leap year
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert start.month == 2
        assert end.day == 29  # February has 29 days in leap year
        assert end.month == 2

    def test_monthly_february_non_leap_year(self) -> None:
        """Test monthly period for February in non-leap year."""
        date = datetime(2023, 2, 15, 10, 0, 0)  # 2023 is not a leap year
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert end.day == 28  # February has 28 days in non-leap year
        assert end.month == 2

    def test_monthly_30_day_month(self) -> None:
        """Test monthly period for 30-day month."""
        date = datetime(2024, 4, 15, 10, 0, 0)  # April has 30 days
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert end.day == 30
        assert end.month == 4

    def test_monthly_december(self) -> None:
        """Test monthly period for December."""
        date = datetime(2024, 12, 15, 10, 0, 0)
        start, end = _get_period_bounds(date, "monthly")
        
        assert start.day == 1
        assert start.month == 12
        assert end.day == 31
        assert end.month == 12
        assert end.year == 2024  # Should not roll over to next year


class TestQuarterlyPeriodBounds:
    """Test quarterly period boundary calculations."""

    def test_quarterly_q1_start(self) -> None:
        """Test quarterly period for Q1 start."""
        date = datetime(2024, 1, 15, 10, 0, 0)  # Q1: Jan-Mar
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 1
        assert start.day == 1
        assert start.year == 2024
        
        assert end.month == 3
        assert end.day == 31  # March has 31 days
        assert end.year == 2024

    def test_quarterly_q1_end(self) -> None:
        """Test quarterly period for Q1 end."""
        date = datetime(2024, 3, 31, 10, 0, 0)  # Q1: Jan-Mar
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 1
        assert end.month == 3
        assert end.day == 31

    def test_quarterly_q2(self) -> None:
        """Test quarterly period for Q2."""
        date = datetime(2024, 5, 15, 10, 0, 0)  # Q2: Apr-Jun
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 4
        assert start.day == 1
        assert end.month == 6
        assert end.day == 30  # June has 30 days

    def test_quarterly_q3(self) -> None:
        """Test quarterly period for Q3."""
        date = datetime(2024, 8, 15, 10, 0, 0)  # Q3: Jul-Sep
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 7
        assert start.day == 1
        assert end.month == 9
        assert end.day == 30  # September has 30 days

    def test_quarterly_q4(self) -> None:
        """Test quarterly period for Q4."""
        date = datetime(2024, 11, 15, 10, 0, 0)  # Q4: Oct-Dec
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 10
        assert start.day == 1
        assert end.month == 12
        assert end.day == 31  # December has 31 days
        assert end.year == 2024  # Should not roll over to next year

    def test_quarterly_q4_end_of_year(self) -> None:
        """Test quarterly period for Q4 at end of year."""
        date = datetime(2024, 12, 31, 10, 0, 0)  # Q4: Oct-Dec
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 10
        assert end.month == 12
        assert end.day == 31
        assert end.year == 2024

    def test_quarterly_leap_year_february(self) -> None:
        """Test quarterly period with February in leap year (Q1)."""
        date = datetime(2024, 2, 15, 10, 0, 0)  # Q1 in leap year
        start, end = _get_period_bounds(date, "quarterly")
        
        assert start.month == 1
        assert end.month == 3
        assert end.day == 31


class TestPeriodBoundsEdgeCases:
    """Test edge cases for period boundary calculations."""

    def test_daily_period(self) -> None:
        """Test daily period boundaries."""
        date = datetime(2024, 1, 15, 12, 30, 45)
        start, end = _get_period_bounds(date, "daily")
        
        assert start.year == date.year
        assert start.month == date.month
        assert start.day == date.day
        assert start.hour == 0
        assert start.minute == 0
        
        assert end.year == date.year
        assert end.month == date.month
        assert end.day == date.day
        assert end.hour == 23
        assert end.minute == 59

    def test_yearly_period(self) -> None:
        """Test yearly period boundaries."""
        date = datetime(2024, 6, 15, 12, 0, 0)
        start, end = _get_period_bounds(date, "yearly")
        
        assert start.month == 1
        assert start.day == 1
        assert start.year == 2024
        
        assert end.month == 12
        assert end.day == 31
        assert end.year == 2024

    def test_weekly_january_1_edge_case(self) -> None:
        """Test weekly period when Jan 1 is not a Monday."""
        # Jan 1, 2024 is a Monday, but Jan 1, 2025 is a Wednesday
        date = datetime(2025, 1, 1, 10, 0, 0)  # Wednesday
        start, end = _get_period_bounds(date, "weekly")
        
        # Should go back to Monday of that week (Dec 30, 2024)
        assert start.weekday() == 0
        assert start.year == 2024 or start.year == 2025
        assert end.weekday() == 6






