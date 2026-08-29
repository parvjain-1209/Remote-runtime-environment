"""
Python Worker Service for GDG Remote Runtime.

Listens to Redis Streams for submission job IDs, performs atomic status claiming,
invokes the Judge pipeline (Docker Sandbox or System Binaries LocalExecutor),
persists results to PostgreSQL, and ACKs jobs.
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add worker and backend to Python path
WORKER_DIR = Path(__file__).resolve().parent
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.models.problem import Problem
from app.models.submission import Submission, SubmissionStatus, TERMINAL_STATUSES
from app.models.testcase import TestCase

from comparator import OutputComparator
from compiler import compile_code
from executor import DockerExecutor, LocalExecutor
from judge import Judge, JudgeResult
from sandbox_policy import DEFAULT_SANDBOX_POLICY, CompileLimits, ExecutionLimits

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")


def is_docker_available() -> bool:
    """Checks if docker CLI and daemon are accessible."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3.0,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


class Worker:
    """
    Background worker processing submission jobs from Redis Stream.
    """

    def __init__(self):
        redis_kwargs = {"decode_responses": True}
        if settings.redis_url.startswith("rediss://"):
            redis_kwargs["ssl_cert_reqs"] = "none"
        self.redis_client = redis.from_url(settings.redis_url, **redis_kwargs)
        self.stream_name = settings.redis_stream_name
        self.group_name = settings.redis_consumer_group
        self.consumer_name = settings.worker_consumer_name

    def ensure_consumer_group(self) -> None:
        """Ensures the Redis Stream consumer group exists."""
        try:
            self.redis_client.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id="$",
                mkstream=True,
            )
            logger.info(f"Created Redis Stream consumer group '{self.group_name}'")
        except redis.exceptions.ResponseError as err:
            if "BUSYGROUP" in str(err):
                pass
            else:
                raise

    def recover_stale_jobs(self) -> None:
        """
        Scans PostgreSQL for unqueued QUEUED jobs or abandoned COMPILING/RUNNING jobs
        (older than stale timeout) and re-enqueues them to Redis.
        """
        db: Session = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc)
            stale_cutoff = now_utc - timedelta(seconds=settings.stale_job_timeout_seconds)

            # 1. Re-enqueue QUEUED jobs older than 10s (reconciliation for failed initial XADD)
            queued_cutoff = now_utc - timedelta(seconds=10.0)
            queued_submissions = (
                db.query(Submission)
                .filter(
                    Submission.status == SubmissionStatus.QUEUED.value,
                    Submission.created_at < queued_cutoff
                )
                .all()
            )
            for sub in queued_submissions:
                logger.info(f"Recovery: Re-enqueuing stuck QUEUED submission '{sub.id}'")
                try:
                    self.redis_client.xadd(self.stream_name, {"submission_id": sub.id})
                except Exception as ex:
                    logger.error(f"Failed to re-enqueue submission '{sub.id}': {ex}")

            # 2. Reset TRULY STALE COMPILING/RUNNING jobs (started_at < stale_cutoff)
            stale_subs = (
                db.query(Submission)
                .filter(
                    Submission.status.in_([SubmissionStatus.COMPILING.value, SubmissionStatus.RUNNING.value]),
                    Submission.started_at != None,
                    Submission.started_at < stale_cutoff
                )
                .all()
            )
            for sub in stale_subs:
                logger.info(f"Recovery: Resetting stale submission '{sub.id}' (started {sub.started_at}) to QUEUED")
                sub.status = SubmissionStatus.QUEUED.value
                db.commit()
                try:
                    self.redis_client.xadd(self.stream_name, {"submission_id": sub.id})
                except Exception as ex:
                    logger.error(f"Failed to re-enqueue reset submission '{sub.id}': {ex}")
        except Exception as ex:
            logger.error(f"Stale job recovery error: {ex}")
        finally:
            db.close()

    def reclaim_abandoned_stream_messages(self) -> None:
        """Uses XAUTOCLAIM to reclaim abandoned pending messages in consumer group."""
        try:
            min_idle_ms = int(settings.stale_job_timeout_seconds * 1000)
            res = self.redis_client.xautoclaim(
                name=self.stream_name,
                groupname=self.group_name,
                consumername=self.consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=10,
            )
            if res and len(res) > 1 and res[1]:
                for msg in res[1]:
                    msg_id = msg[0]
                    data = msg[1]
                    sub_id = data.get("submission_id") if isinstance(data, dict) else None
                    if sub_id:
                        logger.info(f"XAUTOCLAIM: Reclaimed pending message {msg_id} for submission '{sub_id}'")
                        if self.process_submission_id(sub_id):
                            self.redis_client.xack(self.stream_name, self.group_name, msg_id)
        except Exception as ex:
            logger.debug(f"XAUTOCLAIM notice: {ex}")

    def process_submission_id(self, submission_id: str) -> bool:
        """
        Atomically claims submission and invokes Judge evaluation pipeline.

        Returns:
            True if job was processed or already completed; False on retryable error.
        """
        db: Session = SessionLocal()
        try:
            # 1. Load submission from PostgreSQL
            sub = db.query(Submission).filter(Submission.id == submission_id).first()
            if not sub:
                logger.warning(f"Submission '{submission_id}' not found in DB. Skipping.")
                return True

            # 2. Idempotency Check: Skip terminal submissions
            if sub.status in TERMINAL_STATUSES:
                logger.info(f"Submission '{submission_id}' is already terminal ({sub.status}). ACK job.")
                return True

            # 3. Atomic DB Claiming (QUEUED -> COMPILING)
            now_utc = datetime.now(timezone.utc)
            stmt = text(
                "UPDATE submissions SET status = :new_status, started_at = :started_at "
                "WHERE id = :sub_id AND status = :old_status"
            )
            res = db.execute(
                stmt,
                {
                    "new_status": SubmissionStatus.COMPILING.value,
                    "started_at": now_utc,
                    "sub_id": submission_id,
                    "old_status": SubmissionStatus.QUEUED.value,
                },
            )
            db.commit()

            if res.rowcount == 0:
                logger.info(f"Submission '{submission_id}' claim failed (already claimed/non-QUEUED). Skipping.")
                return True

            # 4. Load Problem and TestCases
            problem = db.query(Problem).filter(Problem.id == sub.problem_id).first()
            if not problem:
                self._update_submission_result(
                    db, submission_id, SubmissionStatus.SYSTEM_ERROR.value, 0.0, "Associated problem not found.", None
                )
                return True

            testcases = (
                db.query(TestCase)
                .filter(TestCase.problem_id == sub.problem_id)
                .order_by(TestCase.id.asc())
                .all()
            )

            if not testcases:
                self._update_submission_result(
                    db, submission_id, SubmissionStatus.SYSTEM_ERROR.value, 0.0, "Problem has no testcases defined.", None
                )
                return True

            judge_tcs = [{"input": tc.input, "expected": tc.expected_output} for tc in testcases]

            # 5. Determine execution engine based on Docker daemon availability
            use_docker = is_docker_available()
            if use_docker:
                logger.info(f"Executing submission '{submission_id}' ({sub.language}) via Docker Sandbox Engine")
                executor = DockerExecutor(
                    policy=DEFAULT_SANDBOX_POLICY, submission_id=submission_id, test_index=0
                )
                use_docker_compiler = True
            else:
                logger.info(f"Docker unavailable on worker host. Executing submission '{submission_id}' ({sub.language}) via LocalExecutor using system binaries.")
                executor = LocalExecutor()
                use_docker_compiler = False

            comp_limits = CompileLimits(timeout_s=DEFAULT_SANDBOX_POLICY.compilation_timeout_seconds)
            exec_limits = ExecutionLimits(
                timeout_s=float(problem.time_limit_ms) / 1000.0 if problem.time_limit_ms else 2.0,
                max_output_bytes=DEFAULT_SANDBOX_POLICY.max_output_bytes,
            )

            judge = Judge(
                executor=executor,
                use_docker_compiler=use_docker_compiler,
                policy=DEFAULT_SANDBOX_POLICY,
            )

            # 6. Evaluate via Judge
            judge_res: JudgeResult = judge.evaluate(
                submission_id=submission_id,
                source_code=sub.source_code,
                testcases=judge_tcs,
                language=sub.language or "cpp",
                compile_limits=comp_limits,
                execution_limits=exec_limits,
            )

            tc_summary_list = [
                {
                    "testcase_index": tc_res.testcase_index,
                    "status": tc_res.status.value,
                    "duration_ms": round(tc_res.duration_ms, 2),
                }
                for tc_res in judge_res.testcase_results
            ]

            # 7. Persist Final Result to PostgreSQL
            self._update_submission_result(
                db=db,
                submission_id=submission_id,
                status_val=judge_res.status.value,
                execution_time_ms=judge_res.total_duration_ms,
                error_message=judge_res.error_message,
                tc_results=tc_summary_list,
            )
            return True

        except Exception as ex:
            logger.error(f"Error processing submission '{submission_id}': {ex}", exc_info=True)
            self._update_submission_result(
                db, submission_id, SubmissionStatus.SYSTEM_ERROR.value, 0.0, f"Worker error: {str(ex)}", None
            )
            return True
        finally:
            db.close()

    def _update_submission_result(
        self,
        db: Session,
        submission_id: str,
        status_val: str,
        execution_time_ms: float,
        error_message: Optional[str],
        tc_results: Optional[List[Dict[str, object]]] = None,
    ) -> None:
        """Helper to update final result in database."""
        try:
            sub = db.query(Submission).filter(Submission.id == submission_id).first()
            if sub:
                sub.status = status_val
                sub.execution_time_ms = round(execution_time_ms, 2)
                sub.error_message = error_message
                if tc_results is not None:
                    sub.testcase_results = tc_results
                sub.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Saved submission '{submission_id}' verdict: {status_val} ({execution_time_ms:.1f}ms)")
        except Exception as ex:
            db.rollback()
            logger.error(f"Failed to persist verdict for '{submission_id}': {ex}")

    def run(self, poll_once: bool = False) -> None:
        """
        Main worker listening loop.

        Args:
            poll_once: If True, exits after single queue drain (useful for tests).
        """
        try:
            init_db()
        except Exception as ex:
            logger.error(f"Worker DB initialization check error: {ex}")

        self.ensure_consumer_group()
        self.recover_stale_jobs()

        logger.info(f"Worker '{self.consumer_name}' listening on stream '{self.stream_name}'...")

        while True:
            try:
                self.reclaim_abandoned_stream_messages()

                response = self.redis_client.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=1,
                    block=2000,
                )

                if not response:
                    if poll_once:
                        break
                    continue

                for stream_key, messages in response:
                    for msg_id, data in messages:
                        sub_id = data.get("submission_id") if isinstance(data, dict) else None
                        if sub_id:
                            processed = self.process_submission_id(sub_id)
                            if processed:
                                self.redis_client.xack(self.stream_name, self.group_name, msg_id)

                if poll_once:
                    break

            except Exception as ex:
                logger.error(f"Worker main loop error: {ex}")
                time.sleep(1.0)
                if poll_once:
                    break


if __name__ == "__main__":
    worker = Worker()
    worker.run()
