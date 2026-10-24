"""Curated vehicle evidence v1; observations are context, never solver inputs."""
from __future__ import annotations
import argparse
import json
import re
import sys
from projectlib import ROOT, atomic_json, lock, read_json
from work2_research import INDEX, PageText

OUT='Work2/research/data/'
SELECTED=[f'W2-P{i:02}' for i in range(1,8)]+[f'W2-V{i:02}' for i in range(1,11)]+[f'W2-VL{i:02}' for i in range(1,13)]
READ_SCOPE={
 'W2-V01':'Milestones 2024-2025 and company context; year-level VTVL entry, not precise event date or technical proof',
 'W2-V02':'Technology-route list and facilities; corporate capability statements, not flight-subtype specification',
 'W2-V03':'Downloads navigation/template only; dynamic item list absent from saved HTML, no scientific document obtained',
 'W2-V04':'2026-07-15 article body: sea recovery organisation, four hooks and flexible net, post-recovery inspection planned',
 'W2-V05':'2026-07-15 interview body: verification priorities, preflight review and limits of ground tests for reuse knowledge',
 'W2-V06':'DOI linking-hub redirect HTML only; no publisher abstract or full text obtained',
 'W2-V08':'2024-01-19 original body: VTVL-1 geometry, trial conditions, modified TQ-12 and stated capability; not orbital ZQ-3 configuration',
 'W2-V09':'2024-09-11 original body: 10002m/200.7s trial, restart, reuse of January test vehicle; future orbital design targets separated',
 'W2-V10':'2025-04-15 original body: hundredth engine, TQ-12B 550s ground test and Huzhou cumulative test statement; not Y1 fit',
 'W2-VL01':'Archived CALT first-flight body paragraphs on event, stage propellants, inherited stage1, verified technologies and future reuse plan',
 'W2-VL02':'Archived CCTV interview text attributed to Chen Muye: 7 engines, 5/2 layout, restart sequence, 200km and 900km capacities; hosted retransmission',
 'W2-VL03':'Archived 2022-09-27 TQ-15A assembly original: ZQ-2 second-batch application, GG components, throttle, gimbal, seal and turbine exhaust; not Y1 specification',
 'W2-VL04':'Crossref JSON title, DOI, authors, journal/volume/pages and print date only; no article abstract/full-text reading',
 'W2-VL05':'CMSE page title, 2022 issue context, 2023-02-21 page date, authors and abstract only; not journal full text',
 'W2-VL06':'Archived 2025-06-20 nine-engine original body: TQ-12A, stated flight-like configuration, 7542kN and 45s; ground test only',
 'W2-VL07':'Archived 2023-12-10 manufacturer-hosted New Beijing News report: early release/B-family design parameters; historical reported targets',
 'W2-VL08':'Archived 2024-03-07 A-family delivery original: ZQ-2 batch02, 60-100%, sample/cumulative tests and 2460s; not orbital ZQ-3 life evidence',
 'W2-VL09':'Archived 2025-05-14 CASC article: 2025-04-26 first full-engine test, 140-ton open-cycle product and development stages; no flight-subtype bridge',
 'W2-VL10':'Archived Xinhua report on CCTV, 2025-05-14: confirms reported 2025-04-26 ground test, no product-to-flight serial identity',
 'W2-VL11':'Archived 2024-12-13 article on CZ-12: four YF-100K and staged-combustion family context; explicitly not CZ-10B fit',
 'W2-VL12':'Archived CCTV item retransmitted by Guangming, 2025-08-16: 2025-08-15 CZ-10-series seven-engine captive firing; not CZ-10B first flight',
}


def observations():
    rows=[]
    def add(oid,vehicle,dim,obj,field,value,unit,sid,locator,quote,scope,kind='reported_fact',event=None):
        row={'id':oid,'vehicle':vehicle,'dimension':dim,'object':obj,'field':field,'value':value,
             'original_unit':unit,'classification':kind,'source_ids':[sid], 'locator':locator,
             'short_quote':quote,'scope':scope,'use':'context_only_not_validated_solver_input','reviewed_on':'2026-10-24'}
        if event: row['event_on']=event
        rows.append(row)
    # Short exact excerpts locate the observation; numeric context is kept in scope.
    z=lambda *a,**kw:add(a[0],'ZQ-3',*a[1:],**kw)
    z('Z001','D01','early release','public_release','ZQ-3',None,'W2-VL07','2023-12-10 body, Dec9 context','正式发布了下一代可重复使用液氧甲烷运载火箭','Manufacturer-hosted New Beijing News report; release date inferred from explicit same-day context',event='2023-12-09')
    z('Z002','D02','2023 early design','length',76.6,'m','W2-VL07','body, founder introduction','全箭总长76.6米','Early announced design, not 2025 Y1 measured geometry',kind='design_target')
    z('Z003','D02','2023 early design','liftoff_mass',660,'t','W2-VL07','body, founder introduction','起飞质量约660吨','Approximate early design',kind='design_target')
    z('Z004','D03','2023 early design','engine_configuration','9 x TQ-12B + 1 x TQ-15B',None,'W2-VL07','body, founder introduction','一子级配置9台','Early B-family announced configuration, not Y1 fit',kind='design_target')
    z('Z005','D05','2023 TQ-12B design','sea_level_thrust',1000,'kN','W2-VL07','body, engine introduction','海平面推力1000千牛','Reported design field, no same-batch chamber card',kind='design_target')
    z('Z006','D05','2023 TQ-15B design','vacuum_thrust',1183,'kN','W2-VL07','body, engine introduction','真空推力1183千牛','Reported design field, not 2025 Y1 TQ-15A',kind='design_target')
    z('Z007','D05','2023 TQ-15B design','vacuum_exhaust_velocity_label',3500,'m/s','W2-VL07','body, engine introduction','真空比冲为3500米/秒','Original Isp notation is velocity; no silent treatment as seconds',kind='design_target')
    z('Z008','D09','VTVL-1 January flight','flight_height',350,'m','W2-V08','opening paragraph','飞行高度约350m','Approximate trial report; one-engine suborbital platform',event='2024-01-19')
    z('Z009','D02','VTVL-1 January flight','diameter',3.35,'m','W2-V08','platform description','箭体直径3.35米','Trial vehicle, not 4.5m orbital vehicle')
    z('Z010','D02','VTVL-1 January flight','length',18.3,'m','W2-V08','platform description','长度18.3米','Trial geometry')
    z('Z011','D07','VTVL-1 January modified TQ-12','throttle_range','45%-110%',None,'W2-V08','platform description','45%~110%','Stated capability of this modified trial engine, not universal A/B specification')
    z('Z012','D09','VTVL-1 September flight','maximum_height',10002,'m','W2-V09','trial trajectory paragraph','高度10002m','Trial report; flight condition is not chamber thermodynamic data',event='2024-09-11')
    z('Z013','D09','VTVL-1 September flight','flight_time',200.7,'s','W2-V09','trial trajectory paragraph','空中飞行总时间为200.7s','Whole test-vehicle flight duration')
    z('Z014','D08','VTVL-1 September flight','reused_test_vehicle',True,None,'W2-V09','reported validation item3','沿用原执行百米级飞行试验任务的试验箭','Actual reported trial-vehicle reuse; does not establish orbital-stage 20-flight life')
    z('Z015','D07','VTVL-1 September modified TQ-12','throttle_range','45%-111%',None,'W2-V09','platform description','45%~111%','Keep separate from January range; nominal reference/technical changes not resolved')
    z('Z016','D09','TQ-12B ground product','ground_test_duration',550,'s','W2-V10','latest TQ-12B paragraph','已完成550秒地面试验','Ground-test report, not evidence of Y1 B-engine fit',event='2025-04-15')
    z('Z017','D03','ZQ-3 June stage1 ground test','engines','9 x TQ-12A',None,'W2-VL06','trial engine paragraph','9机并联总推力达7542kN','Body separately identifies TQ-12A; ground test declared flight-like',event='2025-06-20')
    z('Z018','D05','ZQ-3 June stage1 ground test','total_thrust',7542,'kN','W2-VL06','trial engine paragraph','9机并联总推力达7542kN','Nine-engine aggregate; not one main chamber')
    z('Z019','D09','ZQ-3 June stage1 ground test','stable_work_duration',45,'s','W2-VL06','trial engine paragraph','稳定工作45秒','Stated stable work interval, not total service life')
    z('Z020','D02','ZQ-3 Y1 flight','length',66.1,'m','W2-P02','vehicle description','全箭长66.1m','Specific Y1 announcement',event='2025-12-03')
    z('Z021','D02','ZQ-3 Y1 flight','liftoff_mass',560,'t','W2-P02','vehicle description','起飞质量约560t','Approximate flight-announcement value, separate from static-test approx570t')
    z('Z022','D03','ZQ-3 Y1 flight','engine_configuration','9 x TQ-12A + 1 x TQ-15A',None,'W2-P02','vehicle description','二级采用一台天鹊15A真空型发动机','Stage1 nine TQ-12A in same paragraph')
    z('Z023','D08','ZQ-3 Y1 flight','outcome','orbit reached; stage1 soft landing failed',None,'W2-P02','flight outcome paragraph','回收试验失败','No inferred failure mechanism beyond source; cause under investigation there')
    z('Z024','D08','ZQ-3 Y2 flight','outcome','orbit reached; stage1 leg landing succeeded',None,'W2-P05','opening and recovery paragraphs','成功软着陆于甘肃省民勤县朱雀三号着陆场坪','Subtype/count after landing-engine reduction not specified',event='2026-08-19')
    z('Z025','D02','undated ZQ-3 product','length',76.6,'m','W2-P01','ZQ-3 product fields','76.6m','Undated product, no inference of exact Y2 configuration')
    z('Z026','D03','undated ZQ-3 product','engine_configuration','9 x TQ-12B + 1 x TQ-15B',None,'W2-P01','ZQ-3 heading','一子级采用9台TQ-12B发动机','Current product description, distinct from Y1 and unspecified Y2')
    for oid,field,value,quote in [('Z027','expendable_capacity',21.3,'一次性任务：21.3t'),('Z028','downrange_recovery_capacity',18.3,'航区回收任务：18.3t'),('Z029','return_to_launch_capacity',12.5,'返场回收任务：12.5t')]:
        z(oid,'D02','undated ZQ-3 product',field,value,'t','W2-P01','LEO @450km product fields',quote,'Product capability at 450km LEO; actual delivered payload not established',kind='design_target')
    z('Z030','D08','ZQ-3 orbital stage design','reuse_target',20,'flights','W2-P02','vehicle description','设计重复使用次数不低于20次','At least20 is a design target, not completed orbital flights',kind='design_target')
    for oid,field,value,unit,quote in [('Z031','sea_level_thrust',84.6,'t (thrust label)','84.6t'),('Z032','sea_level_specific_impulse',293,'s','293s'),('Z033','reported_mixture_ratio',2.9,None,'2.9'),('Z034','reported_area_ratio',20.5,None,'20.5')]:
        z(oid,'D05','TQ-12A product section',field,value,unit,'W2-P06','TQ-12A labelled product fields',quote,'Product statement; same-batch chamber/whole-engine boundary and uncertainty absent')
    z('Z035','D05','2022 TQ-15A / ZQ-2 batch02 design','vacuum_thrust',836,'kN','W2-VL03','engine specification paragraph','真空推力达836kN','Historical ZQ-2 application, not a Y1 calibration point')
    z('Z036','D07','2022 TQ-15A / ZQ-2 batch02 design','throttle_range','60%-110%',None,'W2-VL03','engine specification paragraph','60%~110%','Original historical statement')
    z('Z037','D07','2024 TQ-15A / ZQ-2 batch02 delivery','throttle_range','60%-100%',None,'W2-VL08','batch02 delivery paragraph','60%~100%','Separate delivery statement; discrepancy not silently reconciled')
    z('Z038','D04','2022 TQ-15A architecture','turbine_exhaust_route','nozzle extension',None,'W2-VL03','listed improvement item','涡轮排气引入推力室喷管延伸段','Does not mean turbine gas returned to the main chamber')
    z('Z039','D07','A-family ground programme','reported_longest_single_unit_test_time',2460,'s','W2-VL08','ground verification paragraph','单台最长试车时间2460秒','Whether single firing or cumulative per-unit is not resolved; do not call orbital lifetime')
    z('Z040','D09','series ground tests, January2024 report','reported_cumulative_time_lower_bound',100000,'s','W2-V08','validation item2','累计时间已超10万秒','Reported series-wide scope; denominator differs or unresolved against later Huzhou figure')
    z('Z041','D09','Huzhou large-thrust tests, April2025 report','reported_cumulative_time',68000,'s','W2-V10','latest TQ-12B paragraph','累计6.8万秒','Huzhou large-thrust wording; do not force monotonic comparison with different scope')
    z('Z042','D09','ZQ-3 Y1 preflight phase1','event','loading rehearsal and static firing',None,'W2-P07','opening paragraph','2025年10月18日-10月20日','Ground campaign interval; not orbital flight',event='2025-10-18/2025-10-20')
    z('Z043','D06','2022 TQ-15A architecture','turbine_layout','two-stage turbine',None,'W2-VL03','listed improvement item','涡轮泵改为双级涡轮','Historical architecture statement; no pump map or Y1 component identity')
    z('Z044','D06','2022 TQ-15A architecture','pump_seal','end-face seal',None,'W2-VL03','listed improvement item','涡轮泵应用端面密封技术','No leakage/thermal-life measurements supplied')
    z('Z045','D06','ZQ-3 Y1 structure','tank_material','high-strength stainless steel',None,'W2-P02','reported breakthrough item3','高强度不锈钢','Manufacturing claim, not wall thickness/constitutive data or engine cooling law')
    c=lambda *a,**kw:add(a[0],'CZ-10B',*a[1:],**kw)
    c('C001','D09','CZ-10B first flight','launch_time','2026-07-10 12:15 Asia/Shanghai',None,'W2-VL01','opening paragraph','2026年7月10日12时15分','Orbit and stage1 sea capture reported',event='2026-07-10')
    for oid,field,value,unit,quote in [('C002','length_approx',63,'m','全箭长度约63米'),('C004','diameter',5,'m','5米直径两级串联构型'),('C005','liftoff_mass_approx',760,'t','起飞重量约760吨'),('C006','liftoff_thrust_approx',890,'吨 (thrust label)','起飞推力约890吨')]:
        c(oid,'D02','CZ-10B first flight',field,value,unit,'W2-P03','vehicle paragraph',quote,'Vehicle aggregate/approximate statement; not individual engine input')
    c('C003','D02','CZ-10B first-flight interview','length',63.6,'m','W2-VL02','reporter introduction','全箭长度是63.6米','Interview precision and future70m extension separate from approximate product figure')
    c('C007','D02','CZ-10B recovery configuration','payload_capacity_200km',16,'t','W2-VL02','Chen Muye capacity statement','近地200公里轨道的运载能力为16吨','Reported capability, not actual payload mass')
    c('C008','D02','CZ-10B recovery configuration','payload_capacity_900km_50deg',11,'t','W2-VL02','Chen Muye capacity statement','900公里、50度倾角轨道的运载能力为11吨','Keep altitude/inclination and recovery condition')
    c('C009','D03','CZ-10B first flight','stage_propellants','stage1 LOX/kerosene; stage2 LOX/methane',None,'W2-P03','vehicle paragraph','芯二级采用液氧甲烷推进剂','Kerosene grade and stage2 exact engine subtype not supplied')
    c('C010','D03','CZ-10B stage1 interview','engine_count_family','7 x YF-100 family',None,'W2-VL02','Chen Muye engine paragraph','7台液发100系列发动机','Family disclosure; suffix not supplied')
    c('C011','D07','CZ-10B stage1 interview','gimbal_layout','5 gimballed; 2 fixed',None,'W2-VL02','Chen Muye engine paragraph','有5台是可以摇摆的，有2台是固定的','Original interview, no inferred individual ratings')
    c('C012','D07','CZ-10B stage1 interview','restart_capability','5 engines; 2 in deceleration and 3 in final landing description',None,'W2-VL02','Chen Muye engine paragraph','这5台是可以二次启动的','Keep reported sequence; no telemetry-derived per-engine history')
    c('C013','D04','CZ-10B first-flight stage1 description','engine_class','130-ton pump-after-swing LOX/kerosene',None,'W2-P04','sixth-academy paragraph','一子级130吨级泵后摆液氧煤油发动机','Class description, not exact suffix or performance card')
    c('C014','D04','CZ-10B first-flight stage2 description','engine_class','140-ton LOX/methane',None,'W2-P04','stage2 paragraph','二子级140吨级液氧甲烷发动机','Flight context supported; exact model/count and ground-product identity remain unresolved')
    c('C015','D04','130-ton pump-after-swing family paper','cycle','high-pressure staged combustion',None,'W2-VL05','paper title and abstract','高压补燃液氧煤油发动机','Abstract/family context only, not complete CZ-10B flight-state specification')
    c('C016','D04','140-ton ground product, May2025 article','cycle','open cycle',None,'W2-VL09','technology-products paragraph','最大推力的开式液氧甲烷发动机','Ground product; direct serial/subtype bridge to CZ-10B stage2 absent')
    c('C017','D09','140-ton ground product','first_whole_engine_test','successful',None,'W2-VL09','opening paragraph','2025年4月26日','Exact event date from body, publication2025-05-14',event='2025-04-26')
    c('C018','D08','CZ-10B first flight','stage1_recovery','sea-platform net capture succeeded',None,'W2-VL01','opening paragraph','通过网系捕获方式成功回收','One recovered stage, not repeated orbital service life')
    c('C019','D08','CZ-10B first-flight recovery','capture_hooks',4,'hooks','W2-V04','sea capture narrative','四个挂钩精准切入井字形柔性网','Published recovery narrative; no dynamics or hardware load data')
    c('C020','D08','CZ-10B future reuse','planned_reflight','before end of2026',None,'W2-VL01','future paragraph','预计将在今年年底前完成火箭一子级复用飞行','Plan in July article; no completion inferred at October cutoff',kind='design_target')
    c('C021','D09','CZ-10-series low-altitude demonstration','event','low-altitude demonstration and spacecraft max-Q escape test',None,'W2-V04','first retrospective paragraph','今年2月','Month-level retrospective, not exact date or CZ-10B first flight',event='2026-02')
    c('C022','D09','CZ-10-series test stage','event','seven-engine captive firing',None,'W2-VL12','opening and trial paragraphs','一子级试验产品七台发动机同时点火','Series ground test, not seven-flight-engine identity card',event='2025-08-15')
    c('C023','D01','CZ-12 historical engine article','engine_configuration','4 x YF-100K',None,'W2-VL11','engine introduction','4台YF-100K发动机','Explicit neighbouring-vehicle context; cannot substitute CZ-10B suffix')
    c('C024','D06','CZ-10B first-flight technology list','reported_validation','methane autogenous pressurisation',None,'W2-VL01','validated technologies paragraph','甲烷自生增压技术','Technology announcement, not measured inlet thermodynamic state')
    c('C025','D06','CZ-10B preflight structural review','reported_issue','load-path manufacturing concern identified and addressed',None,'W2-V05','preflight structural-test story','发动机与贮箱之间的一处传力结构','Engineering interview, no transferable stress/load or cooling data')
    c('C026','D09','130-ton family paper abstract','reported_whole_engine_test_time_lower_bound',10000,'s','W2-VL05','abstract','逾1万秒整机热试车考核','Family programme; no CZ-10B life or cooling model validated')
    for obj,vehicle,sids in [
        ('ZQ-3 Y1 TQ-12A','ZQ-3',['W2-P02','W2-P06']),('ZQ-3 Y1 TQ-15A','ZQ-3',['W2-P02','W2-VL03']),
        ('ZQ-3 Y2 fitted engine subtype/count','ZQ-3',['W2-P05']),('CZ-10B first-flight stage1','CZ-10B',['W2-P03','W2-VL02']),
        ('CZ-10B first-flight stage2','CZ-10B',['W2-P03','W2-P04'])]:
        for field,unit in [('main_chamber_pressure','Pa'),('main_chamber_oxidizer_fuel_ratio',None),('fuel_inlet_state',None),('oxidizer_inlet_state',None),('nozzle_area_ratio',None),('throat_area','m2')]:
            rows.append({'id':f'U{sum(r["classification"]=="unknown" for r in rows)+1:03}',
             'vehicle':vehicle,'dimension':'D05','object':obj,'field':field,'value':None,'original_unit':unit,
             'classification':'unknown','source_ids':sids,'locator':'Inspected material for the same subtype/batch',
             'short_quote':'','scope':'Not established by this inspected corpus; no claim of absence from all public literature',
             'use':'missing_input_not_zero_or_cross_batch_default','reviewed_on':'2026-10-24'})
    return rows


def expected_data(index,root=ROOT):
    rows=observations();sources={s['id']:s for s in index['sources']}
    selected=[sources[sid] for sid in SELECTED if sid in sources]
    conflicts=[
      {'id':'K01','evidence_ids':['Z002','Z020','Z025'],'issue':'76.6m early/current product vs66.1m Y1','resolution':'Keep design/product and flight versions separate; Y2 geometry not inferred'},
      {'id':'K02','evidence_ids':['Z036','Z037'],'issue':'TQ-15A60-110% vs60-100% in different years','resolution':'Technical reference/condition unresolved; do not merge or assign to Y1'},
      {'id':'K03','evidence_ids':['Z040','Z041'],'issue':'Series>100000s vs later Huzhou68000s','resolution':'Denominators differ or remain unresolved; no monotonic cumulative-time claim'},
      {'id':'K04','evidence_ids':['C002','C003','C006','C010'],'issue':'Approx63m vs63.6m; approx890-ton vehicle vs interview approx900-ton aggregate','resolution':'Retain original precision and context; no averaging or precise engine division'},
      {'id':'K05','evidence_ids':['C014','C016','C017'],'issue':'Flight-stage140-ton description and earlier open-cycle ground product lack exact identity bridge','resolution':'Open-cycle product evidence remains product-specific; flight cycle/subtype not filled'},
      {'id':'K06','evidence_ids':['Z011','Z015'],'issue':'Trial engine45-110% vs45-111% descriptions','resolution':'Keep trial dates/reference conditions separate; no undocumented explanation'},
    ]
    dimensions=['D01','D02','D03','D04','D05','D06','D07','D08','D09','D10']
    gaps={
      'D01':'Exact future/flight fitted-subtype bridges still incomplete; related family is not a fit list',
      'D02':'Product capability is not measured delivered payload; recovery/orbit/input conditions differ',
      'D03':'Coverage is for selected published configurations, not an exhaustive configuration history',
      'D04':'Direct flight-subtype and full-cycle boundary evidence still incomplete',
      'D05':'Same-batch chamber/inlet/geometry and measurement uncertainty remain missing',
      'D06':'Cooling passages, wall heat transfer, pump maps, injector losses and material-life data not obtained',
      'D07':'Per-flight throttle/starting history and acceptance uncertainty not publicly established here',
      'D08':'Trial reuse, first recovery, orbital reflight and design lifetime must remain separate',
      'D09':'Selected milestones only; no complete mission/serial/test-event register verified',
      'D10':'Full technical-paper reading and broader bibliographic coverage remain incomplete; metadata/abstract not full text',
    }
    coverage=[]
    for vehicle in ['ZQ-3','CZ-10B']:
        for dim in dimensions:
            refs=[r['id'] for r in rows if r['vehicle']==vehicle and r['dimension']==dim and r['classification']!='unknown']
            if dim=='D10': refs=['B01'] if vehicle=='ZQ-3' else ['B02']
            coverage.append({'vehicle':vehicle,'dimension':dim,'status':'documented_subset' if refs else 'gap',
                             'evidence_ids':refs,'remaining_gap':gaps[dim]})
    message=read_json(root/sources['W2-VL04']['path'])['message'] if 'W2-VL04' in sources else {}
    bibliography=[{'id':'B01','source_ids':['W2-VL04'],'access':'metadata_only',
      'title':message.get('title',[''])[0],'doi':message.get('DOI'),'authors':message.get('author',[]),
      'journal':message.get('container-title',[]),'volume':message.get('volume'),'pages':message.get('page'),
      'published_print':message.get('published-print'),'limitation':'No publisher abstract/full text obtained; title alone does not identify a flight engine'},
      {'id':'B02','source_ids':['W2-VL05'],'access':'abstract_only','title':'130吨级泵后摆高压补燃液氧煤油发动机关键技术研究',
       'authors':['李斌','刘站国','吕发正','高乐乐','张森'],'issue_context':'载人航天2022年第4期; web publication2023-02-21',
       'limitation':'Family abstract only; full paper/DOI and precise flight subtype not established here'}]
    payload={'schema_version':1,'as_of':'2026-10-24','scope':'Selected public evidence v1, not exhaustive or validated engine inputs',
      'selected_source_ids':SELECTED,'observations':rows,'events':[{'observation_id':r['id'],'vehicle':r['vehicle'],'event_on':r['event_on']} for r in rows if 'event_on' in r],
      'conflicts':conflicts,'bibliography':bibliography,
      'unsupported_leads':[{'claim':'CZ-10B stage2 fits one YF-219','status':'not_supported_by_inspected_primary_sources',
       'process_record':'Work2/research/search/20261024_w2_cz10b_depth_a.md',
       'reason':'Generated narrative names the model/count, but its checked CALT/CASC/interview originals do not; retained only as unverified lead, not disproved'}]}
    cover={'schema_version':1,'as_of':'2026-10-24','scope':'20 questions examined; documented_subset does not mean complete evidence',
      'selected_source_records':len(selected),'available_records':sum(s['available'] for s in selected),
      'content_read_records':sum(s['available'] and s.get('content_usable',True) and s.get('read_scope')!='downloaded_only' for s in selected),
      'new_http_attempts':10,'historical_originals_reused':12,'prior_Work2_records_reused':7,
      'observation_count':len(rows),'unknown_observations':sum(r['classification']=='unknown' for r in rows),
      'event_count':len(payload['events']),'conflict_count':len(conflicts),'new_solver_runs':0,
      'coverage':coverage,'search_records':['20261024_w2_zq3_depth_a','20261024_w2_cz10b_depth_a','20261024_w2_zq3_sources_b'],
      'continuation':'Prioritise original papers and same-batch inputs that change C model applicability; keep WBASE independent'}
    return {OUT+'vehicle-evidence-v1.json':payload,OUT+'vehicle-coverage-v1.json':cover}


def verify(root=ROOT):
    path=root/(OUT+'vehicle-evidence-v1.json')
    if not path.is_file(): return []
    issues=[];index=read_json(root/INDEX);sources={s['id']:s for s in index['sources']}
    data=read_json(path);seen=set()
    for row in data['observations']:
        if row['id'] in seen: issues.append('Duplicate vehicle observation '+row['id'])
        seen.add(row['id'])
        if row['classification']=='unknown' and row['value'] is not None: issues.append('Unknown vehicle parameter contains a value: '+row['id'])
        for sid in row['source_ids']:
            source=sources.get(sid)
            if source is None: issues.append('Unknown vehicle source '+sid);continue
            if not source['available'] or not source.get('content_usable',True) or source.get('read_scope')=='downloaded_only':
                issues.append('Unread/unusable vehicle source '+sid)
            if row['short_quote'] and source['available']:
                body=(root/source['path']).read_text(encoding='utf-8')
                reader=PageText();reader.feed(body)
                if re.sub(r'\s+','',row['short_quote']) not in re.sub(r'\s+','',reader.text()):
                    issues.append('Vehicle excerpt not found: '+row['id']+'/'+sid)
    for relative,value in expected_data(index,root).items():
        if not (root/relative).is_file() or read_json(root/relative)!=value: issues.append('Vehicle curated data drift: '+relative)
    return issues


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if not args.check:
        with lock(ROOT,'research-sources'):
            index=read_json(ROOT/INDEX)
            for row in index['sources']:
                if row['id'] in READ_SCOPE: row['read_scope']=READ_SCOPE[row['id']]
                if row['id'] in {'W2-V03','W2-V06'}: row['content_usable']=False
            atomic_json(ROOT/INDEX,index)
        for relative,value in expected_data(index).items(): atomic_json(ROOT/relative,value)
    issues=verify();print(json.dumps({'status':'FAIL' if issues else 'PASS','issues':issues},ensure_ascii=False))
    return int(bool(issues))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.exit(main())
