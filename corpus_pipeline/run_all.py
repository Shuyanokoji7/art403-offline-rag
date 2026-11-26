"""Resume all deterministic stages; review attestation is deliberately not automatic."""
import subprocess,sys
from pathlib import Path

if __name__=='__main__':
    folder=Path(__file__).resolve().parent
    for script in ['stage1_render.py','stage1_entities.py','stage2_analyze.py','stage3_ground.py','stage4_articles.py','stage5_manifest.py','build_index.py','audit.py']:
        subprocess.run([sys.executable,str(folder/script)],check=True,cwd=folder.parent)
