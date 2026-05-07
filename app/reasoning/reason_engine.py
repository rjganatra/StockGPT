def build_reason_output(symbol, score_data):

    return {
        "symbol": symbol,
        "score": score_data["score"],
        "reasons": score_data["reasons"]
    }
