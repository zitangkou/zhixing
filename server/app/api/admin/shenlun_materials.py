"""人民日报申论素材管理。"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import ShenlunMaterial
from app.schemas.shenlun_materials import ShenlunMaterialImport, ShenlunMaterialSave
from app.services.shenlun_materials import RULES, normalize, out, preview, save

router = APIRouter(prefix='/shenlun-materials', tags=['申论素材'])

@router.get('/rules')
def rules(admin=Depends(require_permission('rmrb:read'))):
    return ApiResponse.ok(RULES)

@router.get('')
def listing(start: date|None=None, end: date|None=None, q: str='', theme: str='', item_type: str='', status: str='',
            page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100),
            admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    query=db.query(ShenlunMaterial)
    if start: query=query.filter(ShenlunMaterial.source_date>=start)
    if end: query=query.filter(ShenlunMaterial.source_date<=end)
    if q: query=query.filter(or_(ShenlunMaterial.text.contains(q),ShenlunMaterial.source_title.contains(q),ShenlunMaterial.payload_json.contains(q)))
    if theme: query=query.filter(ShenlunMaterial.theme_code==theme)
    if item_type: query=query.filter(ShenlunMaterial.item_type==item_type)
    if status: query=query.filter(ShenlunMaterial.review_status==status)
    total=query.count()
    rows=query.order_by(ShenlunMaterial.source_date.desc(),ShenlunMaterial.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    stats={key:db.query(ShenlunMaterial.id).filter(ShenlunMaterial.review_status==key).count() for key in ('pending','confirmed','rejected')}
    return ApiResponse.ok({'items':[out(x) for x in rows], 'total':total, 'stats':stats})

@router.get('/export')
def export(start: date|None=None,end: date|None=None,admin=Depends(require_permission('rmrb:read')),db: Session=Depends(get_db)):
    q=db.query(ShenlunMaterial)
    if start:q=q.filter(ShenlunMaterial.source_date>=start)
    if end:q=q.filter(ShenlunMaterial.source_date<=end)
    return ApiResponse.ok([out(x) for x in q.order_by(ShenlunMaterial.source_date,ShenlunMaterial.id).all()])

@router.get('/{material_id}')
def detail(material_id: str,admin=Depends(require_permission('rmrb:read')),db: Session=Depends(get_db)):
    row=db.get(ShenlunMaterial,material_id)
    return ApiResponse.ok(out(row)) if row else ApiResponse.fail('申论素材不存在',code=404)

@router.post('/import-preview')
def import_preview(body: ShenlunMaterialImport,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    return ApiResponse.ok(preview(db,body.items,body.collected_date))

@router.post('/import')
def import_items(body: ShenlunMaterialImport,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    checked=preview(db,body.items,body.collected_date)
    invalid=[x for x in checked if x['status']=='invalid']
    if invalid:return ApiResponse.fail(f"第 {invalid[0]['index']} 条校验失败：{invalid[0]['error']}",code=400)
    added=0; skipped=0
    try:
        for index,item in enumerate(body.items):
            if checked[index]['status']=='duplicate': skipped+=1; continue
            values=normalize(item,body.collected_date,admin.username)
            if db.query(ShenlunMaterial.id).filter_by(fingerprint=values['fingerprint']).first(): skipped+=1; continue
            db.add(ShenlunMaterial(**values)); added+=1
        db.commit()
    except (ValueError,IntegrityError) as exc:
        db.rollback(); return ApiResponse.fail(str(exc) if isinstance(exc,ValueError) else '导入数据重复或冲突，请刷新预览',code=400)
    return ApiResponse.ok({'added':added,'skipped':skipped})

def persist(body,db,admin,row=None):
    try:return ApiResponse.ok(out(save(db,body.item,body.collected_date,admin.username,row)))
    except (ValueError,IntegrityError) as exc:
        db.rollback(); return ApiResponse.fail(str(exc) if isinstance(exc,ValueError) else '重复素材无法保存',code=400)

@router.post('')
def create(body: ShenlunMaterialSave,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    return persist(body,db,admin)

@router.put('/{material_id}')
def update(material_id: str,body: ShenlunMaterialSave,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    row=db.get(ShenlunMaterial,material_id)
    return persist(body,db,admin,row) if row else ApiResponse.fail('申论素材不存在',code=404)

@router.delete('/{material_id}')
def delete(material_id: str,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    row=db.get(ShenlunMaterial,material_id)
    if not row:return ApiResponse.fail('申论素材不存在',code=404)
    db.delete(row);db.commit();return ApiResponse.ok({'deleted':material_id})
