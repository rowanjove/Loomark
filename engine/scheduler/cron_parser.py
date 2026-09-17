from datetime import datetime, timedelta
from typing import Set, Tuple, List, Optional

class CronParseError(ValueError):
    """Raised when a cron expression cannot be parsed."""
    pass

class CronParser:
    """
    Robust, pure-Python 5-field Linux Crontab parser and next-run calculator.
    Fields:
      1. Minute (0-59)
      2. Hour (0-23)
      3. Day of month (1-31)
      4. Month (1-12)
      5. Day of week (0-6, 0=Sunday, 7 also accepted as Sunday)
    """

    FIELD_RANGES = [
        (0, 59, "Minute"),
        (0, 23, "Hour"),
        (1, 31, "Day of Month"),
        (1, 12, "Month"),
        (0, 6, "Day of Week")
    ]

    MONTH_NAMES = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    DAY_NAMES = {
        "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6
    }

    @classmethod
    def parse_field(cls, field_str: str, min_val: int, max_val: int, is_dow: bool = False) -> Set[int]:
        field_str = field_str.strip().lower()
        if not field_str:
            raise CronParseError("Empty cron field")

        # Replace text month/day names if present
        if not is_dow and min_val == 1 and max_val == 12:
            for name, num in cls.MONTH_NAMES.items():
                field_str = field_str.replace(name, str(num))
        elif is_dow:
            for name, num in cls.DAY_NAMES.items():
                field_str = field_str.replace(name, str(num))

        values: Set[int] = set()
        parts = field_str.split(",")

        for part in parts:
            part = part.strip()
            if not part:
                raise CronParseError("Invalid comma-separated value in cron field")

            step = 1
            if "/" in part:
                subparts = part.split("/")
                if len(subparts) != 2:
                    raise CronParseError(f"Invalid step syntax in '{part}'")
                range_part, step_str = subparts[0], subparts[1]
                if not step_str.isdigit() or int(step_str) <= 0:
                    raise CronParseError(f"Step value must be a positive integer: '{step_str}'")
                step = int(step_str)
            else:
                range_part = part

            if range_part == "*":
                start, end = min_val, max_val
            elif "-" in range_part:
                subparts = range_part.split("-")
                if len(subparts) != 2 or not subparts[0].isdigit() or not subparts[1].isdigit():
                    raise CronParseError(f"Invalid range syntax in '{range_part}'")
                start, end = int(subparts[0]), int(subparts[1])
                if start > end:
                    raise CronParseError(f"Range start must be <= end: '{range_part}'")
            else:
                if not range_part.isdigit():
                    raise CronParseError(f"Invalid number in cron field: '{range_part}'")
                start = end = int(range_part)

            # Handle 7 for Sunday
            if is_dow:
                if start == 7:
                    start = 0
                if end == 7:
                    end = 6

            if start < min_val or end > max_val:
                raise CronParseError(f"Value out of bounds ({min_val}-{max_val}): '{range_part}'")

            for v in range(start, end + 1, step):
                if is_dow and v == 7:
                    v = 0
                values.add(v)

        return values

    @classmethod
    def validate_cron(cls, expr: str) -> Tuple[bool, str]:
        """Validate a 5-field cron expression. Returns (is_valid, error_or_success_message)."""
        fields = expr.strip().split()
        if len(fields) != 5:
            return False, f"Cron 表达式必须包含 5 个段位，当前提供了解析出的 {len(fields)} 个段"

        try:
            for i, (min_v, max_v, name) in enumerate(cls.FIELD_RANGES):
                cls.parse_field(fields[i], min_v, max_v, is_dow=(i == 4))
            return True, "Valid cron expression"
        except Exception as e:
            return False, str(e)

    @classmethod
    def parse_expression(cls, expr: str) -> Tuple[Set[int], Set[int], Set[int], Set[int], Set[int], bool, bool]:
        """
        Parse expression into sets of valid integers.
        Also returns whether day_of_month and day_of_week were wildcards '*'.
        """
        fields = expr.strip().split()
        if len(fields) != 5:
            raise CronParseError(f"Expected 5 fields, got {len(fields)}")

        dom_is_wildcard = (fields[2].strip() == "*")
        dow_is_wildcard = (fields[4].strip() == "*")

        minutes = cls.parse_field(fields[0], 0, 59)
        hours = cls.parse_field(fields[1], 0, 23)
        days = cls.parse_field(fields[2], 1, 31)
        months = cls.parse_field(fields[3], 1, 12)
        dows = cls.parse_field(fields[4], 0, 6, is_dow=True)

        return minutes, hours, days, months, dows, dom_is_wildcard, dow_wild_status(dom_is_wildcard, dow_is_wildcard)

    @classmethod
    def get_next_run(cls, expr: str, base_time: Optional[datetime] = None) -> datetime:
        """
        Calculate the next execution datetime matching the cron expression.
        Strict adherence to Linux Crontab DOM/DOW intersection semantics.
        """
        if base_time is None:
            base_time = datetime.now()

        fields = expr.strip().split()
        if len(fields) != 5:
            raise CronParseError(f"Expected 5 fields, got {len(fields)}")

        dom_wild = (fields[2].strip() == "*")
        dow_wild = (fields[4].strip() == "*")

        minutes = cls.parse_field(fields[0], 0, 59)
        hours = cls.parse_field(fields[1], 0, 23)
        days = cls.parse_field(fields[2], 1, 31)
        months = cls.parse_field(fields[3], 1, 12)
        dows = cls.parse_field(fields[4], 0, 6, is_dow=True)

        # Advance by 1 minute and clear seconds/microseconds
        current = (base_time + timedelta(minutes=1)).replace(second=0, microsecond=0)

        # Look forward up to 5 years (approx 5 * 366 * 24 * 60 minutes) to prevent infinite loop
        max_searches = 5 * 366 * 24 * 60
        searches = 0

        while searches < max_searches:
            # 1. Month check
            if current.month not in months:
                # Fast forward to next month
                if current.month == 12:
                    current = datetime(current.year + 1, 1, 1, 0, 0)
                else:
                    current = datetime(current.year, current.month + 1, 1, 0, 0)
                searches += 1
                continue

            # 2. Day check (Linux crontab specification):
            # If both dom and dow are restricted (neither is *), it matches if EITHER matches (OR).
            # If at least one is *, it matches if BOTH match (AND).
            dom_matches = current.day in days
            cron_weekday = (current.weekday() + 1) % 7
            dow_matches = cron_weekday in dows

            day_valid = False
            if not dom_wild and not dow_wild:
                day_valid = dom_matches or dow_matches
            else:
                day_valid = dom_matches and dow_matches

            if not day_valid:
                # Advance to next day at 00:00
                current = (current + timedelta(days=1)).replace(hour=0, minute=0)
                searches += 1
                continue

            # 3. Hour check
            if current.hour not in hours:
                # Advance to next hour at 00 minutes
                current = (current + timedelta(hours=1)).replace(minute=0)
                searches += 1
                continue

            # 4. Minute check
            if current.minute not in minutes:
                current += timedelta(minutes=1)
                searches += 1
                continue

            return current

        raise CronParseError("Could not find matching next run within 5 years.")

    @classmethod
    def get_next_n_runs(cls, expr: str, n: int = 5, base_time: Optional[datetime] = None) -> List[datetime]:
        """Get the next N scheduled execution datetimes."""
        runs = []
        cur = base_time or datetime.now()
        for _ in range(n):
            next_t = cls.get_next_run(expr, cur)
            runs.append(next_t)
            cur = next_t
        return runs

    @classmethod
    def describe_cron(cls, expr: str) -> str:
        """
        Translate 5-field cron into natural, readable Chinese description.
        """
        fields = expr.strip().split()
        if len(fields) != 5:
            return "无效的 Cron 表达式"

        m_str, h_str, dom_str, mon_str, dow_str = fields

        # Simple patterns
        if expr.strip() == "* * * * *":
            return "每分钟执行一次"
        if m_str.startswith("*/") and h_str == "*" and dom_str == "*" and mon_str == "*" and dow_str == "*":
            return f"每 {m_str[2:]} 分钟执行一次"
        if m_str == "0" and h_str == "*" and dom_str == "*" and mon_str == "*" and dow_str == "*":
            return "每小时整点执行一次"
        if m_str == "0" and h_str.startswith("*/") and dom_str == "*" and mon_str == "*" and dow_str == "*":
            return f"每 {h_str[2:]} 小时整点执行一次"
        if dom_str == "*" and mon_str == "*":
            time_part = f"{h_str.zfill(2)}:{m_str.zfill(2)}" if (h_str.isdigit() and m_str.isdigit()) else f"{h_str}时 {m_str}分"
            if dow_str == "*":
                return f"每天 {time_part} 执行"
            elif dow_str in ("1-5", "mon-fri"):
                return f"工作日(周一至周五) {time_part} 执行"
            elif dow_str in ("0,6", "6,0", "sat,sun"):
                return f"周末(周六日) {time_part} 执行"
            elif dow_str.isdigit():
                day_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
                d_idx = int(dow_str) % 7
                return f"每{day_names[d_idx]} {time_part} 执行"

        # General composition
        parts = []
        if mon_str != "*":
            parts.append(f"每年的第 {mon_str} 月")
        if dom_str != "*":
            parts.append(f"每月第 {dom_str} 号")
        if dow_str != "*":
            parts.append(f"周[{dow_str}]")
        if h_str != "*":
            parts.append(f"{h_str} 时")
        else:
            parts.append("每小时")
        if m_str != "*":
            parts.append(f"{m_str} 分")
        else:
            parts.append("每分钟")

        return " ".join(parts) + " 执行"
