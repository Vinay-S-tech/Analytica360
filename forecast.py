from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Sale
from utils.ml_model import forecast_revenue
from utils.auth_helper import get_current_user
import pandas as pd

router = APIRouter()

@router.get("")
def get_forecast(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    rows = db.query(Sale).filter(Sale.user_id == user_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No sales data. Upload a CSV first.")
    df = pd.DataFrame([{"sale_date": r.sale_date, "revenue": float(r.revenue)} for r in rows])
    try:
        return forecast_revenue(df, months_ahead=3)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
