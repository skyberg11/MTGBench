import {copy, cardOrder, cardFiles} from './content.js';
import {renderResearch} from './research.js';
const $ = id => document.getElementById(id);
const gameIds = ['word_chain','wordle','twenty_questions','wheel_of_fortune','situation_puzzles','twenty_features','alias'];
const modelLabels = {
 'deepseek-v3.1-terminus':'DeepSeek V3.1 Terminus',
 'deepseek-v4-flash':'DeepSeek V4 Flash',
 'deepseek-v4-pro':'DeepSeek V4 Pro',
 'gemini-3-flash-preview':'Gemini 3 Flash Preview',
 'gemini-3.1-flash-lite':'Gemini 3.1 Flash Lite',
 'gemini-3.1-pro-preview':'Gemini 3.1 Pro Preview',
 'gpt-4.1':'GPT-4.1',
 'gpt-5.4':'GPT-5.4',
 'gpt-5.4-mini':'GPT-5.4 Mini',
 'gpt-5.4-nano':'GPT-5.4 Nano',
 'gpt-oss-120b':'GPT-OSS 120B',
 'qwen3-235b-a22b-instruct-2507':'Qwen3 235B A22B Instruct 2507',
 'qwen3-235b-a22b-thinking-2507':'Qwen3 235B A22B Thinking 2507',
 'qwen3-30b-a3b-instruct-2507':'Qwen3 30B A3B Instruct 2507',
 'qwen3-30b-a3b-thinking-2507':'Qwen3 30B A3B Thinking 2507',
 'qwen3.5-35b-a3b':'Qwen3.5 35B A3B'
};
function modelFamily(id) {
 if(id.startsWith('gpt-'))return 'openai';
 if(id.startsWith('qwen'))return 'qwen';
 if(id.startsWith('gemini-'))return 'gemini';
 if(id.startsWith('deepseek-'))return 'deepseek';
 return id==='human'?'human':'other';
}
const familyLabels = {openai:'OpenAI',qwen:'Qwen',gemini:'Google Gemini',deepseek:'DeepSeek',human:'Human',other:''};
function modelName(id){return id==='human'?t().human:(modelLabels[id]||id);}
const texts = {
 en: {subtitle:'MTGBench is a benchmark of seven multi-turn games in English and Russian. The paper evaluates how language models use feedback and follow game rules across turns, comparing AO, CoT and Reasoning modes with a human baseline.',paper:'Paper · ACL Anthology ↗',pending:'Paper · coming to ACL Anthology',poster:'Poster',rules:'Rules & scoring ↗',board:'Leaderboard',export:'Export CSV',language:'Evaluation language',metric:'Metric',mode:'Reasoning mode',all:'All',ci:'95% confidence intervals',reset:'Reset',models:'Models',games:'Games',search:'Find a model…',select:'Select all',none:'Clear',method:'Scores are shown on a 0–100 scale; higher is better. The mean weights the selected games equally. Missing results are never treated as zero.',foot:'Intervals are percentile-bootstrap 95% CIs. Human results are available in Russian only, from a small sample.',model:'Model',mean:'Mean',score:'Score',win:'Win rate',reasoning:'Reasoning',empty:'No results. Select at least one model and one game, or reset the filters.',posterPending:'The poster will appear here when it is available.',source:'Methodology & source ↗',raw:'Source CSV ↓',human:'Human',error:'Could not load results. Reload the page or download the source CSV.',gamesList:['Word Chain','Wordle','20 Questions','Wheel of Fortune','Situation Puzzles','20 Features','Alias']},
 ru: {subtitle:'MTGBench — семь multiturn-игр на русском и английском языках. В статье мы оцениваем, как LLM используют обратную связь и соблюдают правила в ходе игры. Сравниваем результаты в режимах AO, CoT и Reasoning, а также приводим результаты людей.',paper:'Статья · ACL Anthology ↗',pending:'Статья · скоро в ACL Anthology',poster:'Постер',rules:'Правила и метрики ↗',board:'Результаты',export:'Скачать CSV',language:'Язык игр',metric:'Метрика',mode:'Режим',all:'Все',ci:'95% доверительные интервалы',reset:'Сбросить',models:'Модели',games:'Игры',search:'Найти модель…',select:'Выбрать все',none:'Очистить',method:'Шкала от 0 до 100; больше — лучше. Среднее учитывает выбранные игры с равными весами.',foot:'95% интервалы рассчитаны перцентильным бутстрэпом. Результаты людей есть только на русском.',model:'Модель',mean:'Среднее',score:'Скор',win:'Доля побед',reasoning:'Reasoning',empty:'Нет результатов. Выберите хотя бы одну модель и игру или сбросьте фильтры.',posterPending:'Здесь появится постер, когда он будет готов.',source:'Методология и данные ↗',raw:'Исходный CSV ↓',human:'Человек',error:'Не удалось загрузить результаты. Обновите страницу или скачайте исходный CSV.',gamesList:['Города','Wordle','20 вопросов','Поле чудес','Данетки','20 признаков','Alias']},
 zh: {subtitle:'MTGBench 包含七种英语和俄语多轮游戏。论文评估语言模型如何在多轮交互中利用反馈并遵守游戏规则，比较 AO、CoT 和 Reasoning 模式，并提供人类基线结果。',paper:'论文 · ACL Anthology ↗',pending:'论文 · 即将发布于 ACL Anthology',poster:'海报',rules:'规则与评分 ↗',board:'排行榜',export:'导出 CSV',language:'评测语言',metric:'指标',mode:'推理模式',all:'全部',ci:'95% 置信区间',reset:'重置',models:'模型',games:'游戏',search:'搜索模型…',select:'全选',none:'清空',method:'分数范围为 0–100，越高越好。均值对所选游戏赋予相同权重。缺失结果不视为零。',foot:'95% 置信区间使用百分位自助法。人类结果仅有俄语，且样本量较小。',model:'模型',mean:'均值',score:'得分',win:'胜率',reasoning:'Reasoning',empty:'没有结果。请至少选择一个模型和一种游戏，或重置筛选条件。',posterPending:'海报发布后将在此显示。',source:'方法与数据 ↗',raw:'原始 CSV ↓',human:'人类',error:'无法加载结果。请刷新页面或下载原始 CSV。',gamesList:['城市接龙','Wordle','20 个问题','幸运转盘','情境谜题','20 个特征','Alias']}
};
let data, config, models, researchData, visibleRows = [];
const params = new URLSearchParams(location.search);
let state = {ui: texts[params.get('ui')] ? params.get('ui') : 'en', language:params.get('language') === 'ru' ? 'ru':'en', metric:params.get('metric') === 'win_rate'?'win_rate':'score', mode:['answer_only','cot','reasoning'].includes(params.get('mode'))?params.get('mode'):'all', ci:params.get('ci') === '1', sort:params.get('sort') || 'mean', ascending:params.get('asc') === '1'};
const t = () => texts[state.ui];
const c = () => copy[state.ui];
const gameName = id => t().gamesList[gameIds.indexOf(id)];
const modeName = id => ({answer_only:'AO',cot:'CoT',reasoning:t().reasoning})[id];
function element(tag, content, cls) { const el=document.createElement(tag); if(content!==undefined)el.textContent=content;if(cls)el.className=cls;return el; }
state.view = params.get('view') === 'poster' || location.hash === '#poster' ? 'poster' : 'explore';
function syncUrl() { const p=new URLSearchParams({ui:state.ui,language:state.language,metric:state.metric,mode:state.mode,ci:state.ci?'1':'0',models:[...state.models].join(','),games:[...state.games].join(','),sort:state.sort,asc:state.ascending?'1':'0'});if(state.view==='poster')p.set('view','poster');history.replaceState(null,'',`${location.pathname}?${p}${location.hash==='#poster'?'':location.hash}`); }
function choices(container, ids, selected, label, onChange) { $(container).replaceChildren();for(const id of ids){const l=element('label');const input=element('input');input.type='checkbox';input.checked=selected.has(id);input.value=id;input.addEventListener('change',()=>{input.checked?selected.add(id):selected.delete(id);onChange();});l.append(input);if(container==='models')l.append(modelLogo(id));l.append(document.createTextNode(label(id)));$(container).append(l);} }
const languageLabels = {
 en:{en:'English',ru:'Russian',zh:'Chinese',interface:'Interface language'},
 ru:{en:'Английский',ru:'Русский',zh:'Китайский',interface:'Язык интерфейса'},
 zh:{en:'英语',ru:'俄语',zh:'中文',interface:'界面语言'}
};
function modelLogo(id){
 const family=modelFamily(id);
 if(!['openai','qwen','gemini','deepseek','human'].includes(family))return document.createDocumentFragment();
 const img=element('img');img.src=`assets/logos/${family}.svg`;img.alt='';img.setAttribute('aria-hidden','true');img.width=20;img.height=20;img.className='model-logo';return img;
}
function translate() {
 document.documentElement.lang=state.ui;
 const languages=languageLabels[state.ui];
 for(const option of $('data-language').options)option.textContent=languages[option.value];
 for(const option of $('ui-language').options)option.textContent={en:'English',ru:'Русский',zh:'中文'}[option.value];
 $('ui-language').setAttribute('aria-label',languages.interface);
 $('ui-language').previousElementSibling.textContent=languages.interface;
 const mapping={subtitle:'subtitle','paper-pending':'pending',paper:'paper',rules:'rules','leaderboard-title':'board',export:'export','language-label':'language','metric-label':'metric','mode-label':'mode','ci-label':'ci',reset:'reset','models-label':'models','games-label':'games','all-models':'select','no-models':'none',method:'method',footnote:'foot','poster-title':'poster',source:'source','raw-data':'raw',caption:'board'};
 for(const [id,key] of Object.entries(mapping))$(id).textContent=t()[key];
 $('model-search').placeholder=t().search;$('model-search').setAttribute('aria-label',t().search);
 $('metric').options[0].textContent=t().score;$('metric').options[1].textContent=t().win;$('mode').options[0].textContent=t().all;$('mode').options[3].textContent=t().reasoning;
 for(const [id,key] of [['ui-language','ui'],['data-language','language'],['metric','metric'],['mode','mode']])$(id).value=state[key];$('ci').checked=state.ci;
 choices('models',models,state.models,modelName,render);
 choices('games',gameIds,state.games,gameName,()=>{if(!state.games.has(state.sort))state.sort='mean';render();});
 filterModels();
 if(!config.posterUrl)$('poster-content').textContent=t().posterPending;
 for(const node of document.querySelectorAll('[data-copy]'))node.textContent=c()[node.dataset.copy];
 $('dialog-close').setAttribute('aria-label',c().close);
 renderCards();setView(state.view);
 if(researchData)renderResearch({data,researchData,config,ui:state.ui,gameIds,gameName,modelName,modelLogo,modeName});
 render();
}
function filterModels(){const normalize=s=>s.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');const q=normalize($('model-search').value);for(const label of $('models').children){const id=label.querySelector('input').value;label.hidden=!normalize(label.textContent+' '+id+' '+familyLabels[modelFamily(id)]).includes(q);}}
function getRows(){
 const grouped=new Map();
 for(const r of data){if(r.language!==state.language||!state.models.has(r.model)||(r.model!=='human'&&state.mode!=='all'&&r.mode!==state.mode))continue;const key=r.model+'|'+r.mode;if(!grouped.has(key))grouped.set(key,{model:r.model,mode:r.mode,cells:{}});grouped.get(key).cells[r.game]=r;}
 return [...grouped.values()].filter(r=>[...state.games].some(g=>r.cells[g])).map(r=>{const vals=[...state.games].map(g=>r.cells[g]?.[state.metric]);r.mean=vals.length&&vals.every(v=>v!==undefined)?vals.reduce((a,b)=>a+b,0)/vals.length:null;return r;}).sort((a,b)=>{const value=r=>state.sort==='model'?modelName(r.model):state.sort==='mean'?r.mean:r.cells[state.sort]?.[state.metric];const x=value(a),y=value(b);if(x==null)return y==null?0:1;if(y==null)return -1;const cmp=typeof x==='string'?x.localeCompare(y):x-y;return (state.ascending?cmp:-cmp)||a.model.localeCompare(b.model)||a.mode.localeCompare(b.mode);});
}
const number = n => (100*n).toLocaleString(state.ui,{minimumFractionDigits:1,maximumFractionDigits:1});
function render(){
 syncUrl();const games=gameIds.filter(g=>state.games.has(g));visibleRows=getRows();
 $('human-notice').hidden=state.language==='ru';
 const tr=element('tr');for(const [key,title] of [['model',t().model],['mode',t().mode],['mean',t().mean],...games.map(g=>[g,gameName(g)])]){const th=element('th');th.scope='col';if(key==='mode')th.textContent=title;else{th.setAttribute('aria-sort',state.sort===key?(state.ascending?'ascending':'descending'):'none');const b=element('button',title+(state.sort===key?(state.ascending?' ↑':' ↓'):''));b.addEventListener('click',()=>{state.ascending=state.sort===key?!state.ascending:key==='model';state.sort=key;render();});th.append(b);}tr.append(th);}$('head').replaceChildren(tr);$('body').replaceChildren();
 let rank=0;
 for(const row of visibleRows){const human=row.model==='human';const tr=element('tr');tr.className='family-'+modelFamily(row.model)+(human?' human':'');tr.dataset.model=row.model;const name=element('td');name.title=familyLabels[modelFamily(row.model)]+' · '+row.model;name.append(element('span',human?'—':String(++rank).padStart(2,'0'),'rank'),modelLogo(row.model),document.createTextNode(modelName(row.model)));tr.append(name,element('td',human?'—':modeName(row.mode)));
 for(const id of ['mean',...games]){const original=id==='mean'?(games.length===7?row.cells.Total:null):row.cells[id];const value=id==='mean'?row.mean:original?.[state.metric];const td=element('td',value==null?'—':number(value));if(original&&value!=null){td.title=`n = ${original.n}; 95% CI ${number(original[state.metric+'_ci_low'])}–${number(original[state.metric+'_ci_high'])}`;if(state.ci)td.append(element('small',`${number(original[state.metric+'_ci_low'])}–${number(original[state.metric+'_ci_high'])}`));}tr.append(td);}$('body').append(tr);}
 if(!visibleRows.length){const tr=element('tr');const td=element('td',t().empty,'empty');td.colSpan=3+games.length;tr.append(td);$('body').append(tr);}
}
function exportCsv(){const games=gameIds.filter(g=>state.games.has(g));const columns=['model','mode','language','metric','mean',...games.flatMap(g=>[g,g+'_ci_low',g+'_ci_high',g+'_n'])];const rows=visibleRows.map(r=>[r.model,r.mode,state.language,state.metric,r.mean,...games.flatMap(g=>{const v=r.cells[g];return v?[v[state.metric],v[state.metric+'_ci_low'],v[state.metric+'_ci_high'],v.n]:['','','',''];})]);const csv=[columns,...rows].map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=element('a');a.href=url;a.download='mtgbench-selection.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function load(){try{
 [data,config]=await Promise.all(['data.json','config.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error(r.status);return r.json();}));
 models=[...new Set(data.map(r=>r.model))].sort((a,b)=>Number(b==='human')-Number(a==='human')||a.localeCompare(b));state.models=new Set(params.has('models')?params.get('models').split(',').filter(m=>models.includes(m)):models);state.games=new Set(params.has('games')?params.get('games').split(',').filter(g=>gameIds.includes(g)):gameIds);if(!['model','mean',...state.games].includes(state.sort))state.sort='mean';
 $('github').href=config.repository;$('rules').href=config.repository+'/blob/main/docs/games.md';$('source').href=config.repository+'/tree/main/analysis';
 if(config.paperUrl){$('paper').hidden=false;$('paper').href=config.paperUrl;$('paper-pending').hidden=true;}
 if(config.posterUrl){const a=element('a');a.href=config.posterUrl;a.target='_blank';a.rel='noopener';if(/\.pdf(?:$|\?)/i.test(config.posterUrl))a.textContent='PDF ↗';else{const img=element('img');img.src=config.posterUrl;img.alt='MTGBench poster';img.loading='lazy';img.width=841;img.height=1189;a.append(img);}$('poster-content').replaceChildren(a);}
 for(const [id,key] of [['ui-language','ui'],['data-language','language'],['metric','metric'],['mode','mode']])$(id).addEventListener('change',e=>{state[key]=e.target.value;key==='ui'?translate():render();});
 $('ci').addEventListener('change',e=>{state.ci=e.target.checked;render();});$('model-search').addEventListener('input',filterModels);
 $('all-models').onclick=()=>{state.models=new Set(models);translate();};$('no-models').onclick=()=>{state.models.clear();translate();};
 $('reset').onclick=()=>{state={...state,language:'en',metric:'score',mode:'all',ci:false,sort:'mean',ascending:false,models:new Set(models),games:new Set(gameIds)};$('model-search').value='';translate();};
 $('export').onclick=exportCsv;
 $('show-human').onclick=()=>{state.language='ru';state.models.add('human');translate();};
 for(const view of ['explore','poster']){
  $('tab-'+view).onclick=()=>setView(view);
  $('tab-'+view).onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'explore':e.key==='End'?'poster':view==='poster'?'explore':'poster';setView(next);$('tab-'+next).focus();}};
 }
 $('dialog-close').onclick=()=>$('game-dialog').close();
 $('game-dialog').onclick=e=>{if(e.target===$('game-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}};
 translate();
 try{const response=await fetch('research.json');if(!response.ok)throw Error(response.status);researchData=await response.json();renderResearch({data,researchData,config,ui:state.ui,gameIds,gameName,modelName,modelLogo,modeName});}catch(error){$('research-status').textContent=c().researchError;console.error(error);}
 }catch(error){$('status').hidden=false;$('status').textContent=t().error;console.error(error);}}
function setView(view){state.view=view;for(const id of ['explore','poster']){$('panel-'+id).hidden=id!==view;$('tab-'+id).setAttribute('aria-selected',String(id===view));$('tab-'+id).tabIndex=id===view?0:-1;}$('findings-link').hidden=view==='poster';syncUrl();}
// Bold the term before the first colon, e.g. "Letter game:".
function termNote(node,text){const [,term,rest]=text.match(/^([^:：]*[:：])?([\s\S]*)$/);node.replaceChildren(...(term?[element('strong',term)]:[]),rest);}
function renderCards(){
 $('game-deck').replaceChildren();
 for(const [i,id] of cardOrder.entries()){
  const b=element('button',undefined,'game-card');b.setAttribute('aria-label',gameName(id));const img=element('img');img.src=cardFiles[id];img.alt='';img.width=750;img.height=1050;b.append(img,element('span',gameName(id),'card-label'));
  b.onclick=()=>{$('dialog-image').src=cardFiles[id];$('dialog-title').textContent=gameName(id);$('dialog-category').textContent=`0${i+1} / 07 · ${i<3?c().letter:c().semantic}`;$('dialog-description').textContent=c().descriptions[gameIds.indexOf(id)];termNote($('dialog-type'),i<3?c().letterNote:c().semanticNote);termNote($('dialog-checker'),['situation_puzzles','twenty_features','alias'].includes(id)?c().judgeNote:c().algorithmicNote);termNote($('dialog-scoring'),['word_chain','twenty_questions'].includes(id)?c().survival:c().speed);$('game-dialog').showModal();};
  $('game-deck').append(b);
 }
}
load();
