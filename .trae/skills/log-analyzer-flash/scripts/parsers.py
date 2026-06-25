"""
parsers.py - Log format parsers for log-analyzer.
Auto-detects and parses common log formats.
"""

import re
from datetime import datetime
from typing import Iterator, Optional, Dict, Any, List, Tuple

# ── Log level patterns ──
LOG_LEVELS = {"TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}

# ── Format definitions ──
FORMAT_PATTERNS: List[Tuple[str, re.Pattern, Dict[str, int]]] = [
    # ISO-8601 / standard timestamp [2024-01-01 12:00:00,123] LEVEL message
    ("iso", re.compile(
        r'^\[?(?P<ts>\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?)\]?\s+'
        r'(?P<level>TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b'
        r'(?:\s+\[?(?P<module>[^\]]+)\]?)?'
        r'\s*[:\-]?\s*(?P<message>.+)',
        re.IGNORECASE
    ), {}),

    # Syslog: <PRI>timestamp hostname tag: message
    ("syslog", re.compile(
        r'^(?:<\d+>)?'
        r'(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)'
        r'\s+\S+\s+(?P<module>\S+?)(?:\[\d+\])?:\s*'
        r'(?P<level>TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL)\s*'
        r'[:\-]?\s*(?P<message>.+)?',
        re.IGNORECASE
    ), {}),

    # NCSA / Common Log Format (Apache/Nginx access log)
    ("ncsa", re.compile(
        r'^(?P<remote>\S+)\s+\S+\s+\S+\s+'
        r'\[(?P<ts>\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4})\]'
        r'\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+\S+"\s+'
        r'(?P<status>\d{3})\s+(?P<size>\d+|-)',
    ), {}),

    # Java stack trace line (continuation lines after exception)
    ("java_stack", re.compile(
        r'^\s+at\s+[\w.$]+\([\w.]+\.java:\d+\)',
    ), {}),

    # Caused by: line
    ("caused_by", re.compile(
        r'^Caused by:\s+(?P<exception>[\w.]+(?:Exception|Error)):\s*(?P<message>.*)',
    ), {}),
]


def detect_format(line: str) -> Optional[str]:
    """Auto-detect which log format a line belongs to."""
    if not line.strip():
        return None
    for name, pattern, _ in FORMAT_PATTERNS:
        if pattern.match(line):
            return name
    return None


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single log line into a structured record.
    Returns None for unrecognized lines (continuation lines, blank lines, etc.)
    """
    stripped = line.strip("\n\r")
    if not stripped:
        return None

    for name, pattern, _ in FORMAT_PATTERNS:
        m = pattern.match(stripped)
        if not m:
            continue

        record: Dict[str, Any] = {
            "_raw": line,
            "_format": name,
            "_line_no": 0,  # set by caller
        }
        gd = m.groupdict()

        # Extract level
        level_raw = gd.get("level", "")
        if level_raw:
            record["level"] = level_raw.upper()
        elif name == "ncsa":
            status = int(gd.get("status", 0))
            if status >= 500:
                record["level"] = "ERROR"
            elif status >= 400:
                record["level"] = "WARN"
            else:
                record["level"] = "INFO"

        # Extract timestamp
        ts_raw = gd.get("ts")
        if ts_raw:
            record["timestamp"] = _parse_timestamp(ts_raw, name)
            record["timestamp_raw"] = ts_raw

        # Extract message
        msg = gd.get("message", "").strip()
        if msg:
            record["message"] = msg

        # Module/class info
        mod = gd.get("module")
        if mod:
            record["module"] = mod.strip("[] ")

        # HTTP-specific
        if name == "ncsa":
            record["http_method"] = gd.get("method", "")
            record["http_path"] = gd.get("path", "")
            record["http_status"] = int(gd.get("status", 0))
            record["remote_addr"] = gd.get("remote", "")
            record["message"] = f'{gd.get("method","")} {gd.get("path","")} -> {gd.get("status","")}'

        if name == "caused_by":
            record["exception"] = gd.get("exception", "")
            record["is_root_cause"] = True

        if name == "java_stack":
            record["is_stack_trace"] = True

        return record

    return None


def _parse_timestamp(raw: str, fmt_name: str) -> Optional[str]:
    """Parse timestamp into ISO-8601 string."""
    try:
        if fmt_name == "iso":
            ts = raw.replace("/", "-").replace("T", " ").replace(",", ".")
            if "." in ts:
                datetime.strptime(ts[:26], "%Y-%m-%d %H:%M:%S.%f")
            else:
                datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            return ts[:26] if "." in ts else ts[:19]

        elif fmt_name == "syslog":
            return datetime.strptime(raw, "%b %d %H:%M:%S").replace(year=datetime.now().year).isoformat()

        elif fmt_name == "ncsa":
            return datetime.strptime(raw[:20], "%d/%b/%Y:%H:%M:%S").isoformat()
    except (ValueError, IndexError):
        pass
    return None


def is_stack_trace_line(line: str) -> bool:
    """Check if a line is a Java stack continuation line."""
    return bool(re.match(r'^\s+at\s+', line)) or bool(re.match(r'^\.\.\.\s+\d+\s+more', line))
