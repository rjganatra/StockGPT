import pandas as pd

def run_swing_scan(data):

    results = data[
        (data["distance_from_52w_low"] <= 30)
        & (data["relative_volume"] >= 1.5)
    ]

    return results
