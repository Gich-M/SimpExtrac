import os
import sys
import django
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpExtrac.settings')
django.setup()