"""Small coordinator CLI. Approval input must quote an actual user message."""
import argparse
import json
import re
from pathlib import Path
from workflow import Ledger

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init'); init.add_argument('research_id'); init.add_argument('--base',type=Path,default=Path('C:/Users/USER/Documents/ResearchWorkspace'))
    for cmd in ('status','resume'):
        p=sub.add_parser(cmd); p.add_argument('root',type=Path)
    approval=sub.add_parser('approve'); approval.add_argument('root',type=Path); approval.add_argument('gate',choices=['research_question','outline']); approval.add_argument('--message-file',required=True,type=Path)
    args=parser.parse_args()
    if args.command=='init':
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.research_id):
            parser.error('Use a safe research ID (letters, digits, underscore, dash)')
        root=args.base/args.research_id
        if root.exists(): parser.error('Existing study: use status/resume')
        ledger=Ledger(root,args.research_id); ledger.save()
        for name in ('sources','extracted','tasks','outlines','approvals'): (root/name).mkdir()
        print(str(root)); return
    ledger=Ledger(args.root)
    if args.command=='resume': ledger.resume()
    if args.command=='approve':
        message=args.message_file.read_text(encoding='utf-8').strip()
        if not message: parser.error('Empty approval message')
        ledger.approve(args.gate,{'explicit':True,'message_id':str(args.message_file.resolve()),'verbatim':message})
        ledger.save()
    print(json.dumps({'research_id':ledger.data['research_id'],'version':ledger.data['version'],
                      'gates':{g:ledger.gate(g) for g in ('research_question','outline','manuscript','final')}},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
