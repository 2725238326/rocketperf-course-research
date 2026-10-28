"""Selected frontier reading records; fixed campaign membership, no latest/SOTA claim."""
from __future__ import annotations

import argparse
import json
import sys

from projectlib import ROOT, atomic_json, read_json
from work2_research import INDEX

OUTPUT='Work2/research/data/frontier-20261028-v1.json'
SCOPES={
    'W2-F01':'arXiv 2605.18264v1 abstract/authors/submission history; no performance reproduction',
    'W2-F02':'FastChem 4 v1 sections 2.1-2.3: gas Newton accelerator, log densities/LSE, separate condensate regularisation; selected methods reading only',
    'W2-F03':'arXiv 2409.15086v1 abstract/history and 2026 journal/DOI metadata',
    'W2-F04':'Combustion Toolbox v1 sections 2.1,2.4,3.1,3.3 and rocket model outline; NASA9/data, MATLAB/GPL, outer Newton-Steffensen; no code run',
    'W2-F05':'HAL v3 metadata, abstract, versions and full-text link; aqueous object explicitly checked',
    'W2-F06':'HTTP403; no publisher full text obtained',
    'W2-F07':'Author HAL v3 PDF pp2-3,17-18,23-25: abstract/aqueous assumptions and numerical protocol/results; pages3/25 rendered and visually checked; 34-page file not fully read',
}


def expected(index):
    by_id={s['id']:s for s in index['sources']}
    for sid,scope in SCOPES.items():
        if sid not in by_id or by_id[sid].get('read_scope')!=scope: raise ValueError('Frontier reading scope missing: '+sid)
    claims=[
        dict(id='F001',classification='verified_fact',source_ids=['W2-F01','W2-F02'],
             statement='FastChem 4 v1于2026-05-18提交；多维Newton为标准迭代慢收敛时的加速器，默认触发400次，论文图2实验采用300次。',
             locator='abstract submission history; section2.1.2-2.1.3',
             short_quote='not to implement the Newton method as the default solver',
             limitation='天体/大气给定p-T化学；没有本项目HP或Windows C移植性能证据。'),
        dict(id='F002',classification='verified_fact',source_ids=['W2-F02'],
             statement='FastChem 4将元素数密度改用对数并采用log-sum-exp；凝相的Levenberg–Marquardt和扰动Hessian回退另属凝相系统。',
             locator='sections2.2-2.3',short_quote='logarithmic element densities rather than linear ones',
             limitation='本项目已有log-sum-exp；论文所报天体算例迭代比不是本项目收益。'),
        dict(id='F003',classification='verified_fact',source_ids=['W2-F03','W2-F04'],
             statement='Combustion Toolbox原稿为2024-09-23；arXiv元数据列CPC320(2026)110004及10.1016/j.cpc.2025.110004；MATLAB/GPLv3，NASA9但默认可含Burcat/ATcT相关数据。',
             locator='arXiv metadata; sections2.1 and3.3',short_quote='implicit third-order Newton-Steffensen root-finding algorithm',
             limitation='二阶Newton指收敛阶，不是二阶导数法；其默认相对停止准则不同，不能直接按迭代数排名或默认数据相同。'),
        dict(id='F004',classification='verified_fact',source_ids=['W2-F05','W2-F07'],
             statement='Jonval等JCP2025/HALv3研究稀水溶液单相平衡；参数化/Cartesian重构及globalization用于低浓度稳健性。数值测试均1bar、298.15K，Julia/ForwardDiff；对象为H2O、海水、水-混凝土。',
             locator='PDF pp3,17-18,23-25 (printed pp2,16-17,22-24)',
             short_quote='diluted solutions of aqueous species',
             limitation='低浓度压力集和初始化分组可借鉴；不是现成高温九CHO HP算法或验证样本。'),
        dict(id='F005',classification='inference',source_ids=['W2-F02','W2-F04','W2-F07'],
             statement='后续优先比较可靠端点/序列热启动与有夹逼保护的导数辅助HP；仅在实测病态出现时尝试残差缩放/正则回退。',
             locator='WBASE cumulative diagnostics plus selected methods; project recommendation',short_quote='',
             limitation='WREF/WEXP须另冻结工况/阈值/预算；本轮未实现这些策略或证明收益。'),
    ]
    return dict(schema_version=1,as_of='2026-10-28',scope='Selected targeted frontier reading, not exhaustive survey or SOTA assessment',
        search=dict(successful_topic='20261028_wbase_frontier_b',search_calls=7,
                    failed_topic='20261028_wbase_frontier_a',failed_http_status=502,
                    note='MaxCalls=4 was prompt guidance; seven tool-call records returned. Model summary independently checked.'),
        sources=[dict(id=sid,available=by_id[sid]['available'],read_scope=scope,
                      sha256=by_id[sid].get('sha256'),path=by_id[sid].get('path')) for sid,scope in SCOPES.items()],
        claims=claims,corrections=[
            '检索摘要把N2或Ar插入九CHO列表；本项目物种含CH4、不含N2/Ar，未按返回建议改模型。',
            '检索摘要称三项均可直接用于小型HP；原文FastChem给定p-T、JCP稀水溶液，HP移植适用性未证明。',
            'FastChem默认400次触发与图2实验300次区分；不将论文迭代倍率当墙钟/本项目加速。',
        ])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    index=read_json(ROOT/INDEX)
    if not args.check:
        for row in index['sources']:
            if row['id'] in SCOPES:
                row['read_scope']=SCOPES[row['id']]
                row['content_usable']=row['id']!='W2-F06'
                row['verified_on']='2026-10-28'
        atomic_json(ROOT/INDEX,index)
    data=expected(index)
    if args.check:
        if read_json(ROOT/OUTPUT)!=data: raise ValueError('Frontier selected data drift')
    else: atomic_json(ROOT/OUTPUT,data)
    print(json.dumps(dict(sources=len(SCOPES),available=sum(s['available'] for s in data['sources']),claims=len(data['claims'])),ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
