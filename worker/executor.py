import subprocess
import tempfile
import os
import sys
import logging

logger = logging.getLogger(__name__)

class LocalExecutor:
    def execute(self, code: str, language: str, input_data: str, time_limit_ms: int = 2000):
        with tempfile.TemporaryDirectory() as tmpdir:
            if language.lower() in ["cpp", "c++"]:
                src_file = os.path.join(tmpdir, "solution.cpp")
                bin_file = os.path.join(tmpdir, "solution")
                with open(src_file, "w") as f:
                    f.write(code)
                
                compile_res = subprocess.run(["g++", "-O3", src_file, "-o", bin_file], capture_output=True, text=True)
                if compile_res.returncode != 0:
                    return {"verdict": "COMPILE_ERROR", "output": compile_res.stderr, "execution_time_ms": 0}
                
                exec_cmd = [bin_file]
            
            elif language.lower() in ["python", "python3", "py"]:
                src_file = os.path.join(tmpdir, "solution.py")
                with open(src_file, "w") as f:
                    f.write(code)
                exec_cmd = [sys.executable, src_file]
            
            else:
                return {"verdict": "SYSTEM_ERROR", "output": f"Unsupported language: {language}", "execution_time_ms": 0}

            try:
                proc_res = subprocess.run(
                    exec_cmd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=time_limit_ms / 1000.0
                )
                return {
                    "verdict": "OK",
                    "output": proc_res.stdout,
                    "error": proc_res.stderr,
                    "returncode": proc_res.returncode,
                    "execution_time_ms": 10
                }
            except subprocess.TimeoutExpired:
                return {"verdict": "TIME_LIMIT_EXCEEDED", "output": "", "execution_time_ms": time_limit_ms}
            except Exception as e:
                logger.exception("Execution crashed")
                return {"verdict": "SYSTEM_ERROR", "output": str(e), "execution_time_ms": 0}
