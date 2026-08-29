"""
Problem Seeding Module for GDG Remote Runtime.
Populates initial catalog of algorithmic problems and testcases.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.testcase import TestCase


SEED_PROBLEMS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Sum of Two Numbers",
        "difficulty": "Easy",
        "tags": "Math, Basics",
        "description": "Write a program that takes two space-separated integers from stdin and prints their sum to stdout.",
        "input_description": "Two space-separated integers a and b.",
        "output_description": "Single integer representing a + b.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "2 3\n", "expected_output": "5\n", "is_sample": True},
            {"input": "100 200\n", "expected_output": "300\n", "is_sample": True},
            {"input": "-5 15\n", "expected_output": "10\n", "is_sample": False},
            {"input": "1000000 2000000\n", "expected_output": "3000000\n", "is_sample": False},
            {"input": "-50 -50\n", "expected_output": "-100\n", "is_sample": False},
        ],
    },
    {
        "id": 2,
        "title": "Maximum of Two Numbers",
        "difficulty": "Easy",
        "tags": "Math, Conditionals",
        "description": "Write a program that reads two space-separated integers from stdin and prints the larger of the two numbers to stdout.",
        "input_description": "Two space-separated integers a and b.",
        "output_description": "Single integer representing max(a, b).",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "7 12\n", "expected_output": "12\n", "is_sample": True},
            {"input": "-3 -8\n", "expected_output": "-3\n", "is_sample": False},
            {"input": "100 100\n", "expected_output": "100\n", "is_sample": False},
            {"input": "0 -15\n", "expected_output": "0\n", "is_sample": False},
        ],
    },
    {
        "id": 3,
        "title": "Reverse a Number",
        "difficulty": "Easy",
        "tags": "Math, Digits",
        "description": "Given a signed integer n from stdin, reverse its digits. If n is negative, the reversed integer must also remain negative.",
        "input_description": "A single signed integer n.",
        "output_description": "Single integer with reversed digits.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "1234\n", "expected_output": "4321\n", "is_sample": True},
            {"input": "-567\n", "expected_output": "-765\n", "is_sample": True},
            {"input": "1200\n", "expected_output": "21\n", "is_sample": False},
            {"input": "0\n", "expected_output": "0\n", "is_sample": False},
            {"input": "-90\n", "expected_output": "-9\n", "is_sample": False},
        ],
    },
    {
        "id": 4,
        "title": "Palindrome Number",
        "difficulty": "Easy",
        "tags": "Math, String",
        "description": "Given an integer n from stdin, print \"true\" if n is a palindrome, and \"false\" otherwise. An integer is a palindrome when it reads the same backward as forward.",
        "input_description": "A single integer n.",
        "output_description": "Print \"true\" or \"false\".",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "121\n", "expected_output": "true\n", "is_sample": True},
            {"input": "-121\n", "expected_output": "false\n", "is_sample": True},
            {"input": "10\n", "expected_output": "false\n", "is_sample": False},
            {"input": "12321\n", "expected_output": "true\n", "is_sample": False},
            {"input": "7\n", "expected_output": "true\n", "is_sample": False},
        ],
    },
    {
        "id": 5,
        "title": "Two Sum",
        "difficulty": "Medium",
        "tags": "Array, Hash Table",
        "description": "Given an array of integers nums and an integer target, return the 0-based indices of the two numbers such that they add up to target.",
        "input_description": "Line 1: N (array length) and Target separated by space.\nLine 2: N space-separated integers.",
        "output_description": "Two 0-based indices separated by a space.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "4 9\n2 7 11 15\n", "expected_output": "0 1\n", "is_sample": True},
            {"input": "3 6\n3 2 4\n", "expected_output": "1 2\n", "is_sample": True},
            {"input": "2 6\n3 3\n", "expected_output": "0 1\n", "is_sample": False},
            {"input": "5 10\n1 4 5 6 9\n", "expected_output": "1 3\n", "is_sample": False},
        ],
    },
    {
        "id": 6,
        "title": "Binary Search",
        "difficulty": "Medium",
        "tags": "Binary Search, Array",
        "description": "Given an array of N integers sorted in ascending order and a target value, search for target in nums. Print its 0-based index if target exists, or -1 otherwise.",
        "input_description": "Line 1: N and Target separated by space.\nLine 2: N sorted space-separated integers.",
        "output_description": "Single integer: 0-based index of target, or -1 if not found.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "6 9\n-1 0 3 5 9 12\n", "expected_output": "4\n", "is_sample": True},
            {"input": "6 2\n-1 0 3 5 9 12\n", "expected_output": "-1\n", "is_sample": True},
            {"input": "1 5\n5\n", "expected_output": "0\n", "is_sample": False},
            {"input": "5 10\n1 3 5 7 9\n", "expected_output": "-1\n", "is_sample": False},
            {"input": "4 4\n1 2 3 4\n", "expected_output": "3\n", "is_sample": False},
        ],
    },
]


def seed_problems(db: Session) -> None:
    """
    Seeds problem catalog into database. Updates existing records or adds missing ones.
    """
    for pdata in SEED_PROBLEMS:
        tc_data_list = pdata.pop("testcases")
        existing_prob = db.query(Problem).filter(Problem.id == pdata["id"]).first()

        if existing_prob:
            existing_prob.title = pdata["title"]
            existing_prob.difficulty = pdata["difficulty"]
            existing_prob.tags = pdata["tags"]
            existing_prob.description = pdata["description"]
            existing_prob.input_description = pdata["input_description"]
            existing_prob.output_description = pdata["output_description"]
            existing_prob.time_limit_ms = pdata["time_limit_ms"]
            existing_prob.memory_limit_mb = pdata["memory_limit_mb"]
            prob_id = existing_prob.id
        else:
            prob = Problem(**pdata)
            db.add(prob)
            db.flush()
            prob_id = prob.id

        # Re-populate testcases for this problem
        db.query(TestCase).filter(TestCase.problem_id == prob_id).delete()
        for tc_data in tc_data_list:
            tc = TestCase(
                problem_id=prob_id,
                input=tc_data["input"],
                expected_output=tc_data["expected_output"],
                is_sample=tc_data["is_sample"],
            )
            db.add(tc)

    db.commit()
