"""
Judge Orchestrator Module.

Coordinates workspace setup, compilation, binary execution via Executor interface,
output comparison, and status verdict determination.
"""

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Ensure backend app import path is available for SubmissionStatus
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.models.submission import SubmissionStatus

from comparator import OutputComparator
from compiler import CompileResult, compile_cpp
from executor import ExecutionResult, Executor
from sandbox_policy import DEFAULT_SANDBOX_POLICY, CompileLimits, ExecutionLimits, SandboxPolicy
from workspace import SubmissionWorkspace, WorkspaceError


@dataclass(frozen=True)
class TestCaseResult:
    """
    Evaluation verdict and execution details for a single testcase.
    """
    testcase_index: int
    status: SubmissionStatus
    execution_result: Optional[ExecutionResult]
    matched: bool
    duration_ms: float


@dataclass(frozen=True)
class JudgeResult:
    """
    Final evaluation verdict and metrics for a complete submission.
    """
    submission_id: str
    status: SubmissionStatus
    compile_result: Optional[CompileResult]
    testcase_results: List[TestCaseResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error_message: Optional[str] = None


class Judge:
    """
    Orchestrates the evaluation pipeline for participant submissions.
    Uses Dependency Injection for the Executor interface.
    """

    def __init__(
        self,
        executor: Executor,
        comparator: Optional[OutputComparator] = None,
        use_docker_compiler: bool = False,
        policy: Optional[SandboxPolicy] = None,
    ):
        self.executor = executor
        self.comparator = comparator or OutputComparator()
        self.use_docker_compiler = use_docker_compiler
        self.policy = policy or DEFAULT_SANDBOX_POLICY

    def evaluate(
        self,
        submission_id: str,
        source_code: str,
        testcases: List[Dict[str, str]],
        compile_limits: Optional[CompileLimits] = None,
        execution_limits: Optional[ExecutionLimits] = None,
    ) -> JudgeResult:
        """
        Evaluates a C++ source code submission against a set of testcases.

        Args:
            submission_id: Unique submission identifier.
            source_code: Participant C++ code string.
            testcases: List of dicts with 'input' and 'expected' keys.
            compile_limits: Time and output limits for compiler.
            execution_limits: Time and output limits for binary runner.

        Returns:
            Structured JudgeResult detailing overall status and testcase outcomes.
        """
        if compile_limits is None:
            compile_limits = self.policy.compile_limits
        if execution_limits is None:
            execution_limits = self.policy.execution_limits

        start_time = time.monotonic()
        testcase_results: List[TestCaseResult] = []

        with SubmissionWorkspace() as workspace:
            # 1. Write source code to workspace
            try:
                workspace.write_source(source_code)
            except WorkspaceError as we:
                duration_ms = (time.monotonic() - start_time) * 1000.0
                return JudgeResult(
                    submission_id=submission_id,
                    status=SubmissionStatus.SYSTEM_ERROR,
                    compile_result=None,
                    testcase_results=[],
                    total_duration_ms=round(duration_ms, 2),
                    error_message=str(we),
                )

            # 2. Compile source code (inside Docker if use_docker_compiler is True)
            compile_res = compile_cpp(
                source_path=workspace.source_path,
                output_path=workspace.binary_path,
                limits=compile_limits,
                use_docker=self.use_docker_compiler,
                policy=self.policy,
            )

            if compile_res.is_docker_system_error:
                duration_ms = (time.monotonic() - start_time) * 1000.0
                return JudgeResult(
                    submission_id=submission_id,
                    status=SubmissionStatus.SYSTEM_ERROR,
                    compile_result=compile_res,
                    testcase_results=[],
                    total_duration_ms=round(duration_ms, 2),
                    error_message=compile_res.error_message or "Docker compilation system error.",
                )

            if not compile_res.success:
                duration_ms = (time.monotonic() - start_time) * 1000.0
                return JudgeResult(
                    submission_id=submission_id,
                    status=SubmissionStatus.COMPILATION_ERROR,
                    compile_result=compile_res,
                    testcase_results=[],
                    total_duration_ms=round(duration_ms, 2),
                    error_message=compile_res.error_message or "Compilation failed.",
                )

            # 3. Execute compiled binary against testcases
            overall_status = SubmissionStatus.ACCEPTED

            for idx, tc in enumerate(testcases):
                stdin_data = tc.get("input", "")
                expected_output = tc.get("expected", "")

                exec_res = self.executor.run(
                    binary_path=workspace.binary_path,
                    stdin_data=stdin_data,
                    limits=execution_limits,
                )

                # Determine testcase verdict with strict priority
                matched = False
                if exec_res.is_docker_system_error:
                    tc_status = SubmissionStatus.SYSTEM_ERROR
                elif exec_res.oom_killed:
                    tc_status = SubmissionStatus.MEMORY_LIMIT_EXCEEDED
                elif exec_res.timed_out:
                    tc_status = SubmissionStatus.TIME_LIMIT_EXCEEDED
                elif exec_res.output_limit_exceeded:
                    tc_status = SubmissionStatus.OUTPUT_LIMIT_EXCEEDED
                elif exec_res.signal_number is not None or exec_res.return_code != 0:
                    tc_status = SubmissionStatus.RUNTIME_ERROR
                else:
                    cmp_res = self.comparator.compare(exec_res.stdout, expected_output)
                    matched = cmp_res.matched
                    tc_status = SubmissionStatus.ACCEPTED if matched else SubmissionStatus.WRONG_ANSWER

                tc_result = TestCaseResult(
                    testcase_index=idx,
                    status=tc_status,
                    execution_result=exec_res,
                    matched=matched,
                    duration_ms=exec_res.duration_ms,
                )
                testcase_results.append(tc_result)

                # Stop on first non-ACCEPTED testcase
                if tc_status != SubmissionStatus.ACCEPTED:
                    overall_status = tc_status
                    break

            total_duration_ms = (time.monotonic() - start_time) * 1000.0

            return JudgeResult(
                submission_id=submission_id,
                status=overall_status,
                compile_result=compile_res,
                testcase_results=testcase_results,
                total_duration_ms=round(total_duration_ms, 2),
                error_message=None if overall_status == SubmissionStatus.ACCEPTED else f"Verdict: {overall_status.value}",
            )
