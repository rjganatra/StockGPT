def calculate_score(stock_data):

    score = 0
    reasons = []

    if stock_data.get("eps_growth", 0) > 10:
        score += 20
        reasons.append("Strong EPS growth")

    if stock_data.get("cfo_positive", False):
        score += 20
        reasons.append("Positive CFO trend")

    if stock_data.get("low_debt", False):
        score += 15
        reasons.append("Low debt")

    if stock_data.get("near_52w_low", False):
        score += 10
        reasons.append("Near 52W low")

    return {
        "score": score,
        "reasons": reasons
    }
