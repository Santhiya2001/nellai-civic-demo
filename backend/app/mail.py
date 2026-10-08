"""Render the same authority message for delivery and administrator preview."""

from app.models import Authority


def complaint_alert_message(db, cfg, complaint):
    authority = (
        db.get(Authority, complaint.assigned_authority_id)
        if complaint.assigned_authority_id
        else None
    )
    url = f"{cfg.public_url.rstrip('/')}/#complaints/{complaint.id}"
    return {
        "subject": f"New complaint: {complaint.reference}",
        "body": (
            "A new civic complaint has been submitted.\n\n"
            f"Reference: {complaint.reference}\n"
            f"Title: {complaint.title}\n"
            f"Category: {complaint.category.replace('_', ' ').title()}\n"
            f"Locality: {complaint.locality or 'Not specified'}\n"
            f"Coordinates: {complaint.latitude}, {complaint.longitude}\n"
            f"Assigned team: {authority.name if authority else 'Pending assignment'}\n\n"
            f"Description:\n{complaint.description}\n\n"
            "Sign in with an authorized account to review the report and its photograph:\n"
            f"{url}\n"
        ),
    }
