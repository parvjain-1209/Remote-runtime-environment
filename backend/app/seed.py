"""
Problem Seeding Module for Remote Runtime Environment.
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
    {
        "id": 7,
        "title": "FizzBuzz",
        "difficulty": "Easy",
        "tags": "Math, Simulation",
        "description": "Write a program that takes an integer n from standard input and prints the numbers from 1 to n separated by space according to the following rules:\n- For multiples of 3, print \"Fizz\" instead of the number.\n- For multiples of 5, print \"Buzz\" instead of the number.\n- For numbers that are multiples of both 3 and 5, print \"FizzBuzz\".",
        "input_description": "A single integer n (1 <= n <= 1000).",
        "output_description": "Space-separated sequence of numbers and substitutions from 1 to n.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "5\n", "expected_output": "1 2 Fizz 4 Buzz\n", "is_sample": True},
            {"input": "15\n", "expected_output": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz\n", "is_sample": True},
            {"input": "1\n", "expected_output": "1\n", "is_sample": False},
            {"input": "3\n", "expected_output": "1 2 Fizz\n", "is_sample": False},
            {"input": "10\n", "expected_output": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz\n", "is_sample": False},
            {"input": "20\n", "expected_output": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz 16 17 Fizz 19 Buzz\n", "is_sample": False},
        ],
    },
    {
        "id": 8,
        "title": "Reverse String",
        "difficulty": "Easy",
        "tags": "String, Two Pointers",
        "description": "Given a single word string s from standard input, print the reversed string to standard output.",
        "input_description": "A single continuous string s without whitespace (1 <= |s| <= 10^5).",
        "output_description": "The reversed string.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "hello\n", "expected_output": "olleh\n", "is_sample": True},
            {"input": "algorithm\n", "expected_output": "mhtirogla\n", "is_sample": True},
            {"input": "a\n", "expected_output": "a\n", "is_sample": False},
            {"input": "racecar\n", "expected_output": "racecar\n", "is_sample": False},
            {"input": "RemoteRuntime\n", "expected_output": "emitnuRetomeR\n", "is_sample": False},
            {"input": "competitive\n", "expected_output": "evititepmoc\n", "is_sample": False},
        ],
    },
    {
        "id": 9,
        "title": "Find Maximum in Array",
        "difficulty": "Easy",
        "tags": "Array, Basics",
        "description": "Given an integer n followed by an array of n integers from standard input, find and print the maximum value in the array.",
        "input_description": "Line 1: A single integer n (1 <= n <= 10^5).\nLine 2: n space-separated integers a_1, a_2, ..., a_n (-10^9 <= a_i <= 10^9).",
        "output_description": "Single integer representing the maximum element in the array.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "5\n1 8 3 9 2\n", "expected_output": "9\n", "is_sample": True},
            {"input": "4\n-10 -3 -50 -2\n", "expected_output": "-3\n", "is_sample": True},
            {"input": "1\n42\n", "expected_output": "42\n", "is_sample": False},
            {"input": "5\n7 7 7 7 7\n", "expected_output": "7\n", "is_sample": False},
            {"input": "6\n-100 -200 -300 -400 -500 -50\n", "expected_output": "-50\n", "is_sample": False},
            {"input": "8\n10 20 30 40 50 60 70 80\n", "expected_output": "80\n", "is_sample": False},
        ],
    },
    {
        "id": 10,
        "title": "Palindrome Check",
        "difficulty": "Easy",
        "tags": "String, Two Pointers",
        "description": "Given a single string s from standard input, determine whether it is a palindrome. Print \"true\" if it is a palindrome, or \"false\" otherwise. A string is a palindrome if it reads the same forward and backward.",
        "input_description": "A single non-empty string s consisting of alphanumeric characters (1 <= |s| <= 10^5).",
        "output_description": "Print \"true\" or \"false\".",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "racecar\n", "expected_output": "true\n", "is_sample": True},
            {"input": "hello\n", "expected_output": "false\n", "is_sample": True},
            {"input": "a\n", "expected_output": "true\n", "is_sample": False},
            {"input": "abacaba\n", "expected_output": "true\n", "is_sample": False},
            {"input": "ab\n", "expected_output": "false\n", "is_sample": False},
            {"input": "noon\n", "expected_output": "true\n", "is_sample": False},
            {"input": "algorithm\n", "expected_output": "false\n", "is_sample": False},
        ],
    },
    {
        "id": 11,
        "title": "Valid Parentheses",
        "difficulty": "Medium",
        "tags": "Stack, String",
        "description": "Given a string s containing only the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\nAn input string is valid if:\n1. Open brackets must be closed by the same type of brackets.\n2. Open brackets must be closed in the correct order.\n3. Every close bracket has a corresponding open bracket of the same type.",
        "input_description": "A single non-empty string s consisting solely of bracket characters (1 <= |s| <= 10^4).",
        "output_description": "Print \"true\" if the brackets are valid, or \"false\" otherwise.",
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
        "testcases": [
            {"input": "()[]{}\n", "expected_output": "true\n", "is_sample": True},
            {"input": "(]\n", "expected_output": "false\n", "is_sample": True},
            {"input": "([)]\n", "expected_output": "false\n", "is_sample": False},
            {"input": "{[]}\n", "expected_output": "true\n", "is_sample": False},
            {"input": "((()))\n", "expected_output": "true\n", "is_sample": False},
            {"input": "]\n", "expected_output": "false\n", "is_sample": False},
            {"input": "(()\n", "expected_output": "false\n", "is_sample": False},
        ],
    },
]


def seed_problems(db: Session) -> None:
    """
    Seeds problem catalog into database. Updates existing records or adds missing ones.
    """
    for pdata in SEED_PROBLEMS:
        tc_data_list = pdata.get("testcases", [])
        field_data = {k: v for k, v in pdata.items() if k != "testcases"}
        existing_prob = db.query(Problem).filter(Problem.id == field_data["id"]).first()

        if existing_prob:
            existing_prob.title = field_data["title"]
            existing_prob.difficulty = field_data["difficulty"]
            existing_prob.tags = field_data["tags"]
            existing_prob.description = field_data["description"]
            existing_prob.input_description = field_data["input_description"]
            existing_prob.output_description = field_data["output_description"]
            existing_prob.time_limit_ms = field_data["time_limit_ms"]
            existing_prob.memory_limit_mb = field_data["memory_limit_mb"]
            prob_id = existing_prob.id
        else:
            prob = Problem(**field_data)
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
