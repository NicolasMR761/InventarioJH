# run.py — punto de entrada del ejecutable
import sys
import os
from pathlib import Path

# Cuando corre como .exe congelado, ajustar paths
if getattr(sys, 'frozen', False):
    # Directorio donde está el .exe
    BASE_DIR = Path(sys.executable).parent
    # Agregar al path para que los imports funcionen
    sys.path.insert(0, str(BASE_DIR))
    os.chdir(BASE_DIR)

from app.main import main

if __name__ == '__main__':
    main()
