import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

RATE_LIMIT_RE = re.compile(r"(429|RESOURCE_EXHAUSTED|rate\s*limit)", re.IGNORECASE)
SOLVED_RE = re.compile(r"SOLUTION TROUV[ÉE].*?:\s*(?P<title>.+)$", re.IGNORECASE | re.MULTILINE)
RECON_RE = re.compile(r"Titre reconstruit à partir des positions exactes\s*:\s*(?P<title>.+)$", re.IGNORECASE | re.MULTILINE)


@dataclass
class BenchResult:
    case_id: str
    provider: str
    sub_provider: str
    attempts: int
    status: str
    duration_s: float
    solved_title: str
    command: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Pedantix agent across providers")
    parser.add_argument("--max-iterations", type=int, default=12)
    parser.add_argument("--cooldown-seconds", type=int, default=70)
    parser.add_argument("--output", type=str, default="debug_output_benchmark_agent.json")
    parser.add_argument("--python", type=str, default=sys.executable)
    parser.add_argument("--case-timeout", type=int, default=240)
    return parser.parse_args()


def extract_title(output: str) -> str:
    solved = SOLVED_RE.search(output)
    if solved:
        return solved.group("title").strip()
    recon = RECON_RE.search(output)
    if recon:
        return recon.group("title").strip()
    return ""


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def run_once(
    python_cmd: str,
    provider: str,
    sub_provider: str,
    max_iterations: int,
    case_timeout: int,
) -> tuple[int, str, float]:
    cmd = [
        python_cmd,
        "-m",
        "scripts.pedantix.cli",
        "--mode",
        "agent",
        "--provider",
        provider,
        "--sub-provider",
        sub_provider,
        "--max-iterations",
        str(max_iterations),
    ]
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=case_timeout)
        duration = time.perf_counter() - start
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode, output, duration
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - start
        partial_out = ""
        if exc.stdout:
            partial_out += _as_text(exc.stdout)
        if exc.stderr:
            stderr_text = _as_text(exc.stderr)
            partial_out += "\n" + stderr_text
        partial_out += f"\n[benchmark] timeout after {case_timeout}s"
        return 124, partial_out, duration


def to_status(return_code: int, output: str) -> str:
    if extract_title(output):
        return "solved"
    if RATE_LIMIT_RE.search(output):
        return "rate_limited"
    if return_code != 0:
        return "failed"
    return "unsolved"


def maybe_fallback_provider(provider: str) -> str | None:
    if provider == "gemini":
        return "groq"
    if provider == "groq":
        return "ollama"
    return None


def benchmark(args: argparse.Namespace) -> list[BenchResult]:
    scenarios = [
        ("case-1", "gemini", "ollama-small"),
        ("case-2", "groq", "ollama-small"),
        ("case-3", "gemini", "groq"),
        ("case-4", "groq", "ollama"),
        ("case-5", "ollama", "ollama-small"),
        ("case-6", "gemini", "ollama"),
    ]

    results: list[BenchResult] = []

    for case_id, provider, sub_provider in scenarios:
        attempts = 0
        active_provider = provider
        active_sub_provider = sub_provider
        final_status = "failed"
        final_duration = 0.0
        final_title = ""

        while attempts < 3:
            attempts += 1
            print(f"\n=== {case_id} | provider={active_provider} | sub_provider={active_sub_provider} | attempt={attempts} ===")
            return_code, output, duration = run_once(
                args.python,
                active_provider,
                active_sub_provider,
                args.max_iterations,
                args.case_timeout,
            )
            status = to_status(return_code, output)
            title = extract_title(output)
            print(f"status={status} | duration={duration:.2f}s | title={title or '-'}")

            final_status = status
            final_duration = duration
            final_title = title

            if status == "solved":
                break

            if status == "rate_limited":
                fallback = maybe_fallback_provider(active_provider)
                if fallback and fallback != active_provider:
                    print(f"rate limit detected: switching provider {active_provider} -> {fallback}")
                    active_provider = fallback
                    continue

                print(f"rate limit detected: waiting {args.cooldown_seconds}s before retry")
                time.sleep(args.cooldown_seconds)
                continue

            if status in {"unsolved", "failed"}:
                break

        cmd_preview = (
            f"{args.python} -m scripts.pedantix.cli --mode agent --provider {active_provider} "
            f"--sub-provider {active_sub_provider} --max-iterations {args.max_iterations}"
        )
        results.append(
            BenchResult(
                case_id=case_id,
                provider=active_provider,
                sub_provider=active_sub_provider,
                attempts=attempts,
                status=final_status,
                duration_s=round(final_duration, 2),
                solved_title=final_title,
                command=cmd_preview,
            )
        )

        # Soft cooldown between Gemini-led scenarios to reduce quota spikes.
        if active_provider == "gemini":
            print(f"cooldown after gemini run: {args.cooldown_seconds}s")
            time.sleep(args.cooldown_seconds)

    return results


def print_summary(results: list[BenchResult]) -> None:
    headers = ["case", "provider", "sub", "attempts", "status", "duration_s", "title"]
    rows = [
        [
            r.case_id,
            r.provider,
            r.sub_provider,
            str(r.attempts),
            r.status,
            f"{r.duration_s:.2f}",
            r.solved_title or "-",
        ]
        for r in results
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print("\n" + fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def main() -> None:
    args = parse_args()
    try:
        results = benchmark(args)
    except KeyboardInterrupt:
        print("\nbenchmark interrupted by user")
        return

    output_path = Path(args.output)
    output_path.write_text(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(results)
    print(f"\nbenchmark written to: {output_path}")


if __name__ == "__main__":
    main()
