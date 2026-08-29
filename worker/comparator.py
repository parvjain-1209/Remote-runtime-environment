"""
Output Comparator Module.

Handles comparison between participant stdout output and expected ground truth testcase output.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonResult:
    """
    Result of comparing output against expected output.
    """
    matched: bool


class OutputComparator:
    """
    Deterministic output comparator.
    Normalizes trailing whitespace per line and trailing newlines.
    """

    def compare(self, actual_output: str, expected_output: str) -> ComparisonResult:
        """
        Compares actual output against expected output.

        Args:
            actual_output: Output captured from stdout.
            expected_output: Ground truth output for the testcase.

        Returns:
            ComparisonResult with matched boolean flag.
        """
        norm_actual = self._normalize(actual_output)
        norm_expected = self._normalize(expected_output)
        return ComparisonResult(matched=(norm_actual == norm_expected))

    def _normalize(self, text: str) -> str:
        """
        Strips right-hand whitespace from lines and trailing newlines from text.
        """
        if not text:
            return ""
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        # Strip trailing empty lines
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)
