from flask.cli import FlaskGroup
from app_cusdata import app, db  # Import your app and db instance

cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
