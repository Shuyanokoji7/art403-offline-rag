"""Render all PDF pages at 300 DPI; resume by content hash and validate dimensions."""
import argparse, concurrent.futures, re, subprocess
from pathlib import Path
from PIL import Image
from common import ROOT, file_hash, index_rows, read_json, write_json, write_text

def render(task):
    pdf, page, target = task
    subprocess.run(['pdftoppm','-r','300','-f',str(page),'-l',str(page),'-singlefile','-png',str(pdf),str(target.with_suffix(''))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    with Image.open(target) as im:
        if im.size != (3000,2250): raise ValueError(f'Unexpected size: {target}: {im.size}')
    return str(target.relative_to(ROOT))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--jobs',type=int,default=4); args=parser.parse_args()
    inventory=[]; jobs=[]
    for pdf in sorted(ROOT.glob('ART403_Module *.pdf')):
        module=int(re.search(r'Module (\d+)',pdf.name)[1]); sha=file_hash(pdf)
        info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
        count=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
        folder=ROOT/f'slides/module-{module}'; folder.mkdir(parents=True,exist_ok=True)
        stamp=folder/'render.json'; old=read_json(stamp) if stamp.exists() else {}
        for page in range(1,count+1):
            target=folder/f'page_{page}.png'
            valid=False
            if old.get('pdf_sha256')==sha and target.exists():
                try:
                    with Image.open(target) as im: valid=im.size==(3000,2250) and im.info.get('dpi',(0,))[0]>299
                except (OSError,ValueError): pass
            if not valid: jobs.append((pdf,page,target))
        txt=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
        texts=txt.split('\f')
        for page in range(1,count+1): write_text(ROOT/f'corpus_data/slide_text/module-{module}/page_{page}.txt',texts[page-1])
        meta=dict(module=module,pdf=pdf.name,pdf_sha256=sha,pages=count,dpi=300,width=3000,height=2250)
        inventory.append(meta)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i,path in enumerate(pool.map(render,jobs),1):
            if i%10==0 or i==len(jobs): print(f'Rendered {i}/{len(jobs)}: {path}',flush=True)
    for meta in inventory: write_json(ROOT/f"slides/module-{meta['module']}/render.json",meta)
    write_json(ROOT/'corpus_data/inventory.json',inventory)
    rows=index_rows(); write_json(ROOT/'corpus_data/index_rows.json',rows)
    print(f"{sum(v['pages'] for v in inventory)} pages, {len(rows)} index rows; {len(jobs)} pages rendered.")

if __name__=='__main__': main()
