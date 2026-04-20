def check_marks(quality_score):
    if quality_score >= 81:
        return 5
    elif quality_score >= 61:
        return 4
    elif quality_score >= 41:
        return 3
    elif quality_score >= 21:
        return 2
    elif quality_score > 0:
        return 1
    else:
        return 0

test_cases = [
    (95, 5),
    (90, 5),
    (81, 5),
    (80, 4),
    (61, 4),
    (60, 3),
    (41, 3),
    (40, 2),
    (21, 2),
    (20, 1),
    (5, 1),
    (0, 0)
]

for q, expected in test_cases:
    actual = check_marks(q)
    print(f"Quality: {q} -> Marks: {actual} (Expected: {expected})")
    assert actual == expected
    
print("\nALL MARKING LOGIC TESTS PASSED!")
