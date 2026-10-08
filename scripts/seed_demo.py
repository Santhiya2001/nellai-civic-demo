"""Idempotent demo fixtures. All organizations, reports and evidence are illustrative."""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from PIL import Image, ImageDraw
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal, now, uid
from app.models import Authority, Boundary, Calendar, Complaint, Upload, User
from app.models import Responsibility
from app.modules import import_models, synchronize
from app.security import hasher
from app.services import auto_assign, record

if not settings().demo_mode or settings().environment == "production":
    raise SystemExit("Demo seed is permitted only with DEMO_MODE=true outside production.")
import_models()
from modules.green.backend.models import PlantingSite, Tree
from modules.volunteer.backend.models import Activity, Volunteer
from modules.water.backend.models import WaterBody


def sample_image(db, owner, label):
    image_id = uid()
    folder = Path(settings().upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1000, 560), "#e5ebda")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((55, 50, 945, 510), radius=24, fill="#f8faf2", outline="#b8c6a2", width=3)
    d.rectangle((55, 50, 945, 160), fill="#254d36")
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    except OSError:
        font = small = None
    d.text((95, 85), "NELLAI GREEN & CIVIC", fill="white", font=font)
    d.text((95, 220), label[:44], fill="#254d36", font=font)
    d.text((95, 290), "DEMONSTRATION EVIDENCE CARD", fill="#a77545", font=small)
    d.text((95, 330), "Illustrative fixture — not a field photograph", fill="#65744f", font=small)
    d.text(
        (95, 420),
        "Replace with a real photograph when reporting an actual issue.",
        fill="#65744f",
        font=small,
    )
    path = folder / f"{image_id}.jpg"
    image.save(path, quality=90)
    path.chmod(0o600)
    db.add(
        Upload(
            id=image_id,
            owner_id=owner.id,
            filename=path.name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    )
    db.flush()
    return image_id


with SessionLocal() as db:
    synchronize(db)
    if db.scalar(select(User).where(User.email == "admin@nellai.example")):
        print("Demo records already exist; no data was changed.")
        raise SystemExit(0)
    team = Authority(name="Demo civic response team", department="Demonstration local services")
    higher = Authority(name="Demo district review team", department="Demonstration escalation services")
    calendar = Calendar(
        name="Demo working calendar (configure official holidays)",
        weekends=[5, 6],
        holidays=[],
        timezone="Asia/Kolkata",
    )
    boundary = Boundary(
        name="Illustrative Nellai demo area",
        geojson={
            "type": "Polygon",
            "coordinates": [[[77.64, 8.62], [77.87, 8.62], [77.87, 8.84], [77.64, 8.84], [77.64, 8.62]]],
        },
        source="Synthetic demonstration extent; NOT an official administrative boundary",
        verified=False,
    )
    db.add_all([team, higher, calendar, boundary])
    db.flush()
    credentials = []
    people = {}
    for role, name, email in [
        ("SUPER_ADMIN", "Demo Administrator", "admin@nellai.example"),
        ("AUTHORITY", "Demo Authority Officer", "authority@nellai.example"),
        ("CITIZEN", "Demo Citizen", "citizen@nellai.example"),
    ]:
        password = secrets.token_urlsafe(15)
        user = User(
            name=name,
            email=email,
            password_hash=hasher.hash(password),
            role=role,
            authority_id=team.id if role == "AUTHORITY" else None,
        )
        db.add(user)
        db.flush()
        people[role] = user
        credentials.append({"role": role, "email": email, "password": password})
    admin, citizen, officer = people["SUPER_ADMIN"], people["CITIZEN"], people["AUTHORITY"]
    rule = Responsibility(
        category="*",
        authority_id=team.id,
        boundary_id=boundary.id,
        calendar_id=calendar.id,
        deadline_days=3,
        priority=1,
        escalation_steps=[
            {"after_days": 1, "authority_id": None},
            {"after_days": 1, "authority_id": higher.id},
        ],
    )
    db.add(rule)
    db.flush()
    examples = [
        ("Blocked drain near market", "DRAIN_BLOCKAGE", "Palayamkottai", "ASSIGNED", 8.720, 77.741),
        (
            "Waste collection point needs attention",
            "GARBAGE_DUMPING",
            "Melapalayam",
            "IN_PROGRESS",
            8.701,
            77.726,
        ),
        ("Streetlight not working", "STREETLIGHT", "Vannarpettai", "VERIFICATION", 8.723, 77.729),
        ("Road surface damaged", "ROAD_DAMAGE", "Town", "ACKNOWLEDGED", 8.733, 77.701),
        ("Plastic waste along the canal", "PLASTIC_WASTE", "Thachanallur", "ASSIGNED", 8.751, 77.716),
        ("Water stagnation at junction", "WATER_STAGNATION", "Palayamkottai", "IN_PROGRESS", 8.716, 77.760),
        ("Canal flow obstructed", "CANAL_BLOCKAGE", "NGO Colony", "CLOSED", 8.684, 77.733),
        ("Fallen branch on walkway", "FALLEN_TREE", "Tirunelveli Junction", "CLOSED", 8.733, 77.710),
        ("Riverbank litter observation", "RIVER_POLLUTION", "Vannarpettai", "ASSIGNED", 8.728, 77.720),
        ("Drain blockage after rainfall", "DRAIN_BLOCKAGE", "Palayamkottai", "REPORTED", 8.7202, 77.7411),
        ("Public toilet maintenance needed", "PUBLIC_TOILET", "Town", "ASSIGNED", 8.733, 77.695),
        ("Waste near bus stop", "GARBAGE_DUMPING", "Perumalpuram", "CLOSED", 8.700, 77.747),
    ]
    for i, (title, category, locality, status, lat, lon) in enumerate(examples):
        photo = sample_image(db, citizen, title)
        c = Complaint(
            reference=f"DEMO-{i + 1:04}",
            user_id=citizen.id,
            title=title,
            description=f"DEMO RECORD: {title} in {locality}. This is synthetic presentation data, not a real complaint or government record.",
            category=category,
            latitude=lat,
            longitude=lon,
            locality=locality,
            image_id=photo,
            severity="HIGH" if i in [0, 5] else "MEDIUM",
            status="REPORTED",
            cycle=0,
            escalation_level=0,
            created_at=now() - timedelta(days=i * 3 + 1),
        )
        db.add(c)
        db.flush()
        record(db, c, citizen.id, "Demonstration issue reported; synthetic data.")
        if status != "REPORTED":
            auto_assign(db, c)
        if status in ["ACKNOWLEDGED", "IN_PROGRESS", "VERIFICATION", "CLOSED"]:
            c.status = "ACKNOWLEDGED"
            record(db, c, officer.id, "Demo authority acknowledged report.")
        if status in ["IN_PROGRESS", "VERIFICATION", "CLOSED"]:
            c.status = "IN_PROGRESS"
            record(db, c, officer.id, "Demo maintenance work started.")
        if status in ["VERIFICATION", "CLOSED"]:
            c.resolution_image_id = sample_image(db, officer, "Resolution: " + title)
            c.resolution_description = (
                "DEMO RESOLUTION: Example work completed. Citizen verification is required."
            )
            c.resolved_at = now() - timedelta(hours=5)
            c.resolved_by = officer.id
            c.resolution_latitude = lat
            c.resolution_longitude = lon
            c.status = "RESOLVED"
            record(db, c, officer.id, "Demonstration evidence submitted.")
            c.status = "VERIFICATION"
            record(db, c, officer.id, "Awaiting reporting citizen verification.")
        if status == "CLOSED":
            c.status = "CLOSED"
            record(db, c, citizen.id, "Citizen confirmed this demonstration resolution.")
        if i == 0:
            c.deadline = now() - timedelta(days=1)
            c.next_escalation_at = c.deadline
    site = PlantingSite(
        name="Demo community plantation site",
        latitude=8.705,
        longitude=77.75,
        capacity=50,
        ownership_status="UNVERIFIED",
    )
    db.add(site)
    db.flush()
    for i, species in enumerate(
        [
            "Neem · Azadirachta indica",
            "Pongamia · Millettia pinnata",
            "Jamun · Syzygium cumini",
            "Indian beech · Pongamia",
            "Banyan · Ficus benghalensis",
            "Neem · Azadirachta indica",
        ]
    ):
        db.add(
            Tree(
                species=species,
                latitude=8.71 + i * 0.005,
                longitude=77.745 + i * 0.003,
                planting_date=date.today() - timedelta(days=30 + i * 3),
                organization="Demo community group",
                volunteer_group="Demo Nellai volunteers",
                status=["HEALTHY", "HEALTHY", "NEEDS_MAINTENANCE", "PLANTED", "HEALTHY", "DEAD"][i],
                maintenance_date=date.today() + timedelta(days=7),
                created_by=admin.id,
                site_id=site.id,
            )
        )
    db.add(
        Volunteer(
            user_id=citizen.id,
            skills=["Gardening"],
            interests=["Tree planting", "Waste cleanup"],
            locality="Palayamkottai",
            availability="Sunday mornings",
        )
    )
    for i, (title, category, locality) in enumerate(
        [
            ("A morning for a greener Nellai", "TREE_PLANTING", "Palayamkottai"),
            ("Our neighbourhood cleanup", "WASTE_CLEANUP", "Vannarpettai"),
            ("Know your local biodiversity", "BIODIVERSITY_SURVEY", "Town"),
        ]
    ):
        db.add(
            Activity(
                title=title,
                category=category,
                description="DEMO ACTIVITY: A synthetic community event for project demonstration. No real event is scheduled.",
                latitude=8.713 + i * 0.007,
                longitude=77.75,
                locality=locality,
                starts_at=now() + timedelta(days=7 + i * 3),
                capacity=30 + i * 10,
                created_by=admin.id,
            )
        )
    db.add(
        WaterBody(
            name="Tamirabharani — demo observation point",
            kind="RIVER",
            latitude=8.725,
            longitude=77.721,
            source="Illustrative coordinate only; no official water-quality feed is connected",
        )
    )
    db.add(
        WaterBody(
            name="Community pond — demo record",
            kind="POND",
            latitude=8.738,
            longitude=77.759,
            source="Synthetic record for presentation",
        )
    )
    db.commit()
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    for filename, body in [
        ("demo-credentials.json", json.dumps(credentials, indent=2)),
        (
            "DEMO_CREDENTIALS.md",
            "# Private local demo logins\n\nGenerated for this installation. Do not publish this file or use these accounts in production.\n\n| Role | Email | Password |\n|---|---|---|\n"
            + "\n".join(f"| {c['role']} | {c['email']} | {c['password']} |" for c in credentials)
            + "\n",
        ),
    ]:
        path = runtime / filename
        path.write_text(body)
        path.chmod(0o600)
    print("Demo ready. Read runtime/DEMO_CREDENTIALS.md for generated local accounts.")
