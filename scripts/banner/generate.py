#!/usr/bin/env python3
from __future__ import annotations
import html, math
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT=Path(__file__).resolve().parents[2]; SOURCE=ROOT/"assets/source/kiran.png"; ASSETS=ROOT/"assets"; DATA=Path(__file__).resolve().parent/"data"
W,H=1180,610; LOOP=16.0; INTRO=2.6; TRAVELLERS=19000; FACE_CAP=15000; TRAVEL_N=1800; SEED=20260918
# NOTE: this banner's face used to be unreadable. Root causes and fixes:
#   1. render() only ever animated TRAVELLERS=1250 points even though
#      portrait_points() captures 25-30k real facial-detail points — the
#      other 95%+ were extracted and thrown away. This was because morph
#      states were matched with scipy's exact Hungarian assignment
#      (linear_sum_assignment over a full cdist cost matrix), which on
#      this photo's real, spatially-clustered points didn't just get slow
#      at higher n — it hung past 5 minutes even at n=10000. TRAVELLERS=1250
#      was a workaround to keep that algorithm's runtime bounded, not a
#      considered choice.
#   2. portrait_points() rescaled every point by a fractional 0.95 factor
#      to fit the panel, which forces a round() when a point is later drawn
#      — quietly blurring the fine, high-frequency dither pattern that
#      carries eyes/brows/nose/mouth. Fixed by resizing the working crop to
#      content that already fits the panel with a plain integer offset.
#   3. The traveller dot itself was drawn as a 1.4x1.4 unit square. At this
#      photo's native point spacing (~1 unit) that's large enough to
#      overlap into solid coverage across most of the face, erasing the
#      density gradient the dither pattern uses to encode shading. Fixed by
#      drawing a 0.6x0.6 unit square instead (see the animateTransform path
#      below) — small enough to preserve contrast, still solid enough to
#      read as a filled portrait.
#   4. transport() now matches point sets by sorting both onto a Hilbert
#      space-filling curve instead of exact optimal transport (see
#      _hilbert_index/transport below) — O(n log n) with no data-dependent
#      blowup, and just as smooth visually for this kind of particle morph.
#      That's what makes raising TRAVELLERS at all practical.
# TRAVELLERS/FACE_CAP: face-priority sampling (in render()) keeps every
# Haar-cascade-detected face point up to FACE_CAP (this photo has ~13-14k;
# 15000 keeps effectively all of it) and fills the rest of the TRAVELLERS
# budget from the body/hoodie. 19000 total is a deliberate balance point:
# dense enough for the face to read clearly, while keeping each generated
# SVG in the ~4-5MB range rather than 10MB+ from including every captured
# point. Raise both toward 40000 if file size isn't a concern for you.
THEMES={
"dark":{"bg":"#0A101F","panel":"#0D1628","panel2":"#101B30","line":"#25344C","muted":"#8291A8","text":"#DDE7F5","portrait":"#7DD3FC","chrome":"#22D3EE","accent":"#10B981","shadow":"#02050B"},
"light":{"bg":"#F6F8FA","panel":"#FFFFFF","panel2":"#EDF3F7","line":"#CBD7E1","muted":"#64748B","text":"#172033","portrait":"#075985","chrome":"#0891B2","accent":"#059669","shadow":"#AAB7C4"}}
ROWS=[("Name","Kiran Kumar Behera"),("Role","Developer / Cybersecurity"),("Focus","Secure Web Applications"),("Location","India 🇮🇳"),("Status","Building + Learning + Shipping"),("ToolChain","VS Code · Git · Postman · Figma"),("Core.Lang","JavaScript · TypeScript · Python · Java · C/C++"),("Core.Frontend","React · Next.js · HTML5 · CSS3 · Tailwind"),("Core.Backend","Node.js · Express · REST APIs · JWT · Clerk"),("Core.Database","MongoDB · MySQL · Supabase · Firebase"),("Core.Cloud","Vercel · Netlify · GitHub Pages"),("Security","OWASP Top 10 · Secure Auth · bcrypt · Web Security"),("GitHub","kiran-devhub"),("Mail","kiran.devhub@gmail.com"),("Web","kkbportfolio.vercel.app")]

def floyd(a):
    a=a.astype(np.float32)/255; out=np.zeros_like(a,dtype=bool); h,w=a.shape
    for y in range(h):
        f=y%2==0; xs=range(w) if f else range(w-1,-1,-1); s=1 if f else -1
        for x in xs:
            old=a[y,x]; new=1.0 if old>=.5 else 0.; out[y,x]=new>.5; e=old-new; nx=x+s
            if 0<=nx<w:a[y,nx]+=e*7/16
            if y+1<h:
                if 0<=x-s<w:a[y+1,x-s]+=e*3/16
                a[y+1,x]+=e*5/16
                if 0<=nx<w:a[y+1,nx]+=e/16
    return out

def mask_subject(rgb):
    bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR); h,w=rgb.shape[:2]; m=np.zeros((h,w),np.uint8)
    bg=np.zeros((1,65),np.float64); fg=np.zeros((1,65),np.float64)
    cv2.grabCut(bgr,m,(14,8,w-28,h-18),bg,fg,8,cv2.GC_INIT_WITH_RECT)
    m=((m==cv2.GC_FGD)|(m==cv2.GC_PR_FGD)).astype(np.uint8)
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)); m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,k,iterations=2)
    n,lab,stats,_=cv2.connectedComponentsWithStats(m,8)
    if n>1:m=(lab==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))).astype(np.uint8)
    return cv2.GaussianBlur(m,(3,3),0)

def portrait_points(theme,rng):
    src=ImageOps.exif_transpose(Image.open(SOURCE).convert("RGB"))
    # Crop box re-tuned for the current assets/source/kiran.png (941x1672):
    # old box (70,225,940,1610) had a 0.628 aspect ratio stretched into the
    # 360x430 (0.837 aspect) target, squashing the face ~33% wider than it
    # should be. This box matches the target aspect almost exactly (0.821)
    # while keeping the head + hoodie/shoulders centred.
    # Resize target chosen to map onto the panel with a plain integer
    # offset and NO extra fractional scale factor. The previous version
    # resized to (360,430) and then multiplied every coordinate by .95 to
    # fit the 390x414 panel — that fractional rescale forces every point
    # through a round() when it's later drawn as an integer-ish dot, which
    # quietly blurs exactly the fine, high-frequency dither pattern that
    # carries eyes/brows/nose/mouth. Resizing straight to content that
    # already fits (370x400, centred with a small margin) removes that
    # quantisation step entirely.
    crop=src.crop((10,190,930,1310)).resize((370,400),Image.Resampling.LANCZOS)
    rgb=np.asarray(crop); m=mask_subject(rgb); gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    # Full histogram equalisation (not just local CLAHE) before dithering: a
    # golden-hour lit face sits almost entirely above the 0.5 threshold Floyd–
    # Steinberg dithers against, so without this the whole face was rendering
    # as one solid "on" blob with only eye/nostril shadows poking through.
    # Equalising first spreads the face's own tones across the full 0-255
    # range so the dither pattern actually carries eyes/brows/nose/mouth.
    gray=cv2.equalizeHist(gray)
    gray=cv2.bilateralFilter(gray,7,35,35)
    gray=cv2.addWeighted(gray,1.4,cv2.GaussianBlur(gray,(0,0),1.3),-.4,0)
    gray=np.clip(gray,0,255).astype(np.uint8)
    active=floyd(gray)&(m>.12)
    edges=cv2.Canny(gray,30,100); edges=cv2.dilate(edges,np.ones((2,2),np.uint8),1)>0; edges&=m>.12
    active|=edges
    active &= cv2.erode((m>.12).astype(np.uint8),np.ones((3,3),np.uint8),1)>0
    OX,OY=59,131  # integer offset only — see resize note above
    ys,xs=np.where(active); pts=np.column_stack((OX+xs,OY+ys)).astype(np.float32)
    if len(pts)>40000:pts=pts[rng.choice(len(pts),40000,False)]

    # Locate the face itself (Haar cascade on the same working-resolution
    # grayscale) so render() can guarantee it keeps every point that falls
    # inside it, instead of diluting facial detail with a flat random
    # subsample across the whole head+torso+background point cloud. This is
    # the actual fix for "face not visible clearly": a uniform subsample at
    # any practical TRAVELLERS count thins the face out faster than the eye
    # forgives, even though the shoulders/hoodie still read fine.
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    faces=cascade.detectMultiScale(cv2.equalizeHist(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)),scaleFactor=1.05,minNeighbors=4,minSize=(60,60))
    if len(faces):
        fx,fy,fw,fh=max(faces,key=lambda f:f[2]*f[3])
        # generous padding: hair/forehead above, jaw below, ears either side
        x0=max(0,fx-fw*0.38); x1=fx+fw+fw*0.38
        y0=max(0,fy-fh*0.85); y1=fy+fh+fh*0.55
        face_box=(OX+x0,OY+y0,OX+x1,OY+y1)
    else:
        face_box=None
    return pts,face_box



def shape(kind,size=360):
    im=Image.new("L",(size,size),0); d=ImageDraw.Draw(im); c=size/2
    if kind=="shield":
        d.polygon([(c,30),(c+120,76),(c+98,190),(c,315),(c-98,190),(c-120,76)],fill=255)
        d.ellipse((c-38,c-8,c+38,c+68),fill=0); d.rectangle((c-10,c+42,c+10,c+95),fill=0)
    elif kind=="code":
        d.line([(145,82),(58,180),(145,278)],fill=255,width=34,joint="curve"); d.line([(215,82),(302,180),(215,278)],fill=255,width=34,joint="curve"); d.line([(205,55),(155,305)],fill=255,width=30)
    else:
        d.rounded_rectangle((60,126,300,300),radius=28,outline=255,width=28); d.arc((110,40,250,192),180,360,fill=255,width=28); d.line((180,190,180,248),fill=255,width=24)
    return im

def sample(kind,rng,n):
    a=np.asarray(shape(kind)); y,x=np.where(a>127); q=rng.choice(len(x),n,replace=len(x)<n)
    return np.column_stack((92+x[q]*.68,170+y[q]*.68)).astype(np.float32)

def _hilbert_index(order,x,y):
    # Classic xy2d Hilbert-curve mapping, vectorised over numpy arrays.
    # Used instead of exact optimal-transport (linear_sum_assignment) for
    # matching point sets between morph states: on this photo's real,
    # spatially-clustered point cloud (thousands of near-duplicate points
    # packed into eyes/brows/hair), scipy's Hungarian solver's runtime blew
    # up far past what its synthetic-random-data benchmark suggested (many
    # near-tied minimum-cost entries are a known worst case for that
    # algorithm family). A space-filling-curve sort is O(n log n) with no
    # data-dependent blowup, and produces just as smooth a morph for this
    # kind of particle animation.
    x=x.astype(np.int64).copy(); y=y.astype(np.int64).copy()
    d=np.zeros(x.shape,dtype=np.int64)
    s=1<<(order-1)
    while s>0:
        rx=((x & s)>0).astype(np.int64)
        ry=((y & s)>0).astype(np.int64)
        d+=s*s*((3*rx)^ry)
        swap=ry==0
        flip=swap & (rx==1)
        x_f=np.where(flip, s-1-x, x)
        y_f=np.where(flip, s-1-y, y)
        x_new=np.where(swap, y_f, x_f)
        y_new=np.where(swap, x_f, y_f)
        x,y=x_new,y_new
        s>>=1
    return d

def transport(a,b):
    order=11  # 2^11=2048, comfortably covers the 1180x610 canvas
    da=_hilbert_index(order,a[:,0],a[:,1])
    db=_hilbert_index(order,b[:,0],b[:,1])
    ia=np.argsort(da,kind="stable"); ib=np.argsort(db,kind="stable")
    o=np.empty_like(b); o[ia]=b[ib]; return o
def esc(s):return html.escape(str(s),quote=True)
def tw(s,z):return len(s)*z*.605
def leader(a,b,y):return "".join(f"M{x:.1f} {y:.1f}h1" for x in np.arange(a,b,5))

def render(theme,portrait,face_box,rng):
    t=THEMES[theme]
    # Face-priority sampling: keep every captured point that falls inside the
    # detected face box (padded for hair/jaw/ears), then fill the remaining
    # TRAVELLERS budget with a random sample of the rest of the body/hoodie.
    # A flat random sample across the whole point cloud spends most of its
    # budget on the (large, low-detail-need) torso and starves the face.
    if face_box is not None:
        x0,y0,x1,y1=face_box
        in_face=(portrait[:,0]>=x0)&(portrait[:,0]<=x1)&(portrait[:,1]>=y0)&(portrait[:,1]<=y1)
        face_pts=portrait[in_face]; rest_pts=portrait[~in_face]
    else:
        face_pts=portrait[:0]; rest_pts=portrait
    if len(face_pts)>FACE_CAP:
        face_pts=face_pts[rng.choice(len(face_pts),FACE_CAP,False)]
    remaining=max(0,TRAVELLERS-len(face_pts))
    if remaining and len(rest_pts):
        rest_n=min(remaining,len(rest_pts))
        rest_pts=rest_pts[rng.choice(len(rest_pts),rest_n,False)]
    else:
        rest_pts=rest_pts[:0]
    src=np.concatenate([face_pts,rest_pts]) if len(face_pts) else rest_pts
    # IMPORTANT ARCHITECTURE NOTE — read this before changing TRAVELLERS.
    # Earlier versions animated (SMIL animateTransform) every one of these
    # ~19000 points individually to morph portrait->shield->code->lock->
    # portrait. That rendered perfectly in isolated PNG snapshots/tests, but
    # on the real, live GitHub page it still looked wrong — because tens of
    # thousands of *concurrently, individually SMIL-animated* elements is
    # something browsers render inconsistently/poorly under real load (frame
    # drops, imprecise sub-pixel positioning, degraded rasterization), which
    # a static image test can't catch at all. That mismatch — "fine in my
    # test, bad in the real browser" — is exactly what happened last round.
    # The fix is architectural, not another size/count tweak:
    #   - The DENSE, camera-accurate portrait (src, up to TRAVELLERS points)
    #     is drawn with the cheap static "batch" paths below: ~32 <path>
    #     elements total (not one per point), each just a fixed shape with
    #     ONE opacity <animate>. That's trivial for any browser to rasterise
    #     crisply regardless of point count, because nothing is *moving*.
    #   - Only a SMALL subset (TRAVEL_N points) is individually animated to
    #     actually morph into the shield/code/lock shapes. Icons are bold,
    #     simple glyphs — they don't need thousands of points to read
    #     clearly, so this stays light for the browser (smooth, precise)
    #     while the dense batch layer's own opacity cycle (see below) makes
    #     sure the *portrait* is only ever carried by the cheap, reliable
    #     layer, never by the thing straining under thousands of animations.
    travel_n=min(TRAVEL_N,len(src))
    travel_idx=rng.choice(len(src),travel_n,False) if travel_n<len(src) else np.arange(len(src))
    travel=src[travel_idx]
    n=len(travel)
    sh=sample("shield",rng,n); co=sample("code",rng,n); lo=sample("lock",rng,n)
    frames=[travel,travel,transport(travel,sh),sh,transport(sh,co),co,transport(co,lo),lo,travel]
    times=[0,3,4.3,6,7.3,9,10.3,13,16]; kt=";".join(f"{x/LOOP:.4f}".rstrip("0").rstrip(".") for x in times)
    # Portrait-visibility keytimes for the dense batch layer: opaque during
    # the "portrait" hold (0-3s and the 13-16s wrap), transparent whenever
    # the travellers are shaped into shield/code/lock (4.3-13s) so the two
    # layers never fight each other.
    vis_kt=";".join(f"{x/LOOP:.4f}".rstrip("0").rstrip(".") for x in [0,3,4.3,13,16])
    font="ui-monospace,SFMono-Regular,Consolas,monospace"
    p=[f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">Kiran Kumar Behera — Developer / Cybersecurity</title><desc id="desc">Animated terminal profile with a detailed point portrait, security shield, code and authentication lock.</desc>
<defs><filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" flood-opacity=".28"/></filter><filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feFlood flood-color="{t["chrome"]}" flood-opacity=".35"/><feComposite in2="b" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="{t["line"]}" stroke-opacity=".18"/></pattern><clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath></defs>
<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/><rect x="13" y="13" width="1154" height="584" rx="13" fill="{t["panel"]}" stroke="{t["line"]}" filter="url(#shadow)"/><path d="M13 62H1167" stroke="{t["line"]}"/>
<circle cx="38" cy="38" r="6" fill="#FF5F57"/><circle cx="59" cy="38" r="6" fill="#FEBC2E"/><circle cx="80" cy="38" r="6" fill="#28C840"/>
<text x="590" y="43" text-anchor="middle" fill="{t["chrome"]}" font-family="{font}" font-size="13">kiran@github:~$ ./profile.sh --live</text><text x="1138" y="43" text-anchor="end" fill="{t["muted"]}" font-family="{font}" font-size="12">v13.0.0</text>
<rect x="35" y="88" width="418" height="472" rx="6" fill="{t["panel2"]}" stroke="{t["line"]}"/><path d="M35 124H453" stroke="{t["line"]}"/><text x="49" y="111" fill="{t["chrome"]}" font-family="{font}" font-size="13" font-weight="700" letter-spacing="1.2">VISUAL.MAP</text><text x="438" y="111" text-anchor="end" fill="{t["muted"]}" font-family="{font}" font-size="11">370×400 / FACE DETAIL</text>
<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 539h12M49 539v-12M439 539h-12M439 539v-12" fill="none" stroke="{t["chrome"]}" opacity=".55"/><g clip-path="url(#visualClip)" shape-rendering="crispEdges"><rect x="49" y="124" width="390" height="414" fill="url(#grid)"/><g>''']
    groups=np.array_split(np.arange(len(src)),32)
    for j,idx in enumerate(groups):
        d="".join(f"M{int(round(x))} {int(round(y))}h1" for x,y in src[idx])
        stagger=.02+j*.05
        p.append(
            f'<path d="{d}" fill="none" stroke="{t["portrait"]}" stroke-width="1.3" opacity="0">'
            f'<animate attributeName="opacity" begin="{stagger:.3f}s" dur=".7s" values="0;1" fill="freeze"/>'
            f'<animate attributeName="opacity" begin="{INTRO}s" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{vis_kt}" values="1;1;0;0;1"/>'
            f'</path>'
        )
    for i in range(n):
        vals=";".join(f"{q[i,0]:.1f} {q[i,1]:.1f}" for q in frames)
        p.append(f'<path d="M-.35-.35h.7v.7h-.7z" fill="{t["portrait"]}"><animateTransform attributeName="transform" type="translate" begin="{INTRO}s" dur="{LOOP}s" repeatCount="indefinite" calcMode="linear" keyTimes="{kt}" values="{vals}"/></path>')
    p.append(f'''</g><rect x="49" y="124" width="390" height="3" fill="{t["chrome"]}" opacity=".22"><animate attributeName="y" values="126;535;126" dur="5.5s" repeatCount="indefinite"/></rect></g><text x="58" y="551" fill="{t["muted"]}" font-family="{font}" font-size="10">PTS {len(portrait):05d} · FACE-DETAIL / SERPENTINE</text>
<rect x="474" y="88" width="672" height="472" rx="6" fill="{t["panel2"]}" stroke="{t["line"]}"/><path d="M474 124H1146" stroke="{t["line"]}"/><text x="490" y="111" fill="{t["chrome"]}" font-family="{font}" font-size="13" font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text><circle cx="915" cy="106" r="4" fill="{t["accent"]}"><animate attributeName="opacity" values="1;.25;1" dur="1.5s" repeatCount="indefinite"/></circle><text x="927" y="111" fill="{t["accent"]}" font-family="{font}" font-size="12" font-weight="700">LIVE</text><rect x="982" y="94" width="146" height="24" rx="12" fill="{t["chrome"]}" opacity=".16" stroke="{t["chrome"]}"/><text x="1055" y="111" text-anchor="middle" fill="{t["chrome"]}" font-family="{font}" font-size="14" font-weight="700">@kiran-devhub</text>''')
    y=153; vr=1127
    for lab,val in ROWS:
        vl=tw(val,14); ll=tw(lab,14); p.append(f'<text x="491" y="{y}" fill="{t["muted"]}" font-family="{font}" font-size="14">{esc(lab)}</text><path d="{leader(491+ll+12,vr-vl-12,y-4)}" fill="none" stroke="{t["line"]}" stroke-width="1" shape-rendering="crispEdges"/><text x="{vr}" y="{y}" text-anchor="end" fill="{t["text"]}" font-family="{font}" font-size="14" textLength="{vl:.1f}" lengthAdjust="spacingAndGlyphs">{esc(val)}</text>'); y+=23
    p.append(f'''<path d="M490 530H1130" stroke="{t["line"]}"/><text x="491" y="548" fill="{t["accent"]}" font-family="{font}" font-size="11">● ALL SYSTEMS NOMINAL</text><text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" font-family="{font}" font-size="11">IST · INDIA NODE</text><text x="49" y="582" fill="{t["chrome"]}" font-family="{font}" font-size="12">&gt; build · secure · share · repeat_</text><text x="1130" y="582" text-anchor="end" fill="{t["muted"]}" font-family="{font}" font-size="11">GitHub · Portfolio · Email · Open Source</text></svg>''')
    return "".join(p)

def main():
    if not SOURCE.exists():raise SystemExit(f"Missing {SOURCE}")
    ASSETS.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
    for i,theme in enumerate(THEMES):
        rng=np.random.default_rng(SEED+i); pts,face_box=portrait_points(theme,rng); np.save(DATA/f"portrait-{theme}.npy",pts)
        out=ASSETS/f"banner-{theme}.v13.svg"; out.write_text(render(theme,pts,face_box,np.random.default_rng(SEED+100+i)),encoding="utf-8")
        print(out,len(pts),out.stat().st_size)
if __name__=="__main__":main()
