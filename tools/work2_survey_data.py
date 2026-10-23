"""Curated first-round survey observations; generates traceable JSON, never engine inputs."""
from __future__ import annotations
import argparse
import json
import sys
from projectlib import ROOT, atomic_json, digest, read_json
from work2_research import INDEX, compare_thermo

DATA='Work2/research/data/'

READ_SCOPE={
'W2-N01':'NASA metadata: title, authors, abstract, original download links',
'W2-N02':'NASA metadata: title, authors, abstract, legacy language and example scope',
'W2-N03':'NASA metadata: report title and download identity',
'W2-N04':'PDF 9-11 / printed 1-3: summary, standard/reference states, NASA9 equations and assigned enthalpy; text extracted, pages visually checked; not all 295 pages read',
'W2-N05':'Part I chapter 2 printed p3: equivalence and constraints; prior local reading of sections 3.3/3.4/6.1 retained',
'W2-N07':'Part II front matter and index only; examples not newly reproduced',
'W2-C01':'README: scope, C++ application interface, pinned 3.1.0 version',
'W2-C02':'BSD-3-Clause text and retained-notice conditions',
'W2-C04':'MultiPhaseEquil.cpp lines 122-171: initialization, composition stepping, failure handling',
'W2-C05':'ThermoPhase.cpp lines 1167-1208: auto/element_potential fallback and state restoration',
'W2-C06':'Versioned equilibrate reference: constraint pairs and solver selector; HTML text inspected around method',
'W2-C07':'ChemEquil.cpp lines 301-337 and 608-672: TP/HP constraints and failure state restoration',
'W2-C08':'README lines 85-105: core/core-c Fortran+C build; not a C numerical core',
'W2-C09':'Apache-2.0 license header/version and scope; no adoption of solver code',
'W2-C10':'NOTICE: data paths and NASA TP / RP references',
'W2-P01':'Product page ZQ-3 and separately TQ-12A headings and values; read entire relevant sections',
'W2-P02':'Announcement dated 2025-12-03: flight configuration and limits, not engine thermodynamic card',
'W2-P03':'Manufacturer CZ-10B page dated 2026-07-10: propellants, vehicle-level approximate figures',
'W2-P04':'Group article 2026-07-15: stage1 130-ton-class and stage2 140-ton-class descriptions only',
'W2-P05':'Announcement 2026-08-19: recovery and reduced landing-engine count without exact subtype/count',
'W2-P06':'English product page TQ-12A section: Nozzle area ratio 20.5 and separate product fields; not a flight-batch card',
'W2-P07':'2025-10-20 first-phase announcement: static fire/loading rehearsal and planned later flight; not a new flight success',
'W2-X01':'arXiv title/authors/abstract: disconfirms the earlier generated chemical-equilibrium citation',
'W2-A01':'Official 2022-11-16 tutorial: ODML, first-order sensitivity prediction, acceptance and full-solve fallback; source author claims kept distinct',
'W2-A02':'2017 v1 original sections 2-4: GEM/LMA, Taylor, acceptance test, reactive-transport experiment setting; no reproduction',
'W2-A03':'Client Challenge HTML only; scientific full text unavailable',
'W2-A04':'arXiv metadata: title/authors, v1 2026-03-11 and v4 2026-08-17, abstract',
'W2-A06':'v4 original abstract, method, dataset/split and Limitations/Future Steps; binary synthetic LLE, not gas HP',
'W2-S01':'Versioned 7.2.1 introduction: C implementation and vector/matrix/backend separation',
'W2-S02':'Latest usage navigation only; version not pinned, not used for API conclusions',
'W2-S03':'Official project license page: BSD-3-Clause statement',
'W2-S04':'Versioned 7.2.1 Usage sections 7.4.2/7.4.3/7.4.4: callbacks, scaling, return flags, cumulative metrics',
'W2-S07':'Tagged v7.2.1 BSD-3-Clause full license text',
'W2-S08':'Tagged v7.2.1 kinsol.c header and solver creation/context outline; no build or complete source audit',
'W2-R01':'Official commit metadata before cutoff; f587235e692b7168faa272c8892a4c079a1f7dd9, 2026-02-02',
'W2-R02':'Pinned README: databases, AD and LGPL-2.1-or-later statement',
'W2-R03':'Pinned LGPL-2.1 header and preamble; not adopted as production dependency',
'W2-R04':'Pinned C++ API: state/specs, solve overloads, sensitivities, records/clusters',
}


def claim(cid,text,sids,locator,quote='',classification='verified_fact',limit=''):
    return {'id':cid,'classification':classification,'statement':text,'source_ids':sids,
            'locator':locator,'short_quote':quote,'limitation':limit,'verified_on':'2026-10-24'}


def observations():
    rows=[]
    def add(oid,obj,field,value,unit,source,quote,boundary,kind='verified_fact',reason=None):
        rows.append({'id':oid,'object':obj,'field':field,'value':value,'original_unit':unit,
                     'classification':kind,'source_ids':source,'short_quote':quote,'boundary':boundary,
                     'missing_reason':reason,'verified_on':'2026-10-24','use':'context_only_not_validated_solver_input'})
    add('P001','ZQ-3 Y1 flight / stage1','engine_configuration','9 x TQ-12A',None,['W2-P02'],'一级采用九台天鹊12A发动机并联','2025-12-03 flight configuration')
    add('P002','ZQ-3 Y1 flight / stage2','engine_configuration','1 x TQ-15A',None,['W2-P02'],'二级采用一台天鹊15A真空型发动机','2025-12-03 flight configuration')
    add('P003','ZQ-3 Y1 flight / vehicle','liftoff_thrust',7542,'kN',['W2-P02'],'起飞推力7542kN','Vehicle parallel propulsion; not one main chamber')
    add('P004','ZQ-3 product at retrieval','engine_configuration','9 x TQ-12B + 1 x TQ-15B',None,['W2-P01'],'一子级采用9台TQ-12B发动机，二子级配置1台TQ-15B真空发动机','Undated current product description; not Y1 or inferred Y2 fit')
    add('P005','TQ-12A product section','sea_level_thrust',84.6,'t (manufacturer thrust notation)',['W2-P01'],'海平面推力','Engine product field; interpretation as tf would be a separate derivation')
    add('P006','TQ-12A product section','sea_level_specific_impulse',293,'s',['W2-P01'],'海平面比冲','Product field; measured batch/uncertainty not stated')
    add('P007','TQ-12A product section','mixture_ratio',2.9,'dimensionless',['W2-P01'],'混合比','Page does not explicitly resolve main-chamber vs whole-engine definition')
    add('P008','CZ-10B first flight stage1','propellants','LOX/kerosene',None,['W2-P03'],'火箭芯一级采用液氧煤油推进剂','Fuel grade/composition/enthalpy not stated')
    add('P009','CZ-10B first flight stage2','propellants','LOX/methane',None,['W2-P03'],'芯二级采用液氧甲烷推进剂','Subtype/cycle not specified by this page')
    add('P010','CZ-10B first flight vehicle','approx_liftoff_thrust',890,'吨 (approximate thrust statement)',['W2-P03'],'全箭起飞推力约890吨','Vehicle total, approximate; not independent engine operating point')
    add('P011','CZ-10B first flight stage1 engine description','thrust_class',130,'吨级',['W2-P04'],'一子级130吨级泵后摆液氧煤油发动机','Class label only, not exact sea-level/vacuum performance')
    add('P012','CZ-10B first flight stage2 engine description','thrust_class',140,'吨级',['W2-P04'],'二子级140吨级液氧甲烷发动机','Class label only; exact subtype/operating state remains unknown')
    add('P013','TQ-12A English product section','reported_nozzle_area_ratio',20.5,'dimensionless',['W2-P06'],'Nozzle area ratio','Manufacturer product label; exact flight batch, operating-state identity and throat area not supplied')
    for obj,sids in [('ZQ-3 Y1 TQ-12A',['W2-P02','W2-P01']),('ZQ-3 Y1 TQ-15A',['W2-P02']),('ZQ-3 current TQ-12B/TQ-15B',['W2-P01']),('CZ-10B first-flight stage1',['W2-P03','W2-P04']),('CZ-10B first-flight stage2',['W2-P03','W2-P04'])]:
        for field,unit in [('main_chamber_pressure','Pa'),('main_chamber_oxidizer_fuel_ratio','dimensionless'),('fuel_inlet_temperature','K'),('oxidizer_inlet_temperature','K'),('nozzle_area_ratio','dimensionless'),('throat_area','m2')]:
            add(f'P{len(rows)+1:03}',obj,field,None,unit,sids,'','Same subtype/batch/condition required','unknown','Not disclosed in the inspected primary pages; not a claim of absence from all public literature')
    return rows


def expected_data(index,root=ROOT):
    claims=[
      claim('M001','NASA I将平衡常数与自由能最小化表述为两种等价的化学平衡形式；等价比较必须保持相同约束和物理模型。',['W2-N05'],'Part I chapter 2 printed p3','two equivalent formulations'),
      claim('M002','NASA9资料在cp/R中使用七项温度函数，焓/熵再有两个积分常数；不是七系数旧形式。',['W2-N04'],'Printed p2 equations 1-3','',limit='Use each species own fit ranges; database-wide bounds are not every-species guarantees'),
      claim('M003','NASA给定焓包含参考形成贡献和显焓；不能再重复加一次形成焓。',['W2-N04'],'Printed p2 Assigned Enthalpy Values equations 4-6','',limit='Exact inlet phase and reference basis still required'),
      claim('M004','Cantera固定源码的auto先试元素势，失败恢复初态后进入多相求解路径。',['W2-C05'],'ThermoPhase.cpp:1167-1208','restoreState(initial_state);',limit='Source reading only; no new Cantera run'),
      claim('M005','Cantera ChemEquil对HP使用质量比焓和压力为约束；并非单纯固定组分setState_HP。',['W2-C07'],'ChemEquil.cpp:301-330','case HP:',limit='Source/API scope only'),
      claim('C001','CEA core-c预设构建Fortran+C，不能据名称称核心纯C。',['W2-C08'],'README Minimal Builds','Fortran + C (no Python bindings):'),
      claim('C002','KINSOL提供问题残差/Jacobian回调，并将数值求解与物理方程分离。',['W2-S04'],'Usage 7.4.4.1-2','typedef int (*KINSysFn)',limit='General nonlinear solver; not thermodynamic database or complete equilibrium model'),
      claim('C003','KINSOL文档明确步长停止可能是无效解附近停滞，不能等同残差收敛。',['W2-S04'],'Usage KINSol return flag KIN_STEP_LT_STPTOL','stalled',limit='Project must independently evaluate physical residuals'),
      claim('C004','KINSOL有累计函数评估、非线性迭代和回溯次数等诊断接口。',['W2-S04'],'Usage optional output functions','KINGetNumFuncEvals',limit='Different counting conventions must be aligned before comparing engines'),
      claim('C005','SUNDIALS v7.2.1发行许可为BSD三条款。',['W2-S07'],'LICENSE first line and redistribution conditions','BSD 3-Clause License',limit='No SUNDIALS code adopted or linked this batch'),
      claim('C006','Reaktoro固定API为C++类和方法；README为LGPL-2.1-or-later声明。',['W2-R02','W2-R04'],'README License and SmartEquilibriumSolver declaration','',limit='Language port does not erase license obligations; candidate reference only'),
      claim('A001','Reaktoro ODML以灵敏度一阶预测，预测未达接受要求时完整求解并补充知识记录。',['W2-A01','W2-A02'],'Tutorial ODML; paper sections 3.1-3.3','first-order Taylor approximation',limit='Existing prior art; not a neural-network requirement or demonstrated gas-HP gain'),
      claim('A002','2017原始论文展示的是60°C、100bar流体/矿物反应输运例，不是高温火箭HP验证。',['W2-A02'],'Section 4 reactive-transport setup','',limit='Its reported speedup cannot be imported as a project forecast'),
      claim('A003','DISCOMAX v4评估二元液液平衡的合成数据；作者明确合成判据不证明真实混合物必然出现实验LLE。',['W2-A06'],'Dataset section','The published dataset should therefore be interpreted as a synthetic benchmark.',limit='Conceptual cross-domain reference, not gas combustion data'),
      claim('A004','DISCOMAX论文用按二元体系隔离的80/10/10划分，并披露只含两相正样本和多组分组合成本限制。',['W2-A06'],'Generalizing to new systems; Limitations & Future Steps','system-wise split',limit='Does not demonstrate reliable single-phase classification or general CHO HP solver'),
      claim('X001','旧无轨迹返回的arXiv:1805.07762实际为Selfishness need not be bad: a general proof，化学平衡论文归属错误。',['W2-X01'],'arXiv title/authors/abstract','Selfishness need not be bad: a general proof',limit='Reject earlier generated title/quote/performance; retained as negative provenance evidence'),
      claim('P001','蓝箭英文TQ-12A产品栏直接列Nozzle area ratio 20.5，不能据此补TQ-12B/15A或遥一具体飞行工况。',['W2-P06'],'TQ-12A product section','Nozzle area ratio',limit='Reported product parameter only, not independently measured or a complete chamber input set'),
      claim('D001','课程与固定CEA两完整物性文件不同，选定10种中性气体的比较字段一致，不能视作独立物性验证。',['W2-L01','W2-L02'],'thermo-comparison.json; tools/work2_research.py compare-thermo','',classification='derived',limit='Only selected records; transport, condensed species and full database not compared'),
      claim('H001','灵敏度预测+真实残差校正/回退可作为C引擎候选，收益必须相对热启动等简单基线证明。',['W2-A01','W2-A02','W2-S04'],'Proposed adaptation, not an implemented or validated result','',classification='hypothesis',limit='Near-singular derivatives, phase changes, memory search and HP outer tolerance remain research questions'),
    ]
    catalog=[
      {'id':'SW01','name':'NASA CEA','version':'v3.3.4','commit':'4c5c612efa2002a94e3a5a1f33b1674d55c65340','core_language':'Fortran','c_interface_is_c_core':False,'license':'Apache-2.0','source_ids':['W2-C08','W2-C09','W2-C10'],'role':'Pinned thermodynamic reference; not production solver dependency','tested_here':False},
      {'id':'SW02','name':'Cantera','version':'3.1.0','commit':'6e0027548cf295bd478b8acfe34816f2db6dd58b','core_language':'C++','c_interface_is_c_core':False,'license':'BSD-3-Clause','source_ids':['W2-C01','W2-C02','W2-C05','W2-C07'],'role':'Reference implementations, solver/state-recovery comparison','tested_here':False},
      {'id':'SW03','name':'SUNDIALS KINSOL','version':'7.2.1','commit':None,'version_pin':'official v7.2.1 tag, byte hashes retained; API commit lookup failed','core_language':'C','c_interface_is_c_core':True,'license':'BSD-3-Clause','source_ids':['W2-S01','W2-S04','W2-S07','W2-S08'],'role':'Algorithm/backend/interface reference; linking only after small-system cost comparison','tested_here':False},
      {'id':'SW04','name':'Reaktoro','version':None,'commit':'f587235e692b7168faa272c8892a4c079a1f7dd9','commit_date':'2026-02-02','core_language':'C++','c_interface_is_c_core':False,'license':'LGPL-2.1-or-later (README); LGPL2.1 text retained','source_ids':['W2-R01','W2-R02','W2-R03','W2-R04','W2-A01'],'role':'Prior art and ODML reference; not a promised whole-library C port','tested_here':False},
    ]
    available=[s for s in index['sources'] if s['available']]
    coverage={'schema_version':1,'as_of':'2026-10-24','scope':'First-round evidence collection; not exhaustive systematic review or new numerical benchmark',
      'source_records':len(index['sources']),'available_records':len(available),'failed_records':len(index['sources'])-len(available),
      'usable_read_records':sum(s.get('content_usable',True) and s.get('read_scope')!='downloaded_only' for s in available),
      'claim_count':len(claims),'parameter_observations':len(observations()),'unknown_parameters':sum(o['classification']=='unknown' for o in observations()),
      'new_solver_runs':0,'new_training_samples':0,'new_gpu_runs':0,
      'tracks':[
        {'id':'M','done':'Official NASA report, pinned CEA/Cantera sources and selected data comparison','gap':'New WBASE solver audit and full species/phase reference coverage'},
        {'id':'V','done':'Benchmark hierarchy, source/data identity and planned dataset contract','gap':'Threshold justification and fresh numerical runs belong to WBASE/WREF'},
        {'id':'C','done':'Four libraries with pinned versions/source language/license and interface comparison','gap':'No new library compiled or timing claim; thread safety/reentrancy not established'},
        {'id':'A','done':'ODML original, official tutorial and 2026 differentiable LLE paper read with limitations','gap':'2020 Springer full text blocked; no exhaustive frontier ranking or gas-HP speed benefit'},
        {'id':'P','done':'Seven primary manufacturer/group pages read; English TQ-12A product area-ratio observation separated from flight inputs','gap':'Same-batch Pc/main O-F/inlet/throat area still absent in inspected pages; product geometry not transplanted into flight cards'},
      ],'search_limit':'At least one structured trace returned; other requests lacked traces. Tool metadata is not independent original-source verification.'}
    return {DATA+'claims.json':{'schema_version':1,'claims':claims},DATA+'software-catalog.json':{'schema_version':1,'software':catalog},
            DATA+'parameter-observations.json':{'schema_version':1,'scope':'Course context observations, not a performance card','observations':observations()},
            DATA+'coverage.json':coverage,DATA+'thermo-comparison.json':compare_thermo(root)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    index=read_json(ROOT/INDEX)
    if not args.check:
        for row in index['sources']:
            if row['id'] in READ_SCOPE: row['read_scope']=READ_SCOPE[row['id']]
            if row['id']=='W2-A03': row['content_usable']=False
        atomic_json(ROOT/INDEX,index)
    issues=[]
    for relative,value in expected_data(index).items():
        if args.check:
            if not (ROOT/relative).is_file() or read_json(ROOT/relative)!=value: issues.append(relative)
        else: atomic_json(ROOT/relative,value)
    print(json.dumps({'status':'FAIL' if issues else 'PASS','generated_data_drift':issues},ensure_ascii=False))
    return int(bool(issues))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.exit(main())
