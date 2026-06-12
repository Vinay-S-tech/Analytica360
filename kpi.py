from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.kpi_calculator import calculate_kpis
from utils.auth_helper import get_current_user
import os
import pandas as pd
from utils.kpi_calculator import calculate_kpis_from_dfs

router = APIRouter()

@router.get("/summary")
def get_kpi_summary(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return calculate_kpis(user_id, db)


@router.get("/guest")
def get_kpi_guest():
    """Compute KPIs from the sample_data CSV files for guest users."""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sample_dir = os.path.join(base, 'sample_data')
    if not os.path.isdir(sample_dir):
        return {"error": "Sample data not found on server."}

    dfs = []
    for fname in os.listdir(sample_dir):
        if not fname.lower().endswith('.csv'): continue
        path = os.path.join(sample_dir, fname)
        try:
            df = pd.read_csv(path)
            # Normalize columns similar to cleaner
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        return {"error": "No CSV sample data available."}

    try:
        return calculate_kpis_from_dfs(dfs)
    except Exception as e:
        return {"error": str(e)}
