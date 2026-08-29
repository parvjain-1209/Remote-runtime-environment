"""
Worker Multi-Language (Python & Java) Execution Unit Tests.
"""

import sys
import unittest
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "worker"
sys.path.insert(0, str(WORKER_DIR))

from compiler import compile_code
from executor import LocalExecutor
from judge import Judge
from workspace import SubmissionWorkspace


class TestMultiLanguagePipeline(unittest.TestCase):

    def setUp(self):
        self.executor = LocalExecutor()
        self.judge = Judge(executor=self.executor, use_docker_compiler=False)

    def test_python_valid_execution(self):
        py_code = (
            "import sys\n"
            "for line in sys.stdin:\n"
            "    parts = line.split()\n"
            "    if len(parts) >= 2:\n"
            "        print(int(parts[0]) + int(parts[1]))\n"
        )
        testcases = [{"input": "3 5\n", "expected": "8\n"}]
        res = self.judge.evaluate("sub-py-1", py_code, testcases, language="python")
        self.assertEqual(res.status.value, "ACCEPTED")
        self.assertEqual(len(res.testcase_results), 1)

    def test_python_syntax_error(self):
        invalid_py = "def main():\n  print('missing paren'\n"
        testcases = [{"input": "1 2\n", "expected": "3\n"}]
        res = self.judge.evaluate("sub-py-err", invalid_py, testcases, language="python")
        self.assertEqual(res.status.value, "COMPILATION_ERROR")

    def test_java_valid_execution(self):
        java_code = (
            "import java.util.Scanner;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        if (sc.hasNextInt()) {\n"
            "            int a = sc.nextInt();\n"
            "            int b = sc.nextInt();\n"
            "            System.out.println(a + b);\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        testcases = [{"input": "10 20\n", "expected": "30\n"}]
        res = self.judge.evaluate("sub-java-1", java_code, testcases, language="java")
        self.assertEqual(res.status.value, "ACCEPTED")
        self.assertEqual(len(res.testcase_results), 1)

    def test_java_compilation_error(self):
        invalid_java = "public class Main { public static void main(String[] args) { System.out.println(MISSING_VAR); } }"
        testcases = [{"input": "1 2\n", "expected": "3\n"}]
        res = self.judge.evaluate("sub-java-err", invalid_java, testcases, language="java")
        self.assertEqual(res.status.value, "COMPILATION_ERROR")


if __name__ == "__main__":
    unittest.main()
