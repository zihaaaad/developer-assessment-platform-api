import asyncio
import os
import shutil
import sys
import tempfile
import time
from typing import Optional

from app.core.config import settings
from app.models.enums import LanguageEnum, SubmissionStatusEnum
from app.sandbox.types import ExecutionResult


class CodeExecutor:
    @staticmethod
    def normalize_output(text: str) -> str:
        if not text:
            return ""
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(lines).strip()

    @classmethod
    async def run(
        cls,
        language: LanguageEnum,
        source_code: str,
        stdin_input: str = "",
        time_limit_ms: int = 2000,
        memory_limit_mb: int = 128,
    ) -> ExecutionResult:
        temp_dir = tempfile.mkdtemp(prefix="sandbox_")
        start_time = time.perf_counter()

        try:
            if language == LanguageEnum.PYTHON:
                script_path = os.path.join(temp_dir, "solution.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(source_code)
                cmd = [sys.executable, "-u", script_path]
            elif language == LanguageEnum.JAVASCRIPT:
                script_path = os.path.join(temp_dir, "solution.js")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(source_code)
                cmd = ["node", f"--max-old-space-size={memory_limit_mb}", script_path]
            else:
                return ExecutionResult(
                    status=SubmissionStatusEnum.RUNTIME_ERROR,
                    stdout="",
                    stderr=f"Unsupported language: {language}",
                    execution_time_ms=0,
                    error_message=f"Unsupported language: {language}",
                )

            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "TEMP": temp_dir,
                "TMP": temp_dir,
            }

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=safe_env,
            )

            input_bytes = stdin_input.encode("utf-8") if stdin_input else None
            timeout_sec = time_limit_ms / 1000.0

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(input=input_bytes),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return ExecutionResult(
                    status=SubmissionStatusEnum.TIME_LIMIT_EXCEEDED,
                    stdout="",
                    stderr="Time Limit Exceeded",
                    execution_time_ms=elapsed_ms,
                    error_message=f"Process exceeded time limit of {time_limit_ms}ms",
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            if len(stdout_data) > settings.MAX_OUTPUT_BUFFER_BYTES:
                return ExecutionResult(
                    status=SubmissionStatusEnum.OUTPUT_LIMIT_EXCEEDED,
                    stdout="",
                    stderr="Output Limit Exceeded",
                    execution_time_ms=elapsed_ms,
                    error_message="Output exceeded maximum allowed buffer size (64KB)",
                )

            stdout_str = stdout_data.decode("utf-8", errors="replace")
            stderr_str = stderr_data.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ExecutionResult(
                    status=SubmissionStatusEnum.RUNTIME_ERROR,
                    stdout=cls.normalize_output(stdout_str),
                    stderr=stderr_str.strip(),
                    execution_time_ms=elapsed_ms,
                    error_message=stderr_str.strip() or f"Process exited with code {process.returncode}",
                )

            return ExecutionResult(
                status=SubmissionStatusEnum.ACCEPTED,
                stdout=cls.normalize_output(stdout_str),
                stderr=stderr_str.strip(),
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                status=SubmissionStatusEnum.RUNTIME_ERROR,
                stdout="",
                stderr=str(e),
                execution_time_ms=elapsed_ms,
                error_message=str(e),
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
