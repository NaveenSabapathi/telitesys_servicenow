from flask import Blueprint

crm_bp = Blueprint('crm', __name__, template_folder='templates')

from . import routes