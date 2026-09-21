#!/usr/bin/env python3
"""Generate a self-hosted top-languages SVG from the GitHub REST API."""
from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/metrics.languages.svg'
USER='kiran-devhub'
UA={'User-Agent':'kiran-github-profile'}
COLORS={'JavaScript':'#f1e05a','TypeScript':'#3178c6','Python':'#3572A5','HTML':'#e34c26','CSS':'#563d7c','Java':'#b07219','C++':'#f34b7d','C':'#555555','Shell':'#89e051','Go':'#00ADD8','Rust':'#dea584'}

def api(url, token=None):
    req=urllib.request.Request(url,headers=UA)
    if token: req.add_header('Authorization',f'Bearer {token}')
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)

def main():
    token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    totals={}; page=1
    while True:
        repos=api(f'https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=pushed',token)
        if not repos: break
        for repo in repos:
            if repo.get('fork') or repo.get('archived'): continue
            try: langs=api(repo['languages_url'],token)
            except Exception: continue
            for k,v in langs.items(): totals[k]=totals.get(k,0)+v
        if len(repos)<100: break
        page+=1
    top=sorted(totals.items(),key=lambda x:x[1],reverse=True)[:8]
    if not top: top=[('JavaScript',1),('TypeScript',1),('Python',1)]
    total=sum(v for _,v in top)
    W,H=700,220
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Kiran Kumar Behera most used GitHub languages">',
         '<rect width="700" height="220" rx="14" fill="#0d1117" stroke="#30363d"/>',
         '<text x="24" y="34" fill="#7dd3fc" font-family="ui-monospace,monospace" font-size="16" font-weight="700">TOP_LANGUAGES.live</text>',
         '<text x="676" y="34" text-anchor="end" fill="#8b949e" font-family="ui-monospace,monospace" font-size="11">kiran-devhub · live API</text>']
    y=62
    for name,val in top:
        pct=val/total*100
        color=COLORS.get(name,'#8b949e')
        out += [f'<circle cx="31" cy="{y-4}" r="5" fill="{color}"/>',
                f'<text x="44" y="{y}" fill="#c9d1d9" font-family="ui-sans-serif,Arial" font-size="13">{name}</text>',
                f'<rect x="230" y="{y-15}" width="300" height="10" rx="5" fill="#172b45"/>',
                f'<rect x="230" y="{y-15}" width="{300*pct/100:.1f}" height="10" rx="5" fill="{color}"/>',
                f'<text x="548" y="{y}" fill="#c9d1d9" font-family="ui-monospace,monospace" font-size="12">{pct:.1f}%</text>']
        y+=19
    out.append('</svg>')
    OUT.write_text(''.join(out),encoding='utf-8')

if __name__=='__main__': main()
