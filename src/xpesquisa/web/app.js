const $ = (selector) => document.querySelector(selector);
const labels = {queued:'Na fila',running:'Em execução',completed:'Concluída',failed:'Falhou',planning:'Planejamento',search_started:'Consultando Europe PMC',search_completed:'Busca concluída',selection:'Seleção exploratória',identifier_check:'Conferência de identificadores',extraction:'Extração de trechos',synthesis_started:'Preparando síntese',synthesis:'Síntese registrada',verification:'Vínculos conferidos',provider_fallback:'Modo extrativo de contingência',interrupted:'Execução interrompida'};
let activeId = null, timer = null, current = null;
const el = (tag, text, cls) => { const node = document.createElement(tag); if(text !== undefined) node.textContent = text; if(cls) node.className = cls; return node; };
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) { const data = await response.json().catch(()=>({})); throw new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível processar o pedido. Confira os campos e tente novamente.'); }
  return response.json();
}
function message(text='') { $('#message').textContent = text; }
async function history() {
  const records = await api('/api/research');
  $('#history').replaceChildren();
  if(!records.length) $('#history').append(el('p','Nenhuma pesquisa ainda.','muted'));
  records.forEach(record => {const button=el('button',record.question,record.id===activeId?'active':''); button.append(el('small',`${labels[record.status]} · ${new Date(record.created_at).toLocaleDateString('pt-BR')}`));button.onclick=()=>open(record.id);$('#history').append(button);});
}
function tab(name) {
  document.querySelectorAll('[role=tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.tab===name)));
  ['synthesis','sources','trace'].forEach(id=>$('#'+id).hidden=id!==name);
}
document.querySelectorAll('[role=tab]').forEach(button=>{
  button.onclick=()=>tab(button.dataset.tab);
  button.onkeydown=event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const buttons=[...document.querySelectorAll('[role=tab]')];const next=buttons[(buttons.indexOf(button)+(event.key==='ArrowRight'?1:2))%3];next.focus();tab(next.dataset.tab);}};
});
function panel(title, text) {const box=el('div',undefined,'panel');box.append(el('h3',title),el('p',text));return box;}
function sourceLink(source) {const a=el('a',source.title);a.href=source.source_url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function renderSources(run) {
  const root=$('#sources');root.replaceChildren();
  const filters=el('div',undefined,'filters'), label=el('label','Filtrar documentos');label.htmlFor='source-filter';
  const filter=el('select');filter.id='source-filter';
  [['all','Todos'],['abstract','Com abstract'],['review','Revisões (metadados da fonte)'],['pending','Identidade não reconfirmada']].forEach(([value,text])=>{const option=el('option',text);option.value=value;filter.append(option);});
  filters.append(label,filter);root.append(filters);const list=el('div');root.append(list);
  function fill(){list.replaceChildren();const sources=run.sources.filter(s=>filter.value==='all'||(filter.value==='abstract'&&s.abstract)||(filter.value==='review'&&s.study_types.some(t=>/review|meta.analysis/i.test(t)))||(filter.value==='pending'&&s.identifier_status!=='matched'));
    if(!sources.length)list.append(el('p','Nenhum registro neste filtro.','muted'));
    sources.forEach(s=>{const card=el('article',undefined,'source-card');card.id='source-'+s.id;card.append(el('span',`${s.source} · ${s.publication_date||'Data não informada'}`,'badge'));const heading=el('h3');heading.append(sourceLink(s));card.append(heading,el('p',s.authors.join(', ')||'Autores não informados'));
      card.append(el('p',`PMID: ${s.pmid||'não informado'} · DOI: ${s.doi||'não informado'}`));card.append(el('p',`Tipos informados pela base: ${s.study_types.join(', ')||'não informados'}`));
      const statuses={matched:'Identificador e metadados reconfirmados na mesma base',mismatch:'Divergência de identidade — excluída da síntese',unavailable:'Identidade não reconfirmada: consulta indisponível',not_checked:'Identidade ainda não conferida'};
      card.append(el('span',statuses[s.identifier_status],'badge '+(s.identifier_status==='matched'?'':'pending')),el('p','País da população: não determinado. Aplicabilidade ao Brasil: não avaliada.'));
      const details=el('details');details.append(el('summary','Ler abstract recuperado'),el('blockquote',s.abstract||'Abstract não disponível.'));card.append(details);list.append(card);});
  }filter.onchange=fill;fill();
}
function render(run) {
  current=run;$('#empty').hidden=true;$('#result').hidden=false;$('#result-title').textContent=run.request.question;
  $('#export').href=`/api/research/${run.id}/export`;
  const last=run.events.at(-1);$('#progress').textContent=`${labels[run.status]}${last?.stage!==run.status?' · '+(labels[last?.stage]||'Aguardando início'):''} · ${new Date(run.created_at).toLocaleString('pt-BR')}`;
  $('#stats').replaceChildren();[[run.sources.length,'fontes'],[run.evidence.length,'trechos'],[run.claims.length,'afirmações']].forEach(([value,text])=>{const item=el('div');item.append(el('strong',value),el('span',text));$('#stats').append(item);});
  const root=$('#synthesis');root.replaceChildren();
  if(run.error)root.append(panel('Pesquisa não concluída',run.error));
  if(run.summary)root.append(panel('Resposta curta',run.summary));
  if(run.plan)root.append(panel('Estratégia executada',`${run.plan.interpretation}\nBusca: ${run.plan.query}`));
  if(run.claims.length)root.append(el('h3',run.provider==='extractive'?'Achados textuais — síntese extrativa':'Rascunhos de síntese — revisão humana necessária'));
  run.claims.forEach((claim,index)=>{
    const box=el('article',undefined,'claim');box.append(el('span',`AFIRMAÇÃO ${String(index+1).padStart(2,'0')}`,'eyebrow'),el('blockquote',claim.text));
    const citedSources=[...new Set(claim.evidence_ids.map(id=>run.evidence.find(e=>e.id===id).source_id))];
    citedSources.forEach(id=>{const source=run.sources.find(s=>s.id===id);const citation=el('p');citation.append(sourceLink(source));box.append(citation,el('p',`${source.publication_date||'Sem data'} · ${source.study_types.join(', ')||'Tipo não informado'} · População não extraída`,'muted'));});
    box.append(el('span',claim.kind==='excerpt'?'Trecho literal conferido':'Rascunho gerado por modelo','badge'),el('span','Suporte clínico não avaliado','badge pending'));
    const detail=el('details');detail.append(el('summary','Abrir caminho: afirmação → evidência → fonte'));
    claim.evidence_ids.forEach(id=>{const evidence=run.evidence.find(e=>e.id===id),source=run.sources.find(s=>s.id===evidence.source_id);const p=el('p');p.append(sourceLink(source));detail.append(p,el('p',`Trecho do abstract, caracteres ${evidence.excerpt_start}–${evidence.excerpt_end}. Relação: contexto. Risco de viés: não avaliado.`));if(claim.kind!=='excerpt')detail.append(el('blockquote',evidence.supporting_excerpt));});box.append(detail);root.append(box);
  });
  if(run.status==='completed'){
    root.append(panel('Evidência brasileira e aplicabilidade','A busca não incluiu uma fonte brasileira dedicada. País da população e aplicabilidade clínica não foram avaliados; isso não significa ausência de evidência brasileira.'));
    root.append(panel('Onde os estudos discordam','Ainda não avaliado. O módulo de busca ativa de evidência contrária faz parte da próxima etapa do projeto.'));
    const limitations=panel('Limitações e o que não conseguimos verificar','');const list=el('ul');run.limitations.forEach(t=>list.append(el('li',t)));limitations.append(list);root.append(limitations);
  }
  renderSources(run);
  const trace=$('#trace');trace.replaceChildren(panel('Registro da pesquisa',`Pipeline ${run.pipeline_version} · Schema ${run.schema_version} · Provider ${run.provider}${run.model?' / '+run.model:''}. Os hashes identificam respostas consultadas; não provam validade científica.`));
  run.events.forEach(event=>{const details=el('details',undefined,'trace-event'),summary=el('summary');summary.append(el('time',new Date(event.timestamp).toLocaleTimeString('pt-BR')),el('span',labels[event.stage]||event.stage));details.append(summary,el('pre',JSON.stringify(event.detail,null,2)));trace.append(details);});
}
async function poll(id) {
  try { const run=await api('/api/research/'+id);if(activeId!==id)return;render(run);if(['queued','running'].includes(run.status))timer=setTimeout(()=>poll(id),1500);else await history(); }
  catch(error){if(activeId===id)message(error.message+' Reabra a pesquisa no histórico para tentar novamente.');}
}
async function open(id) {clearTimeout(timer);activeId=id;message();tab('synthesis');await poll(id);await history().catch(e=>message(e.message));}
$('#research-form').onsubmit=async event=>{
  event.preventDefault();message();$('#submit').disabled=true;
  try {const run=await api('/api/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('#question').value,query:$('#query').value||null,limit:Number($('#limit').value)})});await open(run.id);$('#result').scrollIntoView({behavior:'smooth',block:'start'});}
  catch(error){message(error.message);}finally{$('#submit').disabled=false;}
};
$('#example').onclick=()=>{$('#question').value='Qual é a evidência atual sobre elastografia hepática para avaliação de fibrose?';$('#question').focus();};
$('#new').onclick=()=>{clearTimeout(timer);activeId=null;current=null;$('#result').hidden=true;$('#empty').hidden=false;$('#question').value='';$('#query').value='';message();$('#question').focus();history().catch(e=>message(e.message));};
history().catch(e=>message(e.message));
