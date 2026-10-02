import pandas as pd
df = pd.read_csv("data/sample/SuperStore_Sales_Dataset.csv")
print("Regions:", df["Region"].unique())
print("Customer in West only:")
w_custs = set(df[df["Region"] == "West"]["Customer Name"])
s_custs = set(df[df["Region"] == "South"]["Customer Name"])
west_only = list(w_custs - s_custs)
print(f"West only customer count: {len(west_only)}, example: {west_only[0]}")
