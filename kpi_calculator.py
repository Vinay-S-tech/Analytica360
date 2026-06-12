import pandas as pd
from sqlalchemy.orm import Session
from models import Sale

def calculate_kpis(user_id: int, db: Session) -> dict:
    rows = db.query(Sale).filter(Sale.user_id == user_id).all()
    if not rows:
        return {"error": "No sales data found. Please upload a CSV first."}

    df = pd.DataFrame([{
        "sale_date": r.sale_date, "product": r.product,
        "category": r.category,  "region": r.region,
        "quantity": float(r.quantity), "revenue": float(r.revenue), "profit": float(r.profit),
    } for r in rows])

    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["month"]     = df["sale_date"].dt.to_period("M")

    total_revenue = round(df["revenue"].sum(), 2)
    total_profit  = round(df["profit"].sum(), 2)
    profit_margin = round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0

    monthly = df.groupby("month")["revenue"].sum().sort_index()
    if len(monthly) >= 2:
        growth_pct = round(((float(monthly.iloc[-1]) - float(monthly.iloc[-2])) / float(monthly.iloc[-2])) * 100, 1)
    else:
        growth_pct = 0

    top_products = (df.groupby("product")["revenue"].sum().sort_values(ascending=False)
                    .head(5).reset_index().rename(columns={"revenue": "total_revenue"}).to_dict("records"))

    region_sales = (df.groupby("region")["revenue"].sum()
                    .reset_index().rename(columns={"revenue": "total_revenue"}).to_dict("records"))

    monthly_trend = [{"month": str(m), "revenue": round(float(v), 2)} for m, v in monthly.items()]

    return {
        "total_revenue": total_revenue, "total_profit": total_profit,
        "profit_margin": profit_margin, "monthly_growth": growth_pct,
        "top_products": top_products,   "region_sales": region_sales,
        "monthly_trend": monthly_trend, "total_records": len(df),
    }


def calculate_kpis_from_dfs(dfs: list) -> dict:
    """Calculate KPIs from a list of pandas DataFrames (used for guest/sample data)."""
    import pandas as pd
    processed = []
    rename_map = {
        'date': 'sale_date', 'order_date': 'sale_date', 'timestamp': 'sale_date',
        'sales': 'revenue', 'total': 'revenue', 'revenue': 'revenue',
        'item': 'product', 'product_name': 'product'
    }
    for raw in dfs:
        d = raw.copy()
        d.columns = d.columns.str.strip().str.lower().str.replace(' ', '_')
        d.rename(columns={k: v for k, v in rename_map.items() if k in d.columns}, inplace=True)
        # continue if essential columns missing in this particular file
        if not ({'sale_date','product','revenue'} & set(d.columns)):
            continue
        # keep only expected columns to avoid duplicate/ambiguous ones
        keep = [c for c in ['sale_date','product','category','region','quantity','revenue','profit'] if c in d.columns]
        d = d[keep]
        # coerce types
        d = d.dropna(subset=['sale_date','product','revenue'])
        d['sale_date'] = pd.to_datetime(d['sale_date'], errors='coerce')
        d = d.dropna(subset=['sale_date'])
        d['sale_date'] = d['sale_date'].dt.date
        for col in ['revenue','profit','quantity']:
            if col in d.columns:
                d[col] = pd.to_numeric(d[col], errors='coerce')
        processed.append(d)

    if not processed:
        raise ValueError('Sample data must contain sale_date, product and revenue columns (or mappable variants).')

    df = pd.concat(processed, ignore_index=True, sort=False)

    for col in ['revenue','profit','quantity']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['quantity'] = df.get('quantity', pd.Series(dtype=float)).fillna(1).astype(int)
    df['profit']   = df.get('profit', pd.Series(dtype=float)).fillna(0.0)
    df['category'] = df.get('category', pd.Series(dtype=str)).fillna('Unknown')
    df['region']   = df.get('region', pd.Series(dtype=str)).fillna('Unknown')

    # reuse existing aggregator logic by converting df to expected structure
    df2 = df.copy()
    df2['sale_date'] = pd.to_datetime(df2['sale_date'])
    df2['month'] = df2['sale_date'].dt.to_period('M')

    total_revenue = round(df2['revenue'].sum(), 2)
    total_profit  = round(df2['profit'].sum(), 2)
    profit_margin = round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0

    monthly = df2.groupby('month')['revenue'].sum().sort_index()
    if len(monthly) >= 2:
        growth_pct = round(((float(monthly.iloc[-1]) - float(monthly.iloc[-2])) / float(monthly.iloc[-2])) * 100, 1)
    else:
        growth_pct = 0

    top_products = (df2.groupby('product')['revenue'].sum().sort_values(ascending=False)
                    .head(5).reset_index().rename(columns={'revenue':'total_revenue'}).to_dict('records'))

    region_sales = (df2.groupby('region')['revenue'].sum()
                    .reset_index().rename(columns={'revenue':'total_revenue'}).to_dict('records'))

    monthly_trend = [{'month': str(m), 'revenue': round(float(v), 2)} for m, v in monthly.items()]

    return {
        'total_revenue': total_revenue, 'total_profit': total_profit,
        'profit_margin': profit_margin, 'monthly_growth': growth_pct,
        'top_products': top_products, 'region_sales': region_sales,
        'monthly_trend': monthly_trend, 'total_records': len(df2),
    }
