import click
from datetime import datetime, timezone
from flask.cli import with_appcontext
from app.models import Category, Cycle, PaperCategory
from app.extensions import db

@click.command("seed")
@with_appcontext
def seed_command():
    """Seed the database with an initial superadmin user."""
    if Category.query.count() == 0:
        categories = [
            Category(name="Research Project Staff"),
            Category(name="MBBS/BSc Students"),
            Category(name="PhD Students"),
            Category(name="Junior Residents"),
            Category(name="MSc Students"),
            Category(name="Senior Residents"),
        ]
        db.session.add_all(categories)
        db.session.commit()
        click.echo("Seeded initial categories.")

    if Cycle.query.count() == 0:
        db.session.add(Cycle(
            name="2024-2025",
            start_date=datetime(2024, 7, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 6, 30, tzinfo=timezone.utc),
        ))
        db.session.commit()
        click.echo("Seeded initial cycle.")
    
    if PaperCategory.query.count() == 0:
        paper_categories = [
            PaperCategory(name="Clinical Science"),
            PaperCategory(name="Basic Science"),
        ]
        db.session.add_all(paper_categories)
        db.session.commit()
        click.echo("Seeded initial paper categories.")    