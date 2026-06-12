import json
import os

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Sale, Upload, User
from utils.auth_helper import get_current_user
from utils.data_cleaner import clean_sales_csv

router = APIRouter()


@router.get('/samples')
def list_samples():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sample_dir = os.path.join(base, 'sample_data')
    if not os.path.isdir(sample_dir):
        return JSONResponse({'samples': []})
    samples = [f for f in os.listdir(sample_dir) if f.lower().endswith('.csv')]
    return JSONResponse({'samples': samples})


@router.get('/sample/{name}')
def get_sample(name: str):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sample_dir = os.path.join(base, 'sample_data')
    safe = os.path.basename(name)
    path = os.path.join(sample_dir, safe)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='Sample not found')
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        return JSONResponse({'filename': safe, 'content': content})
    except Exception:
        raise HTTPException(status_code=500, detail='Unable to read sample file')



@router.post('/import-sample/{name}')
def import_sample(name: str, db: Session = Depends(get_db)):
    """Import a named sample CSV into the DB under a guest user (guest@local)."""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sample_dir = os.path.join(base, 'sample_data')
    safe = os.path.basename(name)
    path = os.path.join(sample_dir, safe)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='Sample not found')

    with open(path, 'rb') as fh:
        contents = fh.read()

    try:
        df = clean_sales_csv(contents, mapping=None)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # find or create guest user
    guest_email = 'guest@local'
    guest = db.query(User).filter(User.email == guest_email).first()
    if not guest:
        guest = User(name='Guest', email=guest_email, password='')
        db.add(guest)
        db.commit()
        db.refresh(guest)

    # insert sales
    records = []
    for _, row in df.iterrows():
        records.append(Sale(
            user_id=guest.id,
            sale_date=row['sale_date'],
            product=row['product'],
            category=row.get('category','Unknown'),
            region=row.get('region','Unknown'),
            quantity=(int(row['quantity']) if not pd.isna(row.get('quantity')) else 1),
            revenue=float(row['revenue']),
            profit=(float(row['profit']) if not pd.isna(row.get('profit')) else 0.0),
        ))

    if records:
        db.bulk_save_objects(records)
        db.add(Upload(user_id=guest.id, filename=safe, rows_imported=len(records)))
        db.commit()

    return JSONResponse({'message': f'Imported {len(records)} rows into guest account', 'rows': len(records)})

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
    mapping: str = Form(None)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    contents = await file.read()
    # parse optional mapping sent from the frontend (JSON string)
    mapping_obj = None
    if mapping:
        try:
            mapping_obj = json.loads(mapping)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid mapping JSON.")

    try:
        df = clean_sales_csv(contents, mapping=mapping_obj)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.query(Sale).filter(Sale.user_id == user_id).delete()
    records = [
        Sale(
            user_id=user_id,
            sale_date=row["sale_date"],
            product=row["product"],
            category=row.get("category", "Unknown"),
            region=row.get("region", "Unknown"),
            quantity=(int(row['quantity']) if not pd.isna(row.get('quantity')) else 1),
            revenue=float(row['revenue']),
            profit=(float(row['profit']) if not pd.isna(row.get('profit')) else 0.0),
        )
        for _, row in df.iterrows()
    ]
    db.bulk_save_objects(records)
    db.add(Upload(user_id=user_id, filename=file.filename, rows_imported=len(records)))
    db.commit()
    return {"message": f"Uploaded successfully! {len(records)} rows imported.", "rows": len(records)}
