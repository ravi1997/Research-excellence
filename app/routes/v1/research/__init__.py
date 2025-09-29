from flask import Blueprint

research_bp = Blueprint('research_bp', __name__)

from app.routes.v1.research import cycle_route, category_route, author_route, abstract_route, award_route, papercategory_route, best_paper_route, grading_type_route, grading_route