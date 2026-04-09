import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'faktura.db')
SECRET_KEY = os.urandom(24).hex()
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'vorlagen')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
