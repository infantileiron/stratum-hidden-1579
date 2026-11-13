import csv,hashlib,io,json
from src.constants.domain import MAX_CATEGORIES
from src.models.entities import RunComparison
from src.config.settings import ARTIFACT_DIR
from src.utils import repository as repo
from src.utils.identity import new_id,now
def safe_cell(v):return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v
def list_comparisons():
 out=[]
 for c in repo.all_rows('comparisons'):
  summary={k:v for k,v in c['result'].items() if k!='rows'}
  out.append({**c,'result':summary})
 return out
def _states(run,label):
 states=run['result']['model']['config']['states']
 if not states:raise ValueError(f'{label}结果缺少模型状态快照')
 return states
def validate_mapping(mapping,states_a,states_b):
 cats=[str(c).strip() for c in mapping['categories']]
 if not 1<=len(cats)<=MAX_CATEGORIES:raise ValueError(f'共同类别需1—{MAX_CATEGORIES}个')
 if any(not c or len(c)>30 for c in cats):raise ValueError('共同类别名1—30字')
 if len(set(cats))!=len(cats):raise ValueError('共同类别名称需唯一')
 def side(entries,states,label):
  ids=[s['id'] for s in states];seen={}
  for e in entries:
   state,category=e['state'],str(e['category']).strip()
   if state in seen:raise ValueError(f'{label}状态{state}重复归类，拒绝比较')
   if state not in ids:raise ValueError(f'{label}状态{state}不在其模型快照中，拒绝比较')
   if category not in cats:raise ValueError(f'{label}状态{state}归入未声明的类别{category}，拒绝比较')
   seen[state]=category
  missing=[s for s in ids if s not in seen]
  if missing:raise ValueError(f'{label}状态{missing}未归类，映射有遗漏，拒绝比较')
  return seen
 map_a=side(mapping['run_a'],states_a,'运行A');map_b=side(mapping['run_b'],states_b,'运行B')
 return {'categories':cats,'run_a':[{'state':s['id'],'category':map_a[s['id']]} for s in states_a],'run_b':[{'state':s['id'],'category':map_b[s['id']]} for s in states_b]}
def aligned_rows(run_a,run_b):
 ra,rb=run_a['result'],run_b['result']
 if ra['borehole']!=rb['borehole']:raise ValueError(f'两次运行孔号不符：{ra["borehole"]}与{rb["borehole"]}，拒绝比较')
 rows_a,rows_b=ra['rows'],rb['rows']
 if len(rows_a)!=len(rows_b):raise ValueError(f'两次运行孔段点数不符：{len(rows_a)}与{len(rows_b)}，拒绝比较')
 for a,b in zip(rows_a,rows_b):
  if a['depth_m']!=b['depth_m']:raise ValueError(f'深度不符：{a["depth_m"]}与{b["depth_m"]}，拒绝比较')
  if a['value']!=b['value']:raise ValueError(f'深度{a["depth_m"]}m读数不符：{a["value"]}与{b["value"]}，拒绝比较')
 return rows_a,rows_b
def _aggregate(posterior,state_ids,state_to_cat,index):
 out=[0.]*len(index)
 for p,sid in zip(posterior,state_ids):out[index[state_to_cat[sid]]]+=p
 return out
def _segments(rows):
 segments=[];i=0
 while i<len(rows):
  if rows[i]['agree']:i+=1;continue
  j=i
  while j+1<len(rows) and not rows[j+1]['agree']:j+=1
  part=rows[i:j+1]
  segments.append({'depth_start':part[0]['depth_m'],'depth_end':part[-1]['depth_m'],'length':len(part),'categories_a':list(dict.fromkeys(r['path_category_a'] for r in part)),'categories_b':list(dict.fromkeys(r['path_category_b'] for r in part))})
  i=j+1
 return segments
def compute(run_a,run_b,mapping):
 states_a=_states(run_a,'运行A');states_b=_states(run_b,'运行B')
 normalized=validate_mapping(mapping,states_a,states_b)
 cats=normalized['categories'];index={c:i for i,c in enumerate(cats)}
 map_a={e['state']:e['category'] for e in normalized['run_a']};map_b={e['state']:e['category'] for e in normalized['run_b']}
 ids_a=[s['id'] for s in states_a];ids_b=[s['id'] for s in states_b]
 rows_a,rows_b=aligned_rows(run_a,run_b);rows=[]
 for a,b in zip(rows_a,rows_b):
  ca,cb=map_a[a['path_state']],map_b[b['path_state']]
  rows.append({'depth_m':a['depth_m'],'value':a['value'],'posterior_a':_aggregate(a['posterior'],ids_a,map_a,index),'posterior_b':_aggregate(b['posterior'],ids_b,map_b,index),'path_category_a':ca,'path_category_b':cb,'point_category_a':map_a[a['point_state']],'point_category_b':map_b[b['point_state']],'agree':ca==cb})
 divergent=sum(not r['agree'] for r in rows)
 checksum=hashlib.sha256(json.dumps({'run_a':run_a['id'],'run_b':run_b['id'],'mapping':normalized,'run_checksums':[run_a['result']['checksum'],run_b['result']['checksum']]},sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 result={'borehole':run_a['result']['borehole'],'point_count':len(rows),'depth_start':rows[0]['depth_m'],'depth_end':rows[-1]['depth_m'],'depth_step_m':1.,'categories':cats,'models':{'run_a':run_a['result']['model'],'run_b':run_b['result']['model']},'run_checksums':{'run_a':run_a['result']['checksum'],'run_b':run_b['result']['checksum']},'rows':rows,'divergent_points':divergent,'agreement_ratio':(len(rows)-divergent)/len(rows),'segments':_segments(rows),'category_counts_a':{c:sum(r['path_category_a']==c for r in rows) for c in cats},'category_counts_b':{c:sum(r['path_category_b']==c for r in rows) for c in cats},'checksum':checksum,'limitations':['归并类别是人工指定的共同解释层，不新增地质含义；类别后验为同组状态后验之和','对齐按深度逐一核对孔号/深度/读数，任一不符即拒绝比较，不做插值或错位拼接','分歧孔段由归并后的两条Viterbi路径类别比较得到，与点态argmax是两种推断目标','旧比较保留双方运行快照与原映射；更新归并规则会另存新比较，不改写历史']}
 return normalized,result
def _create(run_a_id,run_b_id,mapping,supersedes=''):
 if run_a_id==run_b_id:raise ValueError('需选择两次不同的已完成运行')
 run_a,run_b=repo.get('runs',run_a_id),repo.get('runs',run_b_id)
 if run_a['status']!='completed':raise ValueError('运行A尚未完成，只有已完成运行可比较')
 if run_b['status']!='completed':raise ValueError('运行B尚未完成，只有已完成运行可比较')
 normalized,result=compute(run_a,run_b,mapping)
 item=repo.put('comparisons',RunComparison(new_id('cmp'),run_a_id,run_b_id,normalized,result,supersedes,now()))
 ARTIFACT_DIR.mkdir(parents=True,exist_ok=True);(ARTIFACT_DIR/(item['id']+'.json')).write_text(json.dumps(item,ensure_ascii=False))
 return item
def create(data):return _create(data.run_a_id,data.run_b_id,{'categories':data.mapping.categories,'run_a':[e.model_dump() for e in data.mapping.run_a],'run_b':[e.model_dump() for e in data.mapping.run_b]})
def recompute(id,data):
 old=repo.get('comparisons',id)
 return _create(old['run_a_id'],old['run_b_id'],{'categories':data.mapping.categories,'run_a':[e.model_dump() for e in data.mapping.run_a],'run_b':[e.model_dump() for e in data.mapping.run_b]},supersedes=id)
def download(id):
 c=repo.get('comparisons',id);r=c['result'];cats=r['categories']
 out=io.StringIO();w=csv.writer(out)
 w.writerow(['comparison','run_a','run_b','borehole','depth_start','depth_end','points','divergent_points','agreement_ratio','supersedes','checksum'])
 w.writerow([c['id'],c['run_a_id'],c['run_b_id'],r['borehole'],r['depth_start'],r['depth_end'],r['point_count'],r['divergent_points'],r['agreement_ratio'],c['supersedes'] or '原始比较',r['checksum']])
 w.writerow(['model_a',safe_cell(r['models']['run_a']['name']),'revision',r['models']['run_a']['revision'],'run_checksum',r['run_checksums']['run_a']])
 w.writerow(['model_b',safe_cell(r['models']['run_b']['name']),'revision',r['models']['run_b']['revision'],'run_checksum',r['run_checksums']['run_b']])
 w.writerow([]);w.writerow(['mapping_side','state_id','state_human_name','common_category'])
 for side in ('run_a','run_b'):
  names={s['id']:s['name'] for s in r['models'][side]['config']['states']}
  for e in c['mapping'][side]:w.writerow([side,e['state'],safe_cell(names.get(e['state'],'')),safe_cell(e['category'])])
 w.writerow([]);w.writerow(['divergent_segment','depth_start','depth_end','length_m','categories_a','categories_b'])
 for i,s in enumerate(r['segments'],1):w.writerow([i,s['depth_start'],s['depth_end'],s['length'],safe_cell('|'.join(s['categories_a'])),safe_cell('|'.join(s['categories_b']))])
 w.writerow([]);w.writerow(['depth_m','measurement','path_category_a','path_category_b','point_category_a','point_category_b','paths_agree']+['posterior_a_'+x for x in cats]+['posterior_b_'+x for x in cats])
 for p in r['rows']:w.writerow([p['depth_m'],p['value'],safe_cell(p['path_category_a']),safe_cell(p['path_category_b']),safe_cell(p['point_category_a']),safe_cell(p['point_category_b']),1 if p['agree'] else 0]+p['posterior_a']+p['posterior_b'])
 return '\ufeff'+out.getvalue()
