import json

from sqlalchemy.orm import Session

from app.models import PhotographyLesson, PhotographyStage, gen_id


def stage_dict(row: PhotographyStage) -> dict:
    return {"id": row.id, "title": row.title, "items": row.items, "description": row.description,
            "sortOrder": row.sort_order, "isPublished": row.is_published}


def lesson_dict(row: PhotographyLesson) -> dict:
    try:
        steps = json.loads(row.steps_json or "[]")
        if not isinstance(steps, list):
            steps = []
    except (TypeError, json.JSONDecodeError):
        steps = []
    return {"id": row.id, "stageId": row.stage_id, "category": row.category, "title": row.title,
            "subtitle": row.subtitle, "level": row.level, "durationMin": row.duration_min,
            "time": f"{row.duration_min} 分钟", "principle": row.principle, "steps": steps,
            "task": row.task, "review": row.review, "sortOrder": row.sort_order,
            "isPublished": row.is_published}


def photography_catalog(db: Session) -> dict:
    stages = db.query(PhotographyStage).filter(PhotographyStage.is_published.is_(True)).order_by(
        PhotographyStage.sort_order, PhotographyStage.title
    ).all()
    lessons = db.query(PhotographyLesson).filter(PhotographyLesson.is_published.is_(True)).order_by(
        PhotographyLesson.sort_order, PhotographyLesson.title
    ).all()
    visible_stage_ids = {row.id for row in stages}
    return {"stages": [stage_dict(row) for row in stages],
            "lessons": [lesson_dict(row) for row in lessons if row.stage_id in visible_stage_ids]}


def seed_photography_content(db: Session) -> None:
    if db.query(PhotographyStage).first() or db.query(PhotographyLesson).first():
        return
    stage_data = [
        ("看见光", "光线方向 · 光质 · 色温 · 明暗关系", "练习判断光源方向、软硬和色彩，用光塑造质感。"),
        ("安排画面", "主体与背景 · 留白 · 线条 · 层次 · 色彩", "控制画面边缘、主体位置与空间关系，让视线有落点。"),
        ("控制相机", "曝光三要素 · 测光与曝光补偿 · 对焦 · 景深", "理解曝光、测光和对焦，建立可控的拍摄习惯。"),
        ("表达主题", "人物 · 静物 · 街景 · 风光 · 叙事与情绪", "围绕常见题材，练习把感受转成画面选择。"),
        ("形成作品", "选片 · 基础后期 · 系列表达 · 复盘与再拍", "通过选片、调整和系列组织，完成自己的表达。"),
    ]
    stages = []
    for index, (title, items, description) in enumerate(stage_data):
        row = PhotographyStage(id=gen_id("phs"), title=title, items=items, description=description,
                               sort_order=index + 1, is_published=True)
        db.add(row)
        stages.append(row)
    db.flush()
    lesson_data = [
        (0, "光线", "先观察光，再按下快门", "用窗边的一束光，拍出有方向的立体感", 12,
         "光线决定画面的明暗、质感和情绪。先找光从哪里来、光有多硬，再决定人物或物体站在哪里。",
         ["把拍摄对象放在离窗约 1 米处，先观察脸上的亮部与阴影。", "让对象慢慢转向窗户，每转一点拍一张，比较光影变化。", "锁定曝光后，试拍正面光、侧光、逆光各一张。"],
         "拍同一个对象的侧光与逆光照片各一张，选择更符合你想表达情绪的一张。", "亮部有没有保留细节？阴影是在塑造形体，还是遮住了重要信息？"),
        (1, "构图", "用边缘和留白安排主体", "从“拍全”转向“决定什么不拍”", 10,
         "构图是对画面元素的取舍与关系安排。留白能给主体呼吸空间，也能引导视线。",
         ["找到一个简单主体，先拍一张把它放在正中央。", "尝试把主体移到画面三分之一处，给视线方向留空间。", "检查四条边缘，移除切入画面的杂物，再拍一张。"],
         "同一场景拍“居中”和“偏置留白”两版，记录你希望观众先看见什么。", "主体是否一眼可辨？边缘是否有多余内容？留白有没有帮助表达？"),
        (2, "曝光", "曝光补偿：让相机理解你的意图", "高调、低调和雪景不必总是灰", 15,
         "相机会把测光区域趋向中间亮度。遇到大面积白色或黑色时，自动曝光可能把它们拍灰，需要用曝光补偿修正。",
         ["找一处白墙或浅色物体，先用自动曝光拍摄。", "分别尝试 +1EV 与 -1EV，观察白色是否更接近现场。", "查看直方图或高光警告，避免重要亮部完全溢出。"],
         "拍一张浅色场景，分别用 -1、0、+1EV 记录效果，写下最贴近现场的一张。", "照片想表达明亮还是压暗？高光、阴影分别保留了多少细节？"),
        (2, "对焦", "先确定焦点，再决定景深", "让背景虚化服务于主体", 12,
         "景深受光圈、焦距、拍摄距离和背景距离共同影响。只追求大光圈，可能会让主体关键部位也失焦。",
         ["选择一个静止主体，单点对焦到最重要的细节。", "保持构图不变，用不同光圈各拍一张。", "再拉开主体与背景距离，观察虚化如何改变。"],
         "拍一组主体清晰、背景简洁的照片，至少比较两种光圈或主体背景距离。", "焦点落在表达重点上了吗？背景虚化是否让主体更清楚？"),
    ]
    for index, (stage_index, category, title, subtitle, duration, principle, steps, task, review) in enumerate(lesson_data):
        db.add(PhotographyLesson(id=gen_id("phl"), stage_id=stages[stage_index].id,
            category=category, title=title, subtitle=subtitle, level="入门", duration_min=duration,
            principle=principle, steps_json=json.dumps(steps, ensure_ascii=False), task=task,
            review=review, sort_order=index + 1, is_published=True))
    db.commit()
