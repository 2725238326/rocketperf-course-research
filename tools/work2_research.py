"""Archive public research originals and validate their provenance (stdlib only)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from projectlib import ROOT, atomic_json, atomic_text, digest, local_path, lock, read_json

INDEX = 'Work2/research/data/source-index.json'
MAX_BYTES = 24_000_000
LEGACY_INDEX = '调研/原始来源/来源文件索引.json'


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}: self.skip+=1
        if tag in {'p','div','br','tr','h1','h2','h3','li','section'}: self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'} and self.skip: self.skip-=1
        if tag in {'p','div','tr','li'}: self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)
    def text(self):
        return '\n'.join(line.strip() for line in ''.join(self.parts).splitlines() if line.strip())+'\n'


def fetch(source_id,url,kind='text',discovery='existing-primary-source'):
    if not re.fullmatch(r'W2-[A-Z]+\d{2,3}',source_id): raise ValueError('Use a stable W2 source ID')
    parsed=urlsplit(url)
    if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Public HTTP(S) URL required')
    index=read_json(ROOT/INDEX) if (ROOT/INDEX).is_file() else {'schema_version':1,'sources':[]}
    if any(r['id']==source_id for r in index['sources']): raise ValueError('Source ID exists; use a dated new identity')
    row={'id':source_id,'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'discovery':discovery,'available':False,'read_scope':'downloaded_only','status':'REQUEST_FAILED'}
    try:
        request=Request(url,headers={'User-Agent':'Work2-Course-Research/1.0 (public-source-verification)'})
        with urlopen(request,timeout=40) as response:
            body=response.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES: raise ValueError('Source exceeds archive budget; record a storage decision first')
            row.update(final_url=response.url,http_status=response.status,content_type=response.headers.get('Content-Type',''))
        suffix={'text':'.txt','html':'.html','json':'.json','pdf':'.pdf'}[kind]
        if kind=='pdf' and not body.startswith(b'%PDF-'): raise ValueError('Expected PDF signature absent')
        target=ROOT/f'Work2/research/raw/20261024/{source_id}{suffix}'
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream: stream.write(body)
        row.update(available=True,status='SAVED',path=target.relative_to(ROOT).as_posix(),bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        if kind=='html':
            reader=PageText(); reader.feed(body.decode('utf-8',errors='replace'))
            atomic_text(ROOT/f'build/work2/reading/20261024/{source_id}.txt',reader.text())
    except HTTPError as exc:
        row.update(http_status=exc.code,error_type='HTTPError')
    except (URLError,TimeoutError,OSError,ValueError) as exc:
        row.update(error_type=type(exc).__name__)
    with lock(ROOT,'research-sources'):
        index=read_json(ROOT/INDEX) if (ROOT/INDEX).is_file() else {'schema_version':1,'sources':[]}
        if any(r['id']==source_id for r in index['sources']): raise ValueError('Source ID already registered')
        index['sources'].append(row)
        atomic_json(ROOT/INDEX,index)
    return {k:row[k] for k in ['id','status','http_status','bytes','path','error_type'] if k in row}


def reuse(source_id,legacy_id,root=ROOT):
    """Reference a hash-verified historical original without refreshing its date."""
    if not re.fullmatch(r'W2-[A-Z]+\d{2,3}',source_id): raise ValueError('Use a stable W2 source ID')
    legacy=next((r for r in read_json(root/LEGACY_INDEX) if r['id']==legacy_id),None)
    if legacy is None or not legacy.get('available'): raise ValueError('Available historical source required')
    path=local_path(root,'调研/原始来源/'+legacy['file'])
    if not path.is_file() or path.stat().st_size!=legacy['bytes'] or digest(path)!=legacy['sha256'].lower():
        raise ValueError('Historical source byte identity mismatch')
    if not legacy.get('saved_at'): raise ValueError('Historical retrieval date required')
    row={'id':source_id,'url':legacy['url'],'retrieved_at':legacy['saved_at'],
         'registered_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'discovery':'Historical original reused in place; no new online retrieval',
         'available':True,'read_scope':'downloaded_only','status':'REUSED_IN_PLACE',
         'path':path.relative_to(root).as_posix(),'bytes':legacy['bytes'],'sha256':digest(path),
         'original_source_id':legacy_id,'original_index':LEGACY_INDEX}
    with lock(root,'research-sources'):
        index=read_json(root/INDEX) if (root/INDEX).is_file() else {'schema_version':1,'sources':[]}
        if any(r['id']==source_id for r in index['sources']): raise ValueError('Source ID already registered')
        index['sources'].append(row)
        atomic_json(root/INDEX,index)
    if path.suffix in {'.txt','.html'}:
        reader=PageText();reader.feed(path.read_text(encoding='utf-8'))
        atomic_text(root/f'build/work2/reading/20261024/{source_id}.txt',reader.text())
    return {k:row[k] for k in ['id','status','path','retrieved_at','original_source_id']}


def verify(root=ROOT):
    if not (root/INDEX).is_file(): return {'sources':0,'checked':0,'issues':[]}
    issues=[]; checked=0; ids=set()
    try:
        rows=read_json(root/INDEX)['sources']
        for row in rows:
            if row['id'] in ids: issues.append('Duplicate research source ID: '+row['id'])
            ids.add(row['id'])
            if not row['available']: continue
            path=local_path(root,row['path'])
            if not path.is_file() or path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
                issues.append('Research original missing or changed: '+row['id'])
            else: checked+=1
        for filename,field in [('claims.json','claims'),('parameter-observations.json','observations')]:
            path=root/'Work2/research/data'/filename
            if not path.exists(): continue
            data=read_json(path)[field]
            seen=set()
            for record in data:
                if record['id'] in seen: issues.append('Duplicate record in '+filename)
                seen.add(record['id'])
                for sid in record.get('source_ids',[]):
                    if sid not in ids: issues.append('Unknown source '+sid+' in '+filename)
                if filename=='claims.json' and record['classification']=='verified_fact' and not record.get('source_ids'):
                    issues.append('Verified claim without source: '+record['id'])
                if filename=='claims.json' and record['classification']=='verified_fact':
                    by_id={s['id']:s for s in rows}
                    for sid in record.get('source_ids',[]):
                        if sid in by_id and (not by_id[sid]['available'] or not by_id[sid].get('content_usable',True) or by_id[sid].get('read_scope')=='downloaded_only'):
                            issues.append('Verified claim cites unavailable or unread source: '+record['id'])
                if filename=='parameter-observations.json' and record.get('classification')=='unknown' and record.get('value') is not None:
                    issues.append('Unknown parameter contains a value: '+record['id'])
        if (root/'Work2/research/data/coverage.json').is_file():
            from work2_survey_data import expected_data
            index=read_json(root/INDEX)
            for relative,value in expected_data(index,root).items():
                if not (root/relative).is_file() or read_json(root/relative)!=value:
                    issues.append('Curated research data drift: '+relative)
        if (root/'Work2/research/data/vehicle-evidence-v1.json').is_file():
            from work2_vehicle_data import verify as verify_vehicles
            issues.extend(verify_vehicles(root))
    except (KeyError,TypeError,OSError,ValueError) as exc:
        issues.append('Research provenance check: '+str(exc))
    return {'sources':len(ids),'checked':checked,'issues':issues}


def compare_thermo(root=ROOT):
    from thermo_data import parse_selected
    original=root/'Work2/火箭发动机原理-第五章推力室的热力计算/NASA关于热力学性质的九系数新形式数据库/thermo.inp'
    pinned=root/'调研/原始来源/20261003_cea_v3.3.4/thermo.inp'
    left=parse_selected(original.read_text(encoding='ascii'))
    right=parse_selected(pinned.read_text(encoding='ascii'))
    fields=['molar_mass_kg_per_kmol','elements','formation_enthalpy_298_j_mol','ranges']
    rows=[]
    for a,b in zip(left,right):
        if a['id']!=b['id']: raise ValueError('Selected species identity differs')
        delta=[f for f in fields if a[f]!=b[f]]
        rows.append({'species':a['id'],'original_line':a['source_line'],'pinned_line':b['source_line'],
                     'different_fields':delta,'source_note_equal':a['source_note']==b['source_note'],'data_equal':not delta})
    return {'schema_version':1,'kind':'source_data_comparison','created_on':'2026-10-24',
            'parser':'tools/thermo_data.py:parse_selected',
            'scope':'10 selected neutral gases only; no full-database or transport equivalence claim',
            'inputs':[{'path':p.relative_to(root).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size} for p in [original,pinned]],
            'byte_identical':digest(original)==digest(pinned),'species':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    get=sub.add_parser('fetch');get.add_argument('id');get.add_argument('url');get.add_argument('--kind',choices=['text','html','json','pdf'],default='text');get.add_argument('--discovery',default='existing-primary-source')
    use=sub.add_parser('reuse');use.add_argument('id');use.add_argument('legacy_id')
    sub.add_parser('verify')
    sub.add_parser('compare-thermo')
    args=parser.parse_args()
    if args.command=='compare-thermo':
        result=compare_thermo()
        atomic_json(ROOT/'Work2/research/data/thermo-comparison.json',result)
    elif args.command=='reuse':
        result=reuse(args.id,args.legacy_id)
    else:
        result=verify() if args.command=='verify' else fetch(args.id,args.url,args.kind,args.discovery)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(bool(result.get('issues')))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
