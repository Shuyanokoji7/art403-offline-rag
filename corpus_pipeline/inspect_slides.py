"""Produce overview/contact sheets or exact native-pixel crops for vision review.

These derivatives never replace the mandatory 300 DPI master PNGs.
"""
import argparse
from PIL import Image, ImageDraw
from common import ROOT, write_json

def main():
    p=argparse.ArgumentParser(); p.add_argument('module',type=int); p.add_argument('pages',nargs='+',type=int)
    p.add_argument('--width',type=int,default=1500); p.add_argument('--crop',nargs=4,type=int,metavar=('X','Y','W','H'))
    p.add_argument('--contact',action='store_true'); args=p.parse_args()
    out=ROOT/'corpus_data/review_images'; out.mkdir(parents=True,exist_ok=True); images=[]
    for page in args.pages:
        src=ROOT/f'slides/module-{args.module}/page_{page}.png'
        with Image.open(src) as raw:
            if args.crop:
                x,y,w,h=args.crop
                if x<0 or y<0 or x+w>raw.width or y+h>raw.height: raise ValueError('Crop outside image')
                im=raw.crop((x,y,x+w,y+h)); suffix='crop-'+'-'.join(map(str,args.crop))
            else:
                im=raw.copy(); im.thumbnail((args.width,args.width)); suffix=f'overview-{args.width}'
            path=out/f'm{args.module}-p{page:02d}-{suffix}.png'; im.save(path)
            write_json(path.with_suffix('.json'),dict(source=str(src.relative_to(ROOT)),crop=args.crop,output_size=im.size,resized=not bool(args.crop)))
            images.append((page,im)); print(path)
    if args.contact:
        w=max(im.width for _,im in images); h=max(im.height for _,im in images)+30
        sheet=Image.new('RGB',(w*2,h*((len(images)+1)//2)),'#eeeeee'); d=ImageDraw.Draw(sheet)
        for i,(page,im) in enumerate(images):
            x=(i%2)*w; y=(i//2)*h; d.text((x+8,y+8),f'Module {args.module} / slide {page}',fill='black'); sheet.paste(im,(x,y+30))
        path=out/f'm{args.module}-contact-{args.pages[0]}-{args.pages[-1]}.png'; sheet.save(path); print(path)

if __name__=='__main__': main()
