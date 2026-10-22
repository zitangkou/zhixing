"""创意平台管理 API；所有对象按所有者或显式共享范围过滤。"""
import json
import re
import hashlib
import secrets
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import UploadFile, File, Header
from datetime import datetime, timedelta
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AdminUser, utcnow, CreativeIdea, CreativeTag, CreativeIdeaTag, CreativeMaterial, CreativeIdeaMaterial, CreativeIdeaRelation, CreativePractice, CreativeEvent, CreativeCaptureRequest, CreativeAttachment
from app.schemas.creative import IdeaCreate, IdeaPatch, TransitionBody, CaptureBody, MaterialIn, MaterialPatch, PracticeIn, TagIn, STATUSES
from app.services.serializers import parse_json
from app.upload_paths import DATA_DIR

router = APIRouter()

def can_manage(admin: AdminUser, idea: CreativeIdea) -> bool:
    perms=parse_json(admin.role.permissions, []) if admin.role else []
    return idea.owner_id == admin.id or (idea.visibility == "shared" and (admin.role.code == "super_admin" or "creative:manage" in perms or "*" in perms))

def idea_query(db: Session, admin: AdminUser):
    perms=parse_json(admin.role.permissions, []) if admin.role else []
    can_manage_shared=bool(admin.role and admin.role.code=="super_admin") or "creative:manage" in perms or "*" in perms
    shared_scope=and_(CreativeIdea.visibility=="shared",or_(CreativeIdea.archived_at.is_(None),can_manage_shared))
    return db.query(CreativeIdea).filter(CreativeIdea.deleted_at.is_(None),or_(CreativeIdea.owner_id==admin.id,shared_scope))

def get_idea(db, admin, idea_id, write=False):
    idea = idea_query(db, admin).filter(CreativeIdea.id == idea_id).first()
    if not idea: raise HTTPException(404, "创意不存在或无权访问")
    if write and not can_manage(admin, idea): raise HTTPException(403, "只能修改自己创建的创意")
    if write and idea.archived_at: raise HTTPException(409, "请先恢复归档创意")
    return idea

def event(db, idea, admin, kind, payload=None):
    db.add(CreativeEvent(idea_id=idea.id, object_type="idea", object_id=idea.id, actor_id=admin.id, event_type=kind, payload_json=json.dumps(payload or {}, ensure_ascii=False)))

def material_event(db, material, admin, kind, payload=None):
    db.add(CreativeEvent(idea_id="", object_type="material", object_id=material.id, actor_id=admin.id, event_type=kind, payload_json=json.dumps(payload or {}, ensure_ascii=False)))

def tags_for(db, idea):
    return [t.name for t in db.query(CreativeTag).join(CreativeIdeaTag, CreativeIdeaTag.tag_id == CreativeTag.id).filter(CreativeIdeaTag.idea_id == idea.id).all()]

def set_tags(db, idea, names, owner_id):
    db.query(CreativeIdeaTag).filter_by(idea_id=idea.id).delete()
    for name in dict.fromkeys(n.strip() for n in names if n.strip()):
        normalized = name.strip()[:48].casefold()[:48]
        tag = db.query(CreativeTag).filter_by(owner_id=owner_id, normalized_name=normalized).first()
        if not tag:
            tag = CreativeTag(owner_id=owner_id, name=name[:48], normalized_name=normalized[:48]); db.add(tag); db.flush()
        db.add(CreativeIdeaTag(idea_id=idea.id, tag_id=tag.id))

def out(idea, db):
    return {"id":idea.id,"title":idea.title,"originalText":idea.original_text,"description":idea.description,"ideaType":idea.idea_type,"status":idea.status,"priority":idea.priority,"starred":idea.starred,"parentId":idea.parent_id,"ownerId":idea.owner_id,"creatorId":idea.creator_id,"visibility":idea.visibility,"nextAction":idea.next_action,"plannedAt":idea.planned_at,"reviewAt":idea.review_at,"conclusion":idea.conclusion,"pauseReason":idea.pause_reason,"version":idea.version,"archivedAt":idea.archived_at,"createdAt":idea.created_at,"updatedAt":idea.updated_at,"tags":tags_for(db, idea)}

def can_manage_material(admin, material):
    perms=parse_json(admin.role.permissions, []) if admin.role else []
    return material.owner_id == admin.id or (material.visibility == "shared" and (admin.role.code == "super_admin" or "creative:manage" in perms or "*" in perms))

def material_out(m, db=None, admin=None):
    attachments=[]
    if db:
        attachments=[{"id":a.id,"name":a.original_name,"size":a.size,"mime":a.mime} for a in db.query(CreativeAttachment).filter_by(material_id=m.id,deleted_at=None).all()]
    return {"canWrite":can_manage_material(admin,m) if admin else False,"attachments":attachments,"id":m.id,"kind":m.kind,"title":m.title,"sourceName":m.source_name,"author":m.author,"url":m.url,"excerpt":m.excerpt,"insight":m.insight,"locator":m.locator,"visibility":m.visibility,"referenceType":m.reference_type,"referenceId":m.reference_id,"ownerId":m.owner_id,"version":m.version,"createdAt":m.created_at}

def practice_out(p):
    return {"id":p.id,"ideaId":p.idea_id,"kind":p.kind,"title":p.title,"occurredAt":p.occurred_at,"action":p.action,"expectation":p.expectation,"result":p.result,"decision":p.decision,"nextAction":p.next_action,"minutes":p.minutes,"cost":p.cost,"metrics":parse_json(p.metrics_json,[]),"resultLinks":parse_json(p.result_links_json,[]),"version":p.version,"createdAt":p.created_at}

@router.get("/creative/overview")
def overview(admin=Depends(require_permission("creative:read")), db: Session=Depends(get_db)):
    q=idea_query(db,admin); own=q.filter(CreativeIdea.owner_id==admin.id)
    now=utcnow(); due=own.filter(CreativeIdea.status.in_(["inbox","to_validate","in_progress"]),CreativeIdea.next_action!="", or_(CreativeIdea.planned_at.is_(None),CreativeIdea.planned_at<=now)).order_by(CreativeIdea.planned_at,CreativeIdea.updated_at.desc()).limit(8).all()
    review=own.filter(CreativeIdea.review_at.is_not(None),CreativeIdea.review_at<=now).order_by(CreativeIdea.review_at).limit(8).all()
    stale=own.filter(CreativeIdea.status=="in_progress",CreativeIdea.updated_at<now-timedelta(days=14)).order_by(CreativeIdea.updated_at).limit(8).all()
    count=lambda status: own.filter(CreativeIdea.status==status).count()
    return ApiResponse.ok({"inboxCount":count("inbox"),"inProgressCount":count("in_progress"),"dueCount":len(due),"reviewCount":len(review),"due": [out(x,db) for x in due],"review":[out(x,db) for x in review],"stale":[out(x,db) for x in stale],"recent":[out(x,db) for x in own.order_by(CreativeIdea.created_at.desc()).limit(8).all()]})

@router.get("/creative/ideas")
def list_ideas(q: str="", status: str|None=None, ideaType: str|None=None, tag: str|None=None, starred: bool|None=None, archived: bool=False, page:int=1, pageSize:int=20, admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    query=idea_query(db,admin).filter(CreativeIdea.archived_at.is_not(None) if archived else CreativeIdea.archived_at.is_(None))
    if status: query=query.filter(CreativeIdea.status==status)
    if ideaType: query=query.filter(CreativeIdea.idea_type==ideaType)
    if tag:
        query=query.join(CreativeIdeaTag,CreativeIdeaTag.idea_id==CreativeIdea.id).join(CreativeTag,CreativeTag.id==CreativeIdeaTag.tag_id).filter(CreativeTag.name==tag).distinct()
    if starred is not None: query=query.filter(CreativeIdea.starred==starred)
    if q.strip():
        term=f"%{q.strip()[:100]}%"; query=query.filter(or_(CreativeIdea.title.ilike(term),CreativeIdea.original_text.ilike(term),CreativeIdea.description.ilike(term)))
    total=query.count(); rows=query.order_by(CreativeIdea.updated_at.desc(),CreativeIdea.id).offset((max(page,1)-1)*min(max(pageSize,1),100)).limit(min(max(pageSize,1),100)).all()
    return ApiResponse.ok({"items":[out(x,db) for x in rows],"total":total,"page":page,"pageSize":min(max(pageSize,1),100)})

@router.post("/creative/ideas")
def create_idea(body:IdeaCreate,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    if not body.title.strip() and not body.originalText.strip() and not body.description.strip(): raise HTTPException(400,"请至少填写名称、原始灵感或描述")
    if body.status=="in_progress" and not body.nextAction.strip(): raise HTTPException(400,"实践中必须填写下一步")
    if body.status=="settled" and not body.conclusion.strip(): raise HTTPException(400,"已沉淀必须填写结论")
    if body.status=="paused" and not body.pauseReason.strip(): raise HTTPException(400,"搁置时请填写原因")
    if body.parentId:
        parent=get_idea(db,admin,body.parentId,True)
        if parent.visibility != body.visibility: raise HTTPException(400,"父创意与子创意可见范围需一致")
    title=body.title.strip() or (body.originalText.strip().splitlines()[0][:120] if body.originalText.strip() else "未命名创意")
    idea=CreativeIdea(title=title,original_text=body.originalText,description=body.description,idea_type=body.ideaType,status=body.status,priority=body.priority,starred=body.starred,parent_id=body.parentId,owner_id=admin.id,creator_id=admin.id,visibility=body.visibility,next_action=body.nextAction,planned_at=body.plannedAt,review_at=body.reviewAt,conclusion=body.conclusion,pause_reason=body.pauseReason)
    db.add(idea); db.flush(); set_tags(db,idea,body.tagNames,admin.id); event(db,idea,admin,"created"); db.commit(); db.refresh(idea)
    return ApiResponse.ok(out(idea,db))

@router.post("/creative/captures")
def capture(body:CaptureBody,idempotency_header:str|None=Header(default=None,alias="Idempotency-Key"),admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    text=body.text.strip(); url=body.url.strip()
    idempotency_key=idempotency_header or body.idempotencyKey
    if idempotency_header and body.idempotencyKey and idempotency_header!=body.idempotencyKey: raise HTTPException(400,"请求头与请求体的幂等键不一致")
    if len(idempotency_key)<8 or len(idempotency_key)>100: raise HTTPException(400,"幂等键长度需为 8 至 100 个字符")
    if not url and text:
        match=re.search(r"https?://[^\s，。)）]+", text)
        url=match.group(0).rstrip(".,;!?，。") if match else ""
    if not text and not url: raise HTTPException(400,"请输入想法或参考链接")
    parsed=urlparse(url) if url else None
    if url and (parsed.scheme not in {"http","https"} or not parsed.netloc): raise HTTPException(400,"只支持 HTTP 或 HTTPS 链接")
    payload_hash=hashlib.sha256(json.dumps([text,url,body.title],ensure_ascii=False).encode()).hexdigest()
    old=db.query(CreativeCaptureRequest).filter_by(admin_id=admin.id,idempotency_key=idempotency_key).first()
    if old:
        if old.payload_hash != payload_hash: raise HTTPException(409,"记录请求键已用于其他内容")
        return ApiResponse.ok(out(get_idea(db,admin,old.idea_id),db))
    idea=CreativeIdea(title=body.title.strip() or (text.splitlines()[0][:120] if text else url[:120]),original_text=text,owner_id=admin.id,creator_id=admin.id)
    db.add(idea);db.flush()
    if url:
        material=CreativeMaterial(owner_id=admin.id,kind="link",title=body.title.strip() or url,url=url,visibility="private");db.add(material);db.flush();db.add(CreativeIdeaMaterial(idea_id=idea.id,material_id=material.id))
    db.add(CreativeCaptureRequest(admin_id=admin.id,idempotency_key=idempotency_key,payload_hash=payload_hash,idea_id=idea.id))
    event(db,idea,admin,"captured",{"hasUrl":bool(url)})
    try: db.commit()
    except IntegrityError:
        db.rollback();old=db.query(CreativeCaptureRequest).filter_by(admin_id=admin.id,idempotency_key=idempotency_key).first()
        if old and old.payload_hash==payload_hash: return ApiResponse.ok(out(get_idea(db,admin,old.idea_id),db))
        raise HTTPException(409,"记录请求键已用于其他内容")
    db.refresh(idea)
    return ApiResponse.ok(out(idea,db))

@router.get("/creative/ideas/{idea_id}")
def detail(idea_id:str,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id)
    links=db.query(CreativeIdeaMaterial,CreativeMaterial).join(CreativeMaterial,CreativeMaterial.id==CreativeIdeaMaterial.material_id).filter(CreativeIdeaMaterial.idea_id==idea.id,CreativeMaterial.deleted_at.is_(None),or_(CreativeMaterial.owner_id==admin.id,CreativeMaterial.visibility=="shared")).all()
    children=idea_query(db,admin).filter(CreativeIdea.parent_id==idea.id).order_by(CreativeIdea.created_at).all()
    relations=db.query(CreativeIdeaRelation).filter(or_(CreativeIdeaRelation.left_id==idea.id,CreativeIdeaRelation.right_id==idea.id)).all()
    related=[]
    for rel in relations:
        target_id=rel.right_id if rel.left_id==idea.id else rel.left_id
        target=idea_query(db,admin).filter(CreativeIdea.id==target_id).first()
        if target: related.append(out(target,db))
    practices=db.query(CreativePractice).filter_by(idea_id=idea.id,deleted_at=None).order_by(CreativePractice.occurred_at.desc()).limit(100).all()
    events=db.query(CreativeEvent).filter_by(idea_id=idea.id).order_by(CreativeEvent.created_at.desc()).limit(100).all()
    timeline=[{"id":p.id,"type":"practice","createdAt":p.occurred_at,"practice":practice_out(p)} for p in practices]
    timeline += [{"id":e.id,"type":"event","eventType":e.event_type,"payload":parse_json(e.payload_json,{}),"createdAt":e.created_at} for e in events]
    timeline.sort(key=lambda item:(item["createdAt"],item["id"]),reverse=True)
    return ApiResponse.ok({"canWrite":can_manage(admin,idea),"idea":out(idea,db),"materials":[{**material_out(m,db,admin),"linkInsight":link.insight} for link,m in links],"children":[out(x,db) for x in children],"related":related,"practices":[practice_out(x) for x in practices],"events":[{"id":e.id,"type":e.event_type,"payload":parse_json(e.payload_json,{}),"createdAt":e.created_at} for e in events],"timeline":timeline})


@router.get("/creative/ideas/{idea_id}/timeline")
def idea_timeline(idea_id:str,page:int=1,pageSize:int=20,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id)
    practices=db.query(CreativePractice).filter_by(idea_id=idea.id,deleted_at=None).all()
    events=db.query(CreativeEvent).filter_by(idea_id=idea.id,object_type="idea").all()
    items=[{"id":p.id,"type":"practice","createdAt":p.occurred_at,"practice":practice_out(p)} for p in practices]
    items += [{"id":e.id,"type":"event","eventType":e.event_type,"payload":parse_json(e.payload_json,{}),"createdAt":e.created_at} for e in events]
    items.sort(key=lambda item:(item["createdAt"],item["id"]),reverse=True)
    size=min(max(pageSize,1),100);start=(max(page,1)-1)*size
    return ApiResponse.ok({"items":items[start:start+size],"total":len(items),"page":max(page,1),"pageSize":size})

@router.patch("/creative/ideas/{idea_id}")
def patch_idea(idea_id:str,body:IdeaPatch,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True)
    if idea.version!=body.version: raise HTTPException(409,"创意已被其他页面修改，请刷新后重试")
    data=body.model_dump(exclude_unset=True); data.pop("version",None); tags=data.pop("tagNames",None); parent_id=data.get("parentId",idea.parent_id)
    if parent_id:
        if parent_id==idea.id: raise HTTPException(400,"不能将创意设为自身父级")
        parent=get_idea(db,admin,parent_id,True)
        cursor=parent
        while cursor.parent_id:
            if cursor.parent_id==idea.id: raise HTTPException(400,"父级关系不能形成循环")
            cursor=get_idea(db,admin,cursor.parent_id,True)
    target_visibility=data.get("visibility",idea.visibility)
    if parent_id:
        p=get_idea(db,admin,parent_id)
        if p.visibility != target_visibility: raise HTTPException(400,"父创意与子创意可见范围需一致")
    if target_visibility=="private" and db.query(CreativeIdea).filter(CreativeIdea.parent_id==idea.id,CreativeIdea.visibility=="shared",CreativeIdea.deleted_at.is_(None)).count():
        raise HTTPException(409,"请先取消共享子创意，再设为仅自己可见")
    for k,v in data.items(): setattr(idea, {"ideaType":"idea_type","parentId":"parent_id","nextAction":"next_action","plannedAt":"planned_at","reviewAt":"review_at","pauseReason":"pause_reason"}.get(k,k),v)
    if idea.status=="in_progress" and not idea.next_action.strip(): raise HTTPException(400,"实践中必须填写下一步")
    if idea.status=="settled" and not idea.conclusion.strip(): raise HTTPException(400,"已沉淀必须填写结论")
    idea.version+=1
    if tags is not None: set_tags(db,idea,tags,idea.owner_id)
    event(db,idea,admin,"updated",{"fields":list(data.keys())});db.commit();db.refresh(idea)
    return ApiResponse.ok(out(idea,db))

@router.post("/creative/ideas/{idea_id}/transition")
def transition(idea_id:str,body:TransitionBody,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True)
    if body.version!=idea.version: raise HTTPException(409,"创意已被其他页面修改，请刷新后重试")
    if body.status not in STATUSES: raise HTTPException(400,"创意状态无效")
    if body.status=="in_progress" and not idea.next_action.strip(): raise HTTPException(400,"实践中必须先填写下一步")
    if body.status=="settled" and not idea.conclusion.strip(): raise HTTPException(400,"已沉淀必须先填写结论")
    if body.status=="paused" and not body.reason.strip(): raise HTTPException(400,"搁置时请填写原因")
    before=idea.status;idea.status=body.status;idea.version+=1
    if body.status=="paused": idea.pause_reason=body.reason.strip()
    event(db,idea,admin,"status_changed",{"from":before,"to":body.status,"reason":body.reason});db.commit();db.refresh(idea)
    return ApiResponse.ok(out(idea,db))

@router.post("/creative/ideas/{idea_id}/archive")
def archive(idea_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True);idea.archived_at=utcnow();event(db,idea,admin,"archived");db.commit();return ApiResponse.ok(out(idea,db))

@router.post("/creative/ideas/{idea_id}/unarchive")
def unarchive(idea_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=db.query(CreativeIdea).filter(CreativeIdea.id==idea_id,CreativeIdea.deleted_at.is_(None)).first()
    if not idea or not can_manage(admin,idea): raise HTTPException(404,"创意不存在")
    idea.archived_at=None;event(db,idea,admin,"restored_from_archive");db.commit();return ApiResponse.ok(out(idea,db))

@router.delete("/creative/ideas/{idea_id}")
def delete_idea(idea_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=db.query(CreativeIdea).filter(CreativeIdea.id==idea_id,CreativeIdea.deleted_at.is_(None)).first()
    if not idea or not can_manage(admin,idea): raise HTTPException(404,"创意不存在或无权访问")
    if db.query(CreativeIdea).filter(CreativeIdea.parent_id==idea.id,CreativeIdea.deleted_at.is_(None)).count(): raise HTTPException(409,"请先移动或删除子创意")
    idea.deleted_at=utcnow();event(db,idea,admin,"deleted");db.commit();return ApiResponse.ok({"id":idea.id})

@router.post("/creative/ideas/{idea_id}/restore")
def restore_idea(idea_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=db.query(CreativeIdea).filter_by(id=idea_id).first()
    if not idea or not can_manage(admin,idea): raise HTTPException(404,"创意不存在")
    if idea.parent_id:
        parent=db.query(CreativeIdea).filter_by(id=idea.parent_id,deleted_at=None).first()
        if not parent or parent.visibility!=idea.visibility: raise HTTPException(409,"请先恢复可见范围一致的父创意")
    idea.deleted_at=None;event(db,idea,admin,"restored");db.commit();return ApiResponse.ok(out(idea,db))

@router.post("/creative/ideas/{idea_id}/practices")
def add_practice(idea_id:str,body:PracticeIn,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True)
    if body.version is not None and body.version!=idea.version: raise HTTPException(409,"创意已被其他页面修改，请刷新后重试")
    for metric in body.metrics:
        if not metric.get("name") or len(str(metric.get("name")))>80: raise HTTPException(400,"指标名称必填且不能超过 80 字")
        if isinstance(metric.get("value"),(int,float)) and abs(metric["value"])>1e12: raise HTTPException(400,"指标数值超出范围")
    p=CreativePractice(idea_id=idea.id,creator_id=admin.id,kind=body.kind,title=body.title,occurred_at=body.occurredAt or utcnow(),action=body.action,expectation=body.expectation,result=body.result,decision=body.decision,next_action=body.nextAction,minutes=body.minutes,cost=body.cost,metrics_json=json.dumps(body.metrics,ensure_ascii=False),result_links_json=json.dumps(body.resultLinks,ensure_ascii=False))
    db.add(p)
    if body.updateNextAction:
        if not body.nextAction.strip(): raise HTTPException(400,"同步下一步时不能为空")
        idea.next_action=body.nextAction.strip();idea.version+=1
    event(db,idea,admin,"practice_added",{"practiceId":p.id,"title":p.title});db.commit();db.refresh(p)
    return ApiResponse.ok(practice_out(p))

@router.get("/creative/ideas/{idea_id}/practices")
def list_practices(idea_id:str,page:int=1,pageSize:int=20,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id);q=db.query(CreativePractice).filter_by(idea_id=idea.id,deleted_at=None);total=q.count();rows=q.order_by(CreativePractice.occurred_at.desc()).offset((max(page,1)-1)*min(max(pageSize,1),100)).limit(min(max(pageSize,1),100)).all()
    return ApiResponse.ok({"items":[practice_out(x) for x in rows],"total":total})

@router.get("/creative/materials")
def list_materials(q:str="",page:int=1,pageSize:int=20,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    query=db.query(CreativeMaterial).filter(CreativeMaterial.deleted_at.is_(None),or_(CreativeMaterial.owner_id==admin.id,CreativeMaterial.visibility=="shared"))
    if q.strip():
        term=f"%{q.strip()[:100]}%";query=query.filter(or_(CreativeMaterial.title.ilike(term),CreativeMaterial.excerpt.ilike(term),CreativeMaterial.insight.ilike(term),CreativeMaterial.source_name.ilike(term)))
    total=query.count();rows=query.order_by(CreativeMaterial.created_at.desc()).offset((max(page,1)-1)*min(max(pageSize,1),100)).limit(min(max(pageSize,1),100)).all()
    return ApiResponse.ok({"items":[material_out(x,db,admin) for x in rows],"total":total})

@router.post("/creative/materials")
def create_material(body:MaterialIn,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    if body.url:
        u=urlparse(body.url)
        if u.scheme not in {"http","https"} or not u.netloc: raise HTTPException(400,"只支持 HTTP 或 HTTPS 链接")
    if body.visibility not in {"private","shared"}: raise HTTPException(400,"可见范围无效")
    m=CreativeMaterial(owner_id=admin.id,kind=body.kind,title=body.title,source_name=body.sourceName,author=body.author,url=body.url,excerpt=body.excerpt,insight=body.insight,locator=body.locator,visibility=body.visibility,reference_type=body.referenceType,reference_id=body.referenceId)
    db.add(m);db.flush();material_event(db,m,admin,"material_created");db.commit();db.refresh(m);return ApiResponse.ok(material_out(m,db,admin))



@router.get("/creative/materials/{material_id}")
def get_material(material_id:str,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    material=db.query(CreativeMaterial).filter(CreativeMaterial.id==material_id,CreativeMaterial.deleted_at.is_(None),or_(CreativeMaterial.owner_id==admin.id,CreativeMaterial.visibility=="shared")).first()
    if not material: raise HTTPException(404,"物料不存在或无权访问")
    events=db.query(CreativeEvent).filter_by(object_type="material",object_id=material.id).order_by(CreativeEvent.created_at.desc()).limit(100).all()
    return ApiResponse.ok({**material_out(material,db,admin),"events":[{"id":e.id,"type":e.event_type,"payload":parse_json(e.payload_json,{}),"createdAt":e.created_at} for e in events]})

@router.patch("/creative/materials/{material_id}")
def patch_material(material_id:str,body:MaterialPatch,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    material=db.query(CreativeMaterial).filter_by(id=material_id,deleted_at=None).first()
    if not material or not can_manage_material(admin,material): raise HTTPException(404,"物料不存在")
    if material.version!=body.version: raise HTTPException(409,"物料已被修改，请刷新后重试")
    data=body.model_dump(exclude_unset=True);data.pop("version",None)
    if data.get("visibility") not in {None,"private","shared"}: raise HTTPException(400,"可见范围无效")
    if data.get("url"):
        u=urlparse(data["url"])
        if u.scheme not in {"http","https"} or not u.netloc: raise HTTPException(400,"只支持 HTTP 或 HTTPS 链接")
    if data.get("visibility")=="private" and db.query(CreativeIdeaMaterial).join(CreativeIdea,CreativeIdea.id==CreativeIdeaMaterial.idea_id).filter(CreativeIdeaMaterial.material_id==material.id,CreativeIdea.visibility=="shared",CreativeIdea.deleted_at.is_(None)).count(): raise HTTPException(409,"请先解除共享创意对该物料的引用")
    for key,value in data.items(): setattr(material,{"sourceName":"source_name","referenceType":"reference_type","referenceId":"reference_id"}.get(key,key),value)
    material.version+=1;material_event(db,material,admin,"material_updated",{"fields":list(data.keys())});db.commit();db.refresh(material);return ApiResponse.ok(material_out(material,db,admin))

@router.post("/creative/ideas/{idea_id}/materials/{material_id}")
def link_material(idea_id:str,material_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True);m=db.query(CreativeMaterial).filter(CreativeMaterial.id==material_id,CreativeMaterial.deleted_at.is_(None),or_(CreativeMaterial.owner_id==admin.id,and_(CreativeMaterial.visibility=="shared",idea.visibility=="shared"))).first()
    if not m: raise HTTPException(404,"物料不存在或未共享")
    if not db.query(CreativeIdeaMaterial).filter_by(idea_id=idea.id,material_id=m.id).first(): db.add(CreativeIdeaMaterial(idea_id=idea.id,material_id=m.id));event(db,idea,admin,"material_linked",{"materialId":m.id});db.commit()
    return ApiResponse.ok({"ideaId":idea.id,"materialId":m.id})

@router.delete("/creative/ideas/{idea_id}/materials/{material_id}")
def unlink_material(idea_id:str,material_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True);db.query(CreativeIdeaMaterial).filter_by(idea_id=idea.id,material_id=material_id).delete();event(db,idea,admin,"material_unlinked",{"materialId":material_id});db.commit();return ApiResponse.ok({"ok":True})

@router.post("/creative/ideas/{idea_id}/relations/{target_id}")
def relate(idea_id:str,target_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True);target=get_idea(db,admin,target_id,True)
    if idea.id==target.id: raise HTTPException(400,"不能关联自身")
    left,right=sorted([idea.id,target.id]);
    if not db.query(CreativeIdeaRelation).filter_by(left_id=left,right_id=right).first(): db.add(CreativeIdeaRelation(left_id=left,right_id=right));event(db,idea,admin,"related",{"targetId":target.id});db.commit()
    return ApiResponse.ok({"leftId":left,"rightId":right})

@router.get("/creative/tags")
def list_tags(admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    visible_tag_ids=db.query(CreativeIdeaTag.tag_id).join(CreativeIdea,CreativeIdea.id==CreativeIdeaTag.idea_id).filter(CreativeIdea.deleted_at.is_(None),or_(CreativeIdea.owner_id==admin.id,and_(CreativeIdea.visibility=="shared",CreativeIdea.archived_at.is_(None)))).subquery()
    rows=db.query(CreativeTag).filter(or_(CreativeTag.owner_id==admin.id,CreativeTag.id.in_(visible_tag_ids))).distinct().order_by(CreativeTag.name).all()
    return ApiResponse.ok([{"id":x.id,"name":x.name} for x in rows])

@router.get("/creative/recycle-bin")
def recycle_bin(admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    perms=parse_json(admin.role.permissions, []) if admin.role else []
    can_manage_shared=bool(admin.role and admin.role.code=="super_admin") or "creative:manage" in perms or "*" in perms
    ideas=db.query(CreativeIdea).filter(CreativeIdea.deleted_at.is_not(None),or_(CreativeIdea.owner_id==admin.id,and_(CreativeIdea.visibility=="shared",can_manage_shared))).order_by(CreativeIdea.updated_at.desc()).limit(200).all()
    mats=db.query(CreativeMaterial).filter(CreativeMaterial.deleted_at.is_not(None),or_(CreativeMaterial.owner_id==admin.id,and_(CreativeMaterial.visibility=="shared",can_manage_shared))).order_by(CreativeMaterial.updated_at.desc()).limit(200).all()
    return ApiResponse.ok({"ideas":[out(x,db) for x in ideas],"materials":[material_out(x,db,admin) for x in mats]})


@router.delete("/creative/materials/{material_id}")
def delete_material(material_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    material=db.query(CreativeMaterial).filter_by(id=material_id,deleted_at=None).first()
    if not material or not can_manage_material(admin,material): raise HTTPException(404,"物料不存在")
    material.deleted_at=utcnow();material_event(db,material,admin,"material_deleted");db.commit();return ApiResponse.ok({"id":material.id})

@router.post("/creative/materials/{material_id}/restore")
def restore_material(material_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    material=db.query(CreativeMaterial).filter_by(id=material_id).first()
    if not material or not can_manage_material(admin,material): raise HTTPException(404,"物料不存在")
    material.deleted_at=None;material_event(db,material,admin,"material_restored");db.commit();return ApiResponse.ok(material_out(material,db,admin))

@router.post("/creative/materials/{material_id}/attachments")
async def upload_attachment(material_id:str,file:UploadFile=File(...),admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    material=db.query(CreativeMaterial).filter_by(id=material_id,deleted_at=None).first()
    if not material or not can_manage_material(admin,material): raise HTTPException(404,"物料不存在")
    if db.query(CreativeAttachment).filter_by(material_id=material_id,deleted_at=None).count()>=10: raise HTTPException(400,"每个物料最多添加 10 个附件")
    name=Path(file.filename or "attachment").name[:240]
    allowed={".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp",".pdf":"application/pdf",".txt":"text/plain",".md":"text/markdown",".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ext=Path(name).suffix.lower()
    if ext not in allowed: raise HTTPException(400,"附件仅支持 JPG、PNG、WebP、PDF、TXT、MD 和 DOCX")
    raw=await file.read(20*1024*1024+1)
    if not raw or len(raw)>20*1024*1024: raise HTTPException(413,"附件不能为空且不能超过 20MB")
    actual=(file.content_type or "").split(";")[0].lower()
    if actual not in {allowed[ext],"application/octet-stream"}: raise HTTPException(400,"文件类型与扩展名不匹配")
    if ext==".pdf" and not raw.startswith(b"%PDF-"): raise HTTPException(400,"PDF 文件格式无效")
    if ext==".png" and not raw.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(400,"PNG 文件格式无效")
    if ext in {".jpg",".jpeg"} and not raw.startswith(b"\xff\xd8\xff"): raise HTTPException(400,"JPEG 文件格式无效")
    key=secrets.token_hex(24);folder=DATA_DIR/"creative-private";folder.mkdir(parents=True,exist_ok=True);(folder/key).write_bytes(raw)
    attachment=CreativeAttachment(material_id=material.id,owner_id=admin.id,storage_key=key,original_name=name,mime=allowed[ext],size=len(raw),checksum=hashlib.sha256(raw).hexdigest())
    db.add(attachment);material_event(db,material,admin,"attachment_added",{"attachmentId":attachment.id,"name":attachment.original_name});db.commit();db.refresh(attachment)
    return ApiResponse.ok({"id":attachment.id,"name":attachment.original_name,"size":attachment.size,"mime":attachment.mime})

@router.get("/creative/attachments/{attachment_id}/download")
def download_attachment(attachment_id:str,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    row=db.query(CreativeAttachment).filter_by(id=attachment_id,deleted_at=None).first()
    if not row: raise HTTPException(404,"附件不存在")
    material=db.query(CreativeMaterial).filter_by(id=row.material_id,deleted_at=None).first()
    if not material or (material.owner_id!=admin.id and material.visibility!="shared"): raise HTTPException(404,"附件不存在或无权访问")
    path=DATA_DIR/"creative-private"/row.storage_key
    if not path.is_file() or path.parent.resolve()!=(DATA_DIR/"creative-private").resolve(): raise HTTPException(404,"附件文件不存在")
    return FileResponse(path,media_type=row.mime,filename=row.original_name,headers={"X-Content-Type-Options":"nosniff","Cache-Control":"private, no-store"})

@router.get("/creative/ideas/{idea_id}/export")
def export_idea(idea_id:str,admin=Depends(require_permission("creative:read")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id)
    lines=[f"# {idea.title}","",f"- 类型：{idea.idea_type}",f"- 状态：{idea.status}",f"- 创建：{idea.created_at}","", "## 原始灵感",idea.original_text,"", "## 描述",idea.description,"", "## 下一步",idea.next_action,"", "## 沉淀结论",idea.conclusion,"", "## 实践记录"]
    material_rows=db.query(CreativeMaterial).join(CreativeIdeaMaterial,CreativeIdeaMaterial.material_id==CreativeMaterial.id).filter(CreativeIdeaMaterial.idea_id==idea.id,CreativeMaterial.deleted_at.is_(None),or_(CreativeMaterial.owner_id==admin.id,CreativeMaterial.visibility=="shared")).all()
    lines += ["", "## 参考物料"]
    for material in material_rows: lines += [f"- [{material.title or material.source_name}]({material.url})" if material.url else f"- {material.title or material.source_name}: {material.excerpt}"]
    practices=db.query(CreativePractice).filter_by(idea_id=idea.id,deleted_at=None).order_by(CreativePractice.occurred_at).all()
    for p in practices: lines += [f"### {p.title or p.kind} · {p.occurred_at}",p.action,p.result,("下一步："+p.next_action if p.next_action else ""),""]
    return ApiResponse.ok({"filename":f"creative-{idea.id}.md","content":"\n".join(lines)})


@router.patch("/creative/practices/{practice_id}")
def update_practice(practice_id:str,body:PracticeIn,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    p=db.query(CreativePractice).filter_by(id=practice_id,deleted_at=None).first()
    if not p: raise HTTPException(404,"实践记录不存在")
    idea=get_idea(db,admin,p.idea_id,True)
    if p.creator_id!=admin.id and not can_manage(admin,idea): raise HTTPException(403,"无权修改该实践记录")
    if body.version is not None and body.version!=p.version: raise HTTPException(409,"实践记录已被其他页面修改")
    if body.updateNextAction and not body.nextAction.strip(): raise HTTPException(400,"同步下一步时不能为空")
    p.kind=body.kind;p.title=body.title;p.occurred_at=body.occurredAt or p.occurred_at;p.action=body.action;p.expectation=body.expectation;p.result=body.result;p.decision=body.decision;p.next_action=body.nextAction;p.minutes=body.minutes;p.cost=body.cost;p.metrics_json=json.dumps(body.metrics,ensure_ascii=False);p.result_links_json=json.dumps(body.resultLinks,ensure_ascii=False);p.version+=1
    if body.updateNextAction: idea.next_action=body.nextAction.strip();idea.version+=1
    event(db,idea,admin,"practice_updated",{"practiceId":p.id});db.commit();db.refresh(p);return ApiResponse.ok(practice_out(p))

@router.delete("/creative/practices/{practice_id}")
def delete_practice(practice_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    p=db.query(CreativePractice).filter_by(id=practice_id,deleted_at=None).first()
    if not p: raise HTTPException(404,"实践记录不存在")
    idea=get_idea(db,admin,p.idea_id,True)
    if p.creator_id!=admin.id and not can_manage(admin,idea): raise HTTPException(403,"无权删除该实践记录")
    p.deleted_at=utcnow();event(db,idea,admin,"practice_deleted",{"practiceId":p.id});db.commit();return ApiResponse.ok({"id":p.id})

@router.delete("/creative/ideas/{idea_id}/relations/{target_id}")
def unrelate(idea_id:str,target_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    idea=get_idea(db,admin,idea_id,True);target=get_idea(db,admin,target_id,True);left,right=sorted([idea.id,target.id])
    db.query(CreativeIdeaRelation).filter_by(left_id=left,right_id=right).delete();event(db,idea,admin,"relation_removed",{"targetId":target.id});db.commit();return ApiResponse.ok({"ok":True})


@router.delete("/creative/attachments/{attachment_id}")
def delete_attachment(attachment_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    attachment=db.query(CreativeAttachment).filter_by(id=attachment_id,deleted_at=None).first()
    material=db.get(CreativeMaterial,attachment.material_id) if attachment else None
    if not attachment or not material or not can_manage_material(admin,material): raise HTTPException(404,"附件不存在")
    attachment.deleted_at=utcnow();material_event(db,material,admin,"attachment_removed",{"attachmentId":attachment.id});db.commit();return ApiResponse.ok({"id":attachment.id})


@router.post("/creative/tags")
def create_tag(body:TagIn,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    name=body.name.strip()
    tag=db.query(CreativeTag).filter_by(owner_id=admin.id,normalized_name=name.strip()[:48].casefold()[:48]).first()
    if tag: return ApiResponse.ok({"id":tag.id,"name":tag.name})
    tag=CreativeTag(owner_id=admin.id,name=name,normalized_name=name.strip()[:48].casefold()[:48]);db.add(tag);db.commit();db.refresh(tag);return ApiResponse.ok({"id":tag.id,"name":tag.name})

@router.patch("/creative/tags/{tag_id}")
def rename_tag(tag_id:str,body:TagIn,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    tag=db.query(CreativeTag).filter_by(id=tag_id,owner_id=admin.id).first()
    if not tag: raise HTTPException(404,"标签不存在")
    name=body.name.strip();duplicate=db.query(CreativeTag).filter(CreativeTag.owner_id==admin.id,CreativeTag.normalized_name==name.strip()[:48].casefold()[:48],CreativeTag.id!=tag.id).first()
    if duplicate: raise HTTPException(409,"该标签已存在")
    tag.name=name;tag.normalized_name=name.strip()[:48].casefold()[:48];db.commit();return ApiResponse.ok({"id":tag.id,"name":tag.name})

@router.delete("/creative/tags/{tag_id}")
def delete_tag(tag_id:str,admin=Depends(require_permission("creative:write")),db:Session=Depends(get_db)):
    tag=db.query(CreativeTag).filter_by(id=tag_id,owner_id=admin.id).first()
    if not tag: raise HTTPException(404,"标签不存在")
    db.query(CreativeIdeaTag).filter_by(tag_id=tag.id).delete();db.delete(tag);db.commit();return ApiResponse.ok({"id":tag_id})
