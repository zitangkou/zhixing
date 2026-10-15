"""Verify the server-side quick-calculation generator over varied seeds."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ziliao_quick_calc_service import METHODS, _generate, _validate_questions


checked = 0
for method in METHODS:
    code = method["code"]
    for seed in range(500):
        question = _generate(code, {"min": 1000, "max": 9000, "difficulty": seed % 5 + 1}, random.Random(seed))
        _validate_questions([question])
        assert len(question["options"]) == 4
        assert len(set(question["options"])) == 4
        checked += 1

print(f"server quick-calc generator passed: {checked} generated questions")
