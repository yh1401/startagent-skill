#!/usr/bin/env python3
"""
analyze.py - Log-analyzer-skill main entry point.
Streams through log files, parses records, computes stats,
infers root causes, and generates multi-format reports.

Zero external dependencies, runs on Python 3.8+.

Usage:
  python3 scripts/analyze.py <log-file-path> [--format markdown|json|html] [--output-dir ./] [--verbose]
  python3 scripts/analyze.py ./logs/ --format json -o ./reports
  python3 scripts/analyze.py "logs/**/*.log" --format html --verbose
"""

import os
import sys
import time
import glob
import argparse
from typing import Optional, Dict, Any
from datetime import datetime

# Allow running from scripts/ directory directly
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from parsers import parse_line, detect_format, parse_json_log, is_stack_trace_line
from stats import compute_statistics, compute_trend_analysis, compute_severity_distribution
from root_cause import infer_root_causes
from reporters import generate_markdown, generate_json_report, generate_html_report, generate_word_report, generate_pdf_report


STREAM_THRESHOLD = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 64 * 1024  # 64 KB chunks


def stream_parse(file_path: str, verbose: bool = False) -> list:
    """
    Stream-parse a log file. For large files (>100MB), uses chunked streaming
    to avoid loading the entire file into memory at once.
    Returns a list of parsed record dicts.
    Supports: ISO, Syslog, NCSA, Java stack, JSON log formats.
    """
    file_size = os.path.getsize(file_path)
    use_stream = file_size > STREAM_THRESHOLD

    if verbose:
        print(f"📄 文件大小: {_fmt_size(file_size)}", file=sys.stderr)
        print(f"🚰 流式模式: {'启用' if use_stream else '关闭(全量加载)'}", file=sys.stderr)

    records = []
    line_no = 0
    start = time.time()
    current_record = None
    stack_trace = []

    if use_stream:
        with open(file_path, "r", errors="replace") as f:
            buffer = ""
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer += chunk
                lines = buffer.split("\n")
                buffer = lines.pop()

                for line in lines:
                    if not line.strip():
                        line_no += 1
                        continue
                    line_no += 1

                    # Handle stack trace continuation
                    if is_stack_trace_line(line):
                        stack_trace.append(line.strip())
                        if current_record:
                            current_record["stack_trace"] = "\n".join(stack_trace)
                        continue

                    # Try JSON parsing first
                    rec = parse_json_log(line)
                    if rec:
                        if stack_trace and current_record:
                            current_record["stack_trace"] = "\n".join(stack_trace)
                            stack_trace = []
                        rec["_line_no"] = line_no
                        records.append(rec)
                        current_record = rec
                        continue

                    # Regular parsing
                    rec = parse_line(line)
                    if rec:
                        if stack_trace and current_record:
                            current_record["stack_trace"] = "\n".join(stack_trace)
                            stack_trace = []
                        rec["_line_no"] = line_no
                        records.append(rec)
                        current_record = rec

            if buffer.strip():
                line_no += 1
                rec = parse_json_log(buffer) or parse_line(buffer)
                if rec:
                    if stack_trace:
                        rec["stack_trace"] = "\n".join(stack_trace)
                    rec["_line_no"] = line_no
                    records.append(rec)
    else:
        with open(file_path, "r", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        for i, line in enumerate(lines):
            line_no = i + 1
            if not line.strip():
                continue

            # Handle stack trace continuation
            if is_stack_trace_line(line):
                stack_trace.append(line.strip())
                if current_record:
                    current_record["stack_trace"] = "\n".join(stack_trace)
                continue

            # Try JSON parsing first
            rec = parse_json_log(line)
            if rec:
                if stack_trace and current_record:
                    current_record["stack_trace"] = "\n".join(stack_trace)
                    stack_trace = []
                rec["_line_no"] = line_no
                records.append(rec)
                current_record = rec
                continue

            # Regular parsing
            rec = parse_line(line)
            if rec:
                if stack_trace and current_record:
                    current_record["stack_trace"] = "\n".join(stack_trace)
                    stack_trace = []
                rec["_line_no"] = line_no
                records.append(rec)
                current_record = rec

            if verbose and line_no % 500000 == 0 and line_no > 0:
                elapsed = time.time() - start
                pct = min(100, line_no / total * 100)
                print(f"  进度: {pct:.0f}% ({line_no:,}/{total:,}, {elapsed:.1f}s)", file=sys.stderr)

    # Handle remaining stack trace
    if stack_trace and current_record:
        current_record["stack_trace"] = "\n".join(stack_trace)

    elapsed = time.time() - start
    if verbose:
        total_lines = line_no
        parsed = len(records)
        print(f"✅ 解析完成: {total_lines:,} 行 → {parsed} 条结构化记录 ({elapsed:.2f}s)", file=sys.stderr)

    return records


def _fmt_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_log_files(path: str) -> list:
    """Find log files by path. Supports single files, directories, and glob patterns."""
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        extensions = ("*.log", "*.txt", "*.out", "*.err", "*.output", "*.syslog")
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(path, ext)))
            files.extend(glob.glob(os.path.join(path, "**", ext), recursive=True))
        return sorted(set(files))
    files = glob.glob(path, recursive=True)
    return sorted(files)


def analyze(file_path: str, output_format: str = "markdown",
            output_dir: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Full analysis pipeline: parse → stats → trend → severity → root cause → report.
    Returns the report metadata dict with trend analysis and health score.
    """
    t0 = time.time()
    records = stream_parse(file_path, verbose=verbose)

    if not records:
        print("⚠️  未解析到任何结构化日志记录。文件可能为空或格式不兼容。", file=sys.stderr)
        return {"status": "empty", "file": file_path}

    # Phase 1: Statistics
    stats = compute_statistics(records)
    t1 = time.time()

    # Phase 2: Trend analysis
    trend = compute_trend_analysis(stats)
    t2 = time.time()

    # Phase 3: Severity distribution (includes health score)
    severity = compute_severity_distribution(stats)
    t3 = time.time()

    # Phase 4: Root cause inference
    root_cause = infer_root_causes(records, stats)
    t4 = time.time()

    duration = time.time() - t0
    report = {}

    # Extended ext_map for all formats
    ext_map = {"markdown": "md", "json": "json", "html": "html", "word": "docx", "pdf": "pdf"}

    if output_format == "json":
        report["_format"] = "json"
        content = generate_json_report(stats, root_cause, file_path, duration, trend, severity)
    elif output_format == "html":
        report["_format"] = "html"
        content = generate_html_report(stats, root_cause, file_path, duration, trend, severity)
    elif output_format == "word":
        report["_format"] = "word"
        content = generate_word_report(stats, root_cause, file_path, duration, trend, severity)
        if not content:
            print("⚠️ Word 报告生成失败：python-docx 库未安装，请运行: pip install python-docx", file=sys.stderr)
    elif output_format == "pdf":
        report["_format"] = "pdf"
        content = generate_pdf_report(stats, root_cause, file_path, duration, trend, severity)
        if not content:
            print("⚠️ PDF 报告生成失败：weasyprint 库未安装，请运行: pip install weasyprint", file=sys.stderr)
    else:
        report["_format"] = "markdown"
        content = generate_markdown(stats, root_cause, file_path, duration, trend, severity)

    if output_dir and content:
        basename = os.path.splitext(os.path.basename(file_path))[0]
        ext = ext_map.get(output_format, "md")
        out_path = os.path.join(output_dir, f"{basename}_report.{ext}")
        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📝 报告已保存: {out_path}", file=sys.stderr)
        report["output_path"] = out_path
    elif content:
        print(content)

    if verbose:
        print(f"\n⚡ 性能: 解析 {t1-t0:.2f}s → 统计 {t2-t1:.2f}s → 趋势 {t3-t2:.2f}s → 根因 {t4-t3:.2f}s → 报告 {time.time()-t4:.2f}s", file=sys.stderr)

    report.update({
        "status": "ok",
        "file": file_path,
        "total_lines": stats.get("total_lines", 0),
        "error_lines": stats.get("error_lines", 0),
        "error_rate": stats.get("error_rate", 0.0),
        "health_score": severity.get("health_score", 0),
        "trend_type": trend.get("trend_type", "unknown"),
        "formatted_causes": root_cause.get("recommendation", ""),
        "duration_sec": round(duration, 2),
    })
    return report


def main():
    parser = argparse.ArgumentParser(
        description="日志深度分析工具 - 流式解析、错误统计、根因推断及多格式报告生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/analyze.py app.log
  python3 scripts/analyze.py app.log --format json --output-dir ./reports
  python3 scripts/analyze.py /var/log/nginx/access.log --format html --verbose
  python3 scripts/analyze.py ./logs/ --format markdown --output-dir ./reports
  python3 scripts/analyze.py "logs/**/*.log" -o ./reports
        """,
    )
    parser.add_argument("path", help="日志文件路径、目录或 glob 通配符")
    parser.add_argument("--format", choices=["markdown", "json", "html", "word", "pdf"], default="markdown",
                        help="输出报告格式（默认 markdown）")
    parser.add_argument("--output-dir", "-o", help="报告输出目录（不指定则打印到终端）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    files = find_log_files(args.path)
    if not files:
        print(f"❌ 未找到日志文件: {args.path}", file=sys.stderr)
        sys.exit(1)

    reports = []
    for fpath in files:
        if args.verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"分析: {fpath}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
        report = analyze(fpath, args.format, args.output_dir, args.verbose)
        reports.append(report)

    if len(files) > 1:
        total_err = sum(r.get("error_lines", 0) for r in reports)
        total_lines = sum(r.get("total_lines", 0) for r in reports)
        total_time = sum(r.get("duration_sec", 0) for r in reports)
        print(f"\n📊 批量分析完成: {len(files)} 个文件, "
              f"共 {total_lines:,} 行, {total_err:,} 条错误, "
              f"耗时 {total_time:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
