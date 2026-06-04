
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE = os.path.join(BASE_DIR, 'faktura.db')

SECRET_KEY = 'c4f86b6fc62f70c01bca9a3bc584ab3b1cfedc3aa92809c7'

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'vorlagen')

OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')

