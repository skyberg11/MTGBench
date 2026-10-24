import {copy, skillIds} from './content.js';

const chartState = {overallMode:'all', languageMode:'reasoning_cot', game:'wordle', languageModels:null, difficultyModels:null, intervals:false};
let chartResizeObserver;
const modeColors = {answer_only:'#4db6ac',cot:'#7753bc',reasoning:'#004d40',human:'#b58a2c'};
const modelColors = ['#56b4e9','#009e73','#0072b2','#b59b00','#d55e00','#e69f00','#7753bc','#be6089','#5c6b47','#9b4e36','#487e91','#3c4c87','#886a94','#ce7381','#635b46','#677b76'];
const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
const svgEl=(tag,attrs={},text)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);if(text!==undefined)node.textContent=text;return node;};
const average=values=>values.reduce((sum,value)=>sum+value,0)/values.length;
const pct=(value,ui)=> (value*100).toLocaleString(ui,{minimumFractionDigits:1,maximumFractionDigits:1});

function pointTip(node,text){
 node.append(svgEl('title',{},text));node.setAttribute('tabindex','0');node.setAttribute('aria-label',text);
 const box=document.getElementById('chart-tooltip');
 const show=event=>{box.textContent=text;box.hidden=false;const rect=node.getBoundingClientRect();const x=event.clientX||rect.left+rect.width/2,y=event.clientY||rect.bottom;box.style.left=Math.max(8,Math.min(x+12,innerWidth-box.offsetWidth-8))+'px';box.style.top=Math.max(8,Math.min(y+12,innerHeight-box.offsetHeight-8))+'px';};
 const hide=()=>{box.hidden=true;};node.addEventListener('pointerenter',show);node.addEventListener('pointermove',show);node.addEventListener('pointerleave',hide);node.addEventListener('focus',show);node.addEventListener('blur',hide);node.addEventListener('keydown',e=>{if(e.key==='Escape')hide();});
}
function svgFrame(width,height,title){const svg=svgEl('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':title,class:'data-chart'});svg.append(svgEl('title',{},title));return svg;}
function grid(svg,x0,x1,y0,y1,horizontal=true){
 for(const v of [0,.25,.5,.75,1]){
  const x=x0+(x1-x0)*v,y=y1-(y1-y0)*v;
  svg.append(svgEl('line',horizontal?{x1:x,y1:y0,x2:x,y2:y1,class:'chart-grid'}:{x1:x0,y1:y,x2:x1,y2:y,class:'chart-grid'}));
  svg.append(svgEl('text',horizontal?{x,y:y1+23,'text-anchor':'middle',class:'chart-tick'}:{x:x0-12,y:y+4,'text-anchor':'end',class:'chart-tick'},String(v*100)));
 }
}
function selectControl(label,values,current,onChange,id){const field=el('label',undefined,'chart-control');field.append(el('span',label));const select=el('select');select.id=id;for(const [value,title] of values){const option=el('option',title);option.value=value;select.append(option);}select.value=current;select.onchange=()=>onChange(select.value);field.append(select);return field;}
// Text wrapped in ||…|| is blurred until hovered, focused or clicked.
function spoilerText(text,cls){const p=el('p',undefined,cls);text.split('||').forEach((part,i)=>{if(i%2){const s=el('span',part,'spoiler');s.tabIndex=0;s.onclick=()=>s.classList.add('revealed');p.append(s);}else p.append(part);});return p;}
// Poster colormap (cream → teal), linear over τ-b in [0, 1]; negative values clamp to cream.
const heatStops=[[255,248,225],[128,203,196],[0,121,107],[0,77,64]];
function heatColor(value){const t=Math.min(1,Math.max(0,value))*(heatStops.length-1),i=Math.min(heatStops.length-2,Math.floor(t)),f=t-i;return heatStops[i].map((v,k)=>Math.round(v+(heatStops[i+1][k]-v)*f));}
function legend(items){const wrap=el('div',undefined,'chart-legend');for(const [label,color] of items){const item=el('span');const swatch=el('i');swatch.style.background=color;item.append(swatch,document.createTextNode(label));wrap.append(item);}return wrap;}

export function renderResearch(context){
 chartResizeObserver?.disconnect();
 const {data,researchData,config,ui,gameIds,gameName,modelName,modeName}=context,c=copy[ui];
 const root=document.getElementById('research');root.replaceChildren();document.getElementById('chart-tooltip').hidden=true;
 const index=new Map(data.map(r=>[[r.model,r.mode,r.language,r.game].join('|'),r]));
 const get=(model,mode,language,game)=>index.get([model,mode,language,game].join('|'));
 const totals=data.filter(r=>r.game==='Total'&&r.language==='en'&&r.model!=='human');
 const orderedModels=[...new Set(totals.map(r=>r.model))].sort((a,b)=>Math.max(...totals.filter(r=>r.model===b).map(r=>r.score))-Math.max(...totals.filter(r=>r.model===a).map(r=>r.score))||a.localeCompare(b));
 const selected=researchData.selectedModels;
 const allModels=[...selected,...orderedModels.filter(model=>model!=='human'&&!selected.includes(model))];
 const modelColor=model=>modelColors[allModels.indexOf(model)];
 if(!chartState.languageModels)chartState.languageModels=new Set(selected);
 if(!chartState.difficultyModels)chartState.difficultyModels=new Set(selected);
 const modes=[['all',c.allModes],['answer_only','AO'],['cot','CoT'],['reasoning',c.reason]];
 const labelMode=id=>id==='human'?c.human:modeName(id);
 function modelSelector(id,stateKey,onChange,colored=false,options=allModels){
  const details=el('details',undefined,'chart-model-selector');details.id=id;
  const summary=el('summary');details.append(summary);
  const controls=el('div',undefined,'model-selector-controls');
  const search=el('input');search.type='search';search.placeholder=c.searchModels;search.setAttribute('aria-label',c.searchModels);controls.append(search);
  const actions=el('div',undefined,'model-selector-actions');controls.append(actions);
  const list=el('div',undefined,'model-toggles');list.setAttribute('role','group');list.setAttribute('aria-label',c.chooseModels);
  const update=()=>{summary.textContent=`${c.chooseModels} · ${chartState[stateKey].size} / ${options.length}`;};
  for(const [action,label,models] of [['all',c.selectAll,options],['default',c.selectDefault,selected],['none',c.selectNone,[]]]){
   const button=el('button',label);button.type='button';button.dataset.action=action;button.onclick=()=>{chartState[stateKey]=new Set(models);for(const input of list.querySelectorAll('input'))input.checked=chartState[stateKey].has(input.value);update();onChange();};actions.append(button);
  }
  for(const model of options){
   const label=el('label');label.dataset.model=model;
   const input=el('input');input.type='checkbox';input.value=model;input.checked=chartState[stateKey].has(model);
   input.onchange=()=>{input.checked?chartState[stateKey].add(model):chartState[stateKey].delete(model);update();onChange();};label.append(input);
   if(colored){label.style.setProperty('--series-color',modelColor(model));label.append(el('i'));}
   label.append(el('span',modelName(model)));list.append(label);
  }
  search.oninput=()=>{const query=search.value.trim().toLocaleLowerCase(ui);for(const label of list.children)label.hidden=!`${modelName(label.dataset.model)} ${label.dataset.model}`.toLocaleLowerCase(ui).includes(query);};
  details.append(controls,list);update();return details;
 }
 function article(number,id,key,sourcePath){
  const article=el('article',undefined,'research-article');article.id=id;
  const heading=el('div',undefined,'research-heading');heading.append(el('span',String(number).padStart(2,'0'),'section-number'));const title=el('div');const h=el('h3',c[key+'Title']);h.id=id+'-title';article.setAttribute('aria-labelledby',h.id);title.append(h,spoilerText(c[key+'Lead'],'chart-lead'));heading.append(title);article.append(heading);
  const layout=el('div',undefined,'figure-layout'),plot=el('div',undefined,'figure-content');
  const explanation=el('aside',undefined,'figure-explanation');explanation.setAttribute('aria-labelledby',h.id);
  const prose=el('div',undefined,'figure-prose');c[key+'Text'].forEach(p=>prose.append(el('p',p)));explanation.append(prose);
  const sources=el('div',undefined,'source-links');const a=el('a',c.source);a.href=config.repository+'/blob/main/'+sourcePath;const download=el('a',c.chartData);download.href=key==='overall'||key==='language'?'summary.csv':'research.json';download.download='';sources.append(a,download);explanation.append(sources);layout.append(plot,explanation);article.append(layout);root.append(article);return plot;
 }

 // 01 · Full-model view, with separate mode markers and original intervals.
 const overall=article(1,'overall','overall','analysis/outputs/tables/summary.csv');
 const overallControls=el('div',undefined,'chart-controls');const overallPlots=el('div',undefined,'chart-scroll overall-chart');
 overallControls.append(selectControl(c.mode,modes,chartState.overallMode,v=>{chartState.overallMode=v;drawOverall();},'overall-mode'),legend(Object.entries(modeColors).map(([id,color])=>[labelMode(id),color])));
 overall.append(overallControls,overallPlots);
 function drawOverall(){
  // A shared model column keeps both language panels readable beside the explanation.
  const compact=overallPlots.clientWidth<800,width=compact?Math.max(280,overallPlots.clientWidth):1000,rowHeight=compact?68:38,y0=62,y1=y0+(orderedModels.length+1)*rowHeight;
  const svg=svgFrame(width,y1+42,c.overallTitle);
  for(const language of ['en','ru']){
   const panel=svgEl('g',{role:'group','aria-label':language==='en'?c.english:c.russian,'data-language':language});
   const x0=compact?(language==='en'?18:width/2+22):(language==='en'?280:650),x1=compact?(language==='en'?width/2-22:width-18):x0+330;
   panel.append(svgEl('text',{x:(x0+x1)/2,y:29,'text-anchor':'middle',class:'chart-panel-title'},language==='en'?c.english:c.russian));grid(panel,x0,x1,y0,y1);
   const panelModels=language==='ru'?[...orderedModels,'human']:orderedModels;
   for(const [i,model] of panelModels.entries()){
    const y=y0+rowHeight*i+(compact?37:18);
    const name=modelName(model);
    if(model==='human'){panel.append(svgEl('rect',{x:x0-12,y:y-(compact?38:17),width:x1-x0+24,height:compact?62:35,rx:5,fill:'#fff4d5'}),svgEl('text',{x:x0+8,y:y+(compact?-17:4),class:'chart-model'},name));}
    const available=model==='human'?['answer_only']:['answer_only','cot','reasoning'].filter(mode=>chartState.overallMode==='all'||mode===chartState.overallMode);
    let j=0;
    for(const mode of available){const r=get(model,mode,language,'Total');if(!r)continue;const yy=y+(available.length>1?(j++-(available.length-1)/2)*9:0),color=modeColors[model==='human'?'human':mode],x=value=>x0+(x1-x0)*value;
     panel.append(svgEl('line',{x1:x(r.score_ci_low),x2:x(r.score_ci_high),y1:yy,y2:yy,stroke:color,'stroke-width':2,opacity:.65}));
     const dot=svgEl('circle',{cx:x(r.score),cy:yy,r:4,fill:color,stroke:'#fff','stroke-width':1});pointTip(dot,`${name} · ${model==='human'?c.reference:modeName(mode)} · ${language.toUpperCase()}: ${pct(r.score,ui)} · 95% CI ${pct(r.score_ci_low,ui)}–${pct(r.score_ci_high,ui)} · n=${r.n}`);panel.append(dot);
    }
   }
   svg.append(panel);
  }
  orderedModels.forEach((model,i)=>{const y=y0+rowHeight*i+(compact?8:22);if(compact)svg.append(svgEl('rect',{x:0,y:y-17,width,height:23,fill:'#fffdf8'}));svg.append(svgEl('text',{x:8,y,class:'chart-model'},modelName(model)));});
  overallPlots.replaceChildren(svg);
 }
 drawOverall();

 // 02 · Paired language results and independently reproducible tier gaps.
 const cross=article(2,'languages','language','analysis/outputs/tables/summary.csv');
 const crossControls=el('div',undefined,'chart-controls'),crossLegend=el('div');crossControls.append(selectControl(c.mode,[['answer_only','AO'],['reasoning_cot','CoT / Reasoning']],chartState.languageMode,v=>{chartState.languageMode=v;drawLanguages();},'language-mode'),crossLegend);
 const tabs=el('div',undefined,'game-pills');tabs.setAttribute('role','group');tabs.setAttribute('aria-label',c.game);
 const paired=el('div',undefined,'chart-scroll');
 for(const game of gameIds){const b=el('button',gameName(game));b.dataset.game=game;b.onclick=()=>{chartState.game=game;drawLanguages();};tabs.append(b);}
 cross.append(modelSelector('language-models','languageModels',drawLanguages,false,['human',...allModels]),crossControls,tabs,paired);
 function drawLanguages(){
  for(const button of tabs.children)button.setAttribute('aria-pressed',String(button.dataset.game===chartState.game));
  const models=allModels.filter(model=>chartState.languageModels.has(model));
  const showHuman=chartState.languageModels.has('human');
  if(showHuman)models.push('human');
  crossLegend.replaceChildren(legend([[c.english,'#00796b'],[c.russian,'#ffa000'],...(showHuman?[[c.human,modeColors.human]]:[])]));
  if(!models.length){paired.replaceChildren(el('p',c.noData,'chart-empty'));return;}
  const compact=paired.clientWidth<800,width=compact?Math.max(280,paired.clientWidth):1000,x0=compact?18:315,x1=compact?width-18:940,y0=20,rowHeight=compact?82:43,y1=32+models.length*rowHeight,svg=svgFrame(width,y1+42,`${gameName(chartState.game)} · ${c.languageTitle}`);grid(svg,x0,x1,y0,y1);const x=value=>x0+(x1-x0)*value;
  models.forEach((model,i)=>{
   const isHuman=model==='human';
   // The paper groups prompted CoT and native Reasoning; retain each model's actual mode.
   const mode=isHuman?'answer_only':chartState.languageMode==='reasoning_cot'
    ? ['reasoning','cot'].find(mode=>get(model,mode,'en',chartState.game)||get(model,mode,'ru',chartState.game))
    : chartState.languageMode;
   const y=42+i*rowHeight+(compact?28:0),labelY=compact?y-36:y-2;
   if(isHuman)svg.append(svgEl('rect',{x:0,y:compact?labelY-18:y-20,width,height:compact?74:40,rx:5,fill:'#fff4d5',class:'human-chart-row'}));
   else if(compact)svg.append(svgEl('rect',{x:0,y:labelY-18,width,height:38,fill:'#fffdf8'}));
   svg.append(svgEl('text',{x:10,y:labelY,class:'chart-model'},modelName(model)));
   if(mode)svg.append(svgEl('text',{x:10,y:labelY+15,class:'chart-tick chart-mode'},isHuman?c.russian:modeName(mode)));
   const en=isHuman?null:get(model,mode,'en',chartState.game),ru=get(model,mode,'ru',chartState.game);
   if(en&&ru)svg.append(svgEl('line',{x1:x(en.score),x2:x(ru.score),y1:y,y2:y,stroke:'#80cbc4','stroke-width':3}));
   for(const [r,color] of [[en,'#00796b'],[ru,isHuman?modeColors.human:'#ffa000']])if(r){const dot=svgEl('circle',{cx:x(r.score),cy:y,r:6,fill:color,stroke:'white','stroke-width':1.5,'data-model':model,'data-mode':r.mode,'data-language':r.language});pointTip(dot,`${modelName(model)}${isHuman?'':' · '+modeName(r.mode)} · ${r.language.toUpperCase()} · ${gameName(r.game)}: ${pct(r.score,ui)} · n=${r.n}`);svg.append(dot);}
   if(!en&&!ru){const message=svgEl('text',{x:compact?10:x0+10,y:y+4,class:'chart-tick chart-unavailable'},mode==='answer_only'?c.aoUnavailable:c.noResult);if(compact&&mode==='answer_only'){message.setAttribute('textLength',width-20);message.setAttribute('lengthAdjust','spacingAndGlyphs');}svg.append(message);}
  });
  paired.replaceChildren(svg);
 }
 drawLanguages();
 const chartWidths=new Map();
 chartResizeObserver=new ResizeObserver(entries=>{for(const entry of entries){const width=entry.contentRect.width;if(chartWidths.get(entry.target)===width)continue;chartWidths.set(entry.target,width);entry.target===overallPlots?drawOverall():drawLanguages();}});
 chartResizeObserver.observe(overallPlots);chartResizeObserver.observe(paired);
 const gapWrap=el('div',undefined,'gap-summary');gapWrap.append(el('h4',c.gapTitle),el('p',c.gap,'gap-unit'));const gaps=el('div',undefined,'gap-grid');
 const sorted=[...totals].sort((a,b)=>a.score-b.score),size=Math.floor(sorted.length/3),families=[[c.letterGames,['wordle','wheel_of_fortune','word_chain']],[c.semanticGames,['situation_puzzles','twenty_questions','twenty_features','alias']]];
 for(const [family,games] of families){const card=el('div',undefined,'gap-card');card.append(el('h5',family),el('p',games.map(gameName).join(' · '),'gap-games'));for(const [label,cohort,color] of [[c.weak,sorted.slice(0,size),'#ffa000'],[c.strong,sorted.slice(-size),'#004d40']]){const gap=average(cohort.map(r=>average(games.map(g=>get(r.model,r.mode,'en',g).score-get(r.model,r.mode,'ru',g).score))));const row=el('div',undefined,'gap-row');row.append(el('span',label),el('strong',`${gap>=0?'+':''}${pct(gap,ui)}`));const track=el('div',undefined,'gap-track');const bar=el('span');bar.style.width=Math.min(100,Math.abs(gap)/.2*100)+'%';bar.style.background=color;track.append(bar);card.append(row,track);}gaps.append(card);}
 gapWrap.append(gaps);cross.append(gapWrap);

 // 03 · Difficulty series preserve the distinct Wordle diagnostic formula.
 const difficulty=article(3,'difficulty','difficulty','analysis/plots/wordle.py');
 const plots=el('div',undefined,'chart-pair'),difficultyLegend=el('div',undefined,'difficulty-legend');
 const intervalLabel=el('label',undefined,'check');const check=el('input');check.type='checkbox';check.id='difficulty-ci';check.checked=chartState.intervals;check.onchange=()=>{chartState.intervals=check.checked;drawDifficulty();};intervalLabel.append(check,document.createTextNode(c.intervals));difficulty.append(modelSelector('difficulty-models','difficultyModels',drawDifficulty,true),intervalLabel,el('p',c.modeHint,'note'),difficultyLegend,plots);
 function drawDifficulty(){
  plots.replaceChildren();const models=allModels.filter(model=>chartState.difficultyModels.has(model));
  difficultyLegend.replaceChildren(legend(models.map(model=>[modelName(model),modelColor(model)])));
  for(const [key,title] of [['wordleDifficulty',gameName('wordle')],['wheelDifficulty',gameName('wheel_of_fortune')]]){
   const panel=el('div',undefined,'chart-panel');panel.append(el('h4',title+' · RU'));const wrap=el('div',undefined,'chart-scroll'),svg=svgFrame(550,330,`${title} · ${c.difficulty}`);const x0=50,x1=520,y0=20,y1=272;grid(svg,x0,x1,y0,y1,false);
   const buckets=['Easy','Medium','Hard'],x=b=>x0+25+buckets.indexOf(b)*(x1-x0-50)/2,y=v=>y1-v*(y1-y0);
   [c.easy,c.medium,c.hard].forEach((label,i)=>svg.append(svgEl('text',{x:x(buckets[i]),y:301,'text-anchor':'middle',class:'chart-tick'},label)));
   const clipId=`clip-${key}`;const defs=svgEl('defs'),clip=svgEl('clipPath',{id:clipId});clip.append(svgEl('rect',{x:x0,y:y0,width:x1-x0,height:y1-y0}));defs.append(clip);svg.append(defs);const lines=svgEl('g',{'clip-path':`url(#${clipId})`});svg.append(lines);
   for(const model of models){const color=modelColor(model);for(const mode of ['answer_only','cot','reasoning']){
    const rows=researchData[key].filter(r=>r.model===model&&r.mode===mode).sort((a,b)=>buckets.indexOf(a.bucket)-buckets.indexOf(b.bucket));if(!rows.length)continue;
    if(chartState.intervals){const points=[...rows.map(r=>`${x(r.bucket)},${y(r.score_ci_low)}`),...rows.toReversed().map(r=>`${x(r.bucket)},${y(r.score_ci_high)}`)].join(' ');lines.append(svgEl('polygon',{points,fill:color,opacity:.09}));}
    lines.append(svgEl('polyline',{points:rows.map(r=>`${x(r.bucket)},${y(r.score)}`).join(' '),fill:'none',stroke:color,'stroke-width':2.3,'stroke-dasharray':{answer_only:'none',cot:'2 4',reasoning:'7 4'}[mode]}));
    rows.forEach(r=>{const dot=svgEl('circle',{cx:x(r.bucket),cy:y(r.score),r:4.5,fill:mode==='reasoning'?'#fffdf8':color,stroke:color,'stroke-width':2});pointTip(dot,`${modelName(model)} · ${modeName(mode)} · ${r.bucket}: ${pct(r.score,ui)} · 95% CI ${pct(r.score_ci_low,ui)}–${pct(r.score_ci_high,ui)} · n=${r.n}`);lines.append(dot);});
   }}
   if(!chartState.difficultyModels.size)svg.append(svgEl('text',{x:275,y:145,'text-anchor':'middle',class:'chart-tick'},c.noData));
   wrap.append(svg);panel.append(wrap);plots.append(panel);
  }
 }
 drawDifficulty();
 const wheelSource=el('a',gameName('wheel_of_fortune')+' · '+c.source);wheelSource.href=config.repository+'/blob/main/'+researchData.sources.wheelDifficulty;difficulty.closest('article').querySelector('.source-links').append(wheelSource);

 // 04 · A native, keyboard-operable heatmap table; no raster layer.
 const cognitive=article(4,'cognition','cognitive',researchData.sources.correlations);
 const heatWrap=el('div',undefined,'chart-scroll');const heat=el('table',undefined,'heatmap');const thead=el('thead'),hr=el('tr');hr.append(el('th',c.tau));for(const game of gameIds){const th=el('th',gameName(game));th.scope='col';hr.append(th);}thead.append(hr);const tbody=el('tbody');const info=el('p',undefined,'cell-detail');info.hidden=true;info.setAttribute('role','status');
 for(const [i,skill] of skillIds.entries()){
  const tr=el('tr'),th=el('th',c.skills[i]);th.scope='row';tr.append(th);
  for(const game of gameIds){const td=el('td');const r=researchData.correlations.find(r=>r.skill===skill&&r.game===game);if(r){const b=el('button',r.tau_b.toLocaleString(ui,{minimumFractionDigits:2,maximumFractionDigits:2})+(r.significant?'*':''));const rgb=heatColor(r.tau_b);b.style.background=`rgb(${rgb.join(',')})`;b.style.color=(.299*rgb[0]+.587*rgb[1]+.114*rgb[2])/255<.55?'#fff':'#000';const description=`${c.skills[i]} × ${gameName(game)}: τ-b = ${r.tau_b.toFixed(4)} · p = ${r.p_value.toPrecision(4)}`;b.title=description;b.setAttribute('aria-label',description);b.onclick=()=>{for(const button of heat.querySelectorAll('button'))button.removeAttribute('aria-pressed');b.setAttribute('aria-pressed','true');info.hidden=false;info.textContent=description;};td.append(b);}else td.textContent='—';tr.append(td);
  }tbody.append(tr);
 }
 heat.append(thead,tbody);heatWrap.append(heat);const scale=el('div',undefined,'heatmap-scale');scale.append(el('span','0'),el('i'),el('span','+1'),el('span',c.significance));cognitive.append(heatWrap,scale,info);

 // 05 · Exact published judge agreement, including missing observations.
 const judge=article(5,'judges','judge','site/assets/poster.svg');
 const jwrap=el('div',undefined,'chart-scroll');const table=el('table',undefined,'agreement-table');
 const head=el('thead'),headRow=el('tr');for(const label of [c.game,c.condition,'GPT 5.4','Gemini 3 Flash',c.human]){const th=el('th',label);th.scope='col';headRow.append(th);}head.append(headRow);const body=el('tbody');
 for(const r of researchData.judgeAgreement){const tr=el('tr');tr.append(el('th',gameName(r.game)),el('td',r.language.toUpperCase()+(r.criterion?' · '+r.criterion:'')));tr.firstChild.scope='row';for(const key of ['gpt','gemini','human']){const value=r[key],td=el('td',value===null?'—':`${Math.round(value*100)}%`);if(value!==null){td.style.setProperty('--agreement',value);td.title=String(value);}else td.title=c.noResult;tr.append(td);}body.append(tr);}table.append(head,body);jwrap.append(table);judge.append(jwrap);
}
