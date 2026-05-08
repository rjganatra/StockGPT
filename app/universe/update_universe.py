import pandas as pd
from pathlib import Path

symbols = ["RELIANCE","TCS","INFY","HDFCBANK"]

df = pd.DataFrame({"symbol": symbols})

Path("data").mkdir(exist_ok=True)

df.to_csv("data/universe.csv", index=False)

print("Universe updated")
