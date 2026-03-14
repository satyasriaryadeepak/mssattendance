from datetime import datetime, timedelta, timezone

def test_logic():
    # Deadlines as integers: 10:10 -> 1010, 14:10 -> 1410, 13:45 -> 1345
    morning_deadline_val = 1010
    afternoon_start_val = 1345
    afternoon_deadline_val = 1410

    test_cases = [
        {"time": "09:00", "desc": "Morning Early", "period": "morning", "expected": True},
        {"time": "10:10", "desc": "Morning On Deadline", "period": "morning", "expected": True},
        {"time": "10:11", "desc": "Morning Late", "period": "morning", "expected": False},
        {"time": "13:30", "desc": "Afternoon Early", "period": "afternoon", "expected": "Too Early"},
        {"time": "13:45", "desc": "Afternoon Start", "period": "afternoon", "expected": True},
        {"time": "14:10", "desc": "Afternoon On Deadline", "period": "afternoon", "expected": True},
        {"time": "14:11", "desc": "Afternoon Late", "period": "afternoon", "expected": False},
    ]

    print(f"{'Time':<8} | {'Description':<20} | {'Period':<10} | {'Result'}")
    print("-" * 55)

    for case in test_cases:
        h, m = map(int, case["time"].split(":"))
        val_now = h * 100 + m
        
        result = "FAIL"
        if case["period"] == "morning":
            if val_now <= morning_deadline_val:
                result = "Marked" if case["expected"] is True else "FAIL"
            else:
                result = "Already Marked/Late" if case["expected"] is False else "FAIL"
        
        elif case["period"] == "afternoon":
            if val_now < afternoon_start_val:
                result = "Too Early" if case["expected"] == "Too Early" else "FAIL"
            elif val_now <= afternoon_deadline_val:
                result = "Marked" if case["expected"] is True else "FAIL"
            else:
                result = "Already Marked/Late" if case["expected"] is False else "FAIL"

        print(f"{case['time']:<8} | {case['desc']:<20} | {case['period']:<10} | {result}")

if __name__ == "__main__":
    test_logic()
