import pytest
from datetime import datetime
from engine.scheduler.cron_parser import CronParser, CronParseError

def test_validate_cron():
    valid, msg = CronParser.validate_cron("* * * * *")
    assert valid is True

    valid, msg = CronParser.validate_cron("*/15 0-23/2 1,15,30 * 1-5")
    assert valid is True

    # Invalid: 4 fields
    valid, msg = CronParser.validate_cron("* * * *")
    assert valid is False

    # Invalid: out of bounds
    valid, msg = CronParser.validate_cron("60 * * * *")
    assert valid is False

    # Invalid: negative step
    valid, msg = CronParser.validate_cron("*/0 * * * *")
    assert valid is False

def test_cron_next_run():
    # Base: 2026-09-17 10:14:20
    base = datetime(2026, 9, 17, 10, 14, 20)

    # 1. Every 15 minutes: should be 10:15:00
    next_1 = CronParser.get_next_run("*/15 * * * *", base)
    assert next_1 == datetime(2026, 9, 17, 10, 15, 0)

    # 2. At 11:00
    next_2 = CronParser.get_next_run("0 11 * * *", base)
    assert next_2 == datetime(2026, 9, 17, 11, 0, 0)

    # 3. Next Monday at 09:00 (2026-09-17 is Thursday)
    # Next Monday is 2026-09-21
    next_mon = CronParser.get_next_run("0 9 * * 1", base)
    assert next_mon == datetime(2026, 9, 21, 9, 0, 0)

def test_cron_describe():
    assert "每 15 分钟" in CronParser.describe_cron("*/15 * * * *")
    assert "工作日" in CronParser.describe_cron("0 9 * * 1-5")
    assert "每小时整点" in CronParser.describe_cron("0 * * * *")
    assert "每天 02:30" in CronParser.describe_cron("30 2 * * *")

def test_get_next_n_runs():
    base = datetime(2026, 1, 1, 0, 0, 0)
    runs = CronParser.get_next_n_runs("0 0 * * *", n=3, base_time=base)
    assert len(runs) == 3
    assert runs[0] == datetime(2026, 1, 2, 0, 0, 0)
    assert runs[1] == datetime(2026, 1, 3, 0, 0, 0)
    assert runs[2] == datetime(2026, 1, 4, 0, 0, 0)
