import pandas as pd
from sklearn.linear_model import LinearRegression
from dateutil.relativedelta import relativedelta

def forecast_revenue(df: pd.DataFrame, months_ahead: int = 3) -> dict:
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["month"]     = df["sale_date"].dt.to_period("M")
    monthly         = df.groupby("month")["revenue"].sum().reset_index().sort_values("month")

    if len(monthly) < 3:
        raise ValueError("Need at least 3 months of sales data to forecast.")

    monthly["month_num"] = range(len(monthly))
    X = monthly[["month_num"]].values
    y = monthly["revenue"].values

    model = LinearRegression()
    model.fit(X, y)

    last_num  = monthly["month_num"].max()
    last_date = monthly["month"].max().to_timestamp()

    predictions = []
    for i in range(1, months_ahead + 1):
        future_date = last_date + relativedelta(months=i)
        predicted   = max(0, round(float(model.predict([[last_num + i]])[0]), 2))
        predictions.append({"month": future_date.strftime("%Y-%m"), "predicted_revenue": predicted})

    historical = [{"month": str(row["month"]), "revenue": round(float(row["revenue"]), 2)}
                  for _, row in monthly.iterrows()]

    return {
        "historical": historical,
        "forecast":   predictions,
        "model":      "LinearRegression",
        "r2_score":   round(float(model.score(X, y)), 3),
    }
