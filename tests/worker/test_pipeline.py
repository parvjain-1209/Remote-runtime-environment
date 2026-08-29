"""
Phase 2 Test Suite for C++ Compile, Execute, and Judge Pipeline.
Uses standard library unittest.
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Add worker and backend to Python path
WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "worker"
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app.models.submission import SubmissionStatus
from compiler import compile_cpp
from executor import LocalExecutor, ExecutionLimits
from judge import Judge
from sandbox_policy import CompileLimits, SandboxPolicy
from workspace import SubmissionWorkspace


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.executor = LocalExecutor()
        self.judge = Judge(executor=self.executor)

    # Test A: Successful Compilation
    def test_successful_compilation(self):
        code = """
        #include <iostream>
        int main() {
            std::cout << "Hello World";
            return 0;
        }
        """
        with SubmissionWorkspace() as ws:
            ws.write_source(code)
            res = compile_cpp(ws.source_path, ws.binary_path, CompileLimits(timeout_s=10.0))
            self.assertTrue(res.success)
            self.assertFalse(res.timed_out)
            self.assertTrue(ws.binary_path.exists())

    # Test B: Compilation Error
    def test_compilation_error(self):
        code = "int main() { std::cout << missing_variable; return 0; }"
        with SubmissionWorkspace() as ws:
            ws.write_source(code)
            res = compile_cpp(ws.source_path, ws.binary_path, CompileLimits(timeout_s=10.0))
            self.assertFalse(res.success)
            self.assertTrue("error" in res.stderr.lower() or "missing_variable" in res.stderr)
            self.assertFalse(res.timed_out)

    # Test C: Successful Execution & Correct Output (Addition)
    def test_successful_execution(self):
        code = """
        #include <iostream>
        int main() {
            int a, b;
            if (std::cin >> a >> b) {
                std::cout << a + b;
            }
            return 0;
        }
        """
        testcases = [
            {"input": "2 3\n", "expected": "5\n"},
            {"input": "10 20\n", "expected": "30\n"},
        ]
        res = self.judge.evaluate("sub-101", code, testcases)
        self.assertEqual(res.status, SubmissionStatus.ACCEPTED)
        self.assertEqual(len(res.testcase_results), 2)
        self.assertTrue(res.testcase_results[0].matched)
        self.assertTrue(res.testcase_results[1].matched)

    # Test D: Wrong Output
    def test_wrong_output(self):
        code = """
        #include <iostream>
        int main() {
            int a, b;
            if (std::cin >> a >> b) {
                std::cout << a * b; // Wrong operation
            }
            return 0;
        }
        """
        testcases = [{"input": "2 3\n", "expected": "5\n"}]
        res = self.judge.evaluate("sub-102", code, testcases)
        self.assertEqual(res.status, SubmissionStatus.WRONG_ANSWER)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.WRONG_ANSWER)
        self.assertFalse(res.testcase_results[0].matched)

    # Test E: Runtime Error (Division by Zero / Exception)
    def test_runtime_error_exception(self):
        code = """
        #include <iostream>
        #include <stdexcept>
        int main() {
            throw std::runtime_error("Simulated runtime failure");
            return 0;
        }
        """
        testcases = [{"input": "", "expected": ""}]
        res = self.judge.evaluate("sub-103", code, testcases)
        self.assertEqual(res.status, SubmissionStatus.RUNTIME_ERROR)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.RUNTIME_ERROR)

    # Test F: Timeout (Infinite Loop) & Process Group Cleanup
    def test_timeout_handling(self):
        code = """
        #include <iostream>
        int main() {
            while (true) {
                // Infinite loop
            }
            return 0;
        }
        """
        testcases = [{"input": "", "expected": ""}]
        limits = ExecutionLimits(timeout_s=0.5, max_output_bytes=1024*1024)

        start_time = time.monotonic()
        res = self.judge.evaluate("sub-104", code, testcases, execution_limits=limits)
        elapsed = time.monotonic() - start_time

        self.assertEqual(res.status, SubmissionStatus.TIME_LIMIT_EXCEEDED)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.TIME_LIMIT_EXCEEDED)
        self.assertTrue(res.testcase_results[0].execution_result.timed_out)
        self.assertLess(elapsed, 2.0)

    # Test G: Output Limit Exceeded
    def test_output_limit_exceeded(self):
        code = """
        #include <iostream>
        int main() {
            while (true) {
                std::cout << "AAAAAAAAAA";
            }
            return 0;
        }
        """
        testcases = [{"input": "", "expected": ""}]
        limits = ExecutionLimits(timeout_s=3.0, max_output_bytes=10 * 1024) # 10 KB limit

        res = self.judge.evaluate("sub-105", code, testcases, execution_limits=limits)
        self.assertEqual(res.status, SubmissionStatus.OUTPUT_LIMIT_EXCEEDED)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.OUTPUT_LIMIT_EXCEEDED)
        self.assertTrue(res.testcase_results[0].execution_result.output_limit_exceeded)
        self.assertLessEqual(len(res.testcase_results[0].execution_result.stdout), 10 * 1024 + 100)

    # Test H: Non-Zero Normal Exit Code (e.g., return 1;)
    def test_non_zero_exit_code(self):
        code = """
        #include <iostream>
        int main() {
            return 1; // Non-zero exit code
        }
        """
        testcases = [{"input": "", "expected": ""}]
        res = self.judge.evaluate("sub-106", code, testcases)
        
        # Should NOT be treated as WRONG_ANSWER by executor; mapped to RUNTIME_ERROR
        self.assertEqual(res.status, SubmissionStatus.RUNTIME_ERROR)
        self.assertEqual(res.testcase_results[0].execution_result.return_code, 1)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.RUNTIME_ERROR)

    # Test I: Multiple Testcases with Short-Circuiting
    def test_multiple_testcases_short_circuit(self):
        code = """
        #include <iostream>
        int main() {
            int x;
            std::cin >> x;
            if (x == 1) std::cout << "PASS";
            else if (x == 2) std::cout << "FAIL";
            else std::cout << "PASS";
            return 0;
        }
        """
        testcases = [
            {"input": "1\n", "expected": "PASS\n"},
            {"input": "2\n", "expected": "PASS\n"}, # Fails here
            {"input": "3\n", "expected": "PASS\n"},
        ]
        res = self.judge.evaluate("sub-107", code, testcases)
        self.assertEqual(res.status, SubmissionStatus.WRONG_ANSWER)
        self.assertEqual(len(res.testcase_results), 2)
        self.assertEqual(res.testcase_results[0].status, SubmissionStatus.ACCEPTED)
        self.assertEqual(res.testcase_results[1].status, SubmissionStatus.WRONG_ANSWER)


if __name__ == "__main__":
    unittest.main()
