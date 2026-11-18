/* Retena MVP - front-end sem dependências externas (funciona offline); todos os dados vêm da API sobre o Oracle. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  const NUM = new Intl.NumberFormat('pt-BR');
  const PCT = v => v == null ? '–' : (100 * v).toLocaleString('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + '%';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const dataHora = s => s ? new Date(s).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '–';
  const data = s => s ? new Date(s).toLocaleDateString('pt-BR') : '–';
  const STATUS = { PENDENTE: 'Pendente', CONTATADO: 'Plano combinado', REATIVADO: 'Reativado', SEM_RETORNO: 'Sem resposta', CANCELAMENTO: 'Vai cancelar', IGNORAR: 'Ignorar' };
  const RES = {
    REATIVADO: ['Reativado', 'voltou a estudar / combinou retorno imediato'],
    PLANO_COMBINADO: ['Plano combinado', 'respondeu; retoma em data acordada'],
    SEM_RESPOSTA: ['Sem resposta', 'continua na fila para nova tentativa'],
    VAI_CANCELAR: ['Vai cancelar', 'encaminhar à retenção financeira'],
  };
  const CANAIS = { WHATSAPP: 'WhatsApp', TELEFONE: 'Telefone', EMAIL: 'E-mail', LMS: 'Mensagem no LMS', PRESENCIAL: 'Presencial/polo' };
  const corFaixa = f => f === 'Alto' ? 'var(--coral)' : f === 'Médio' ? 'var(--ambar)' : 'var(--verde)';

  async function api(caminho, opcoes = {}) {
    const r = await fetch(caminho, { headers: { 'Content-Type': 'application/json' }, ...opcoes });
    let corpo = null;
    try { corpo = await r.json(); } catch (e) { /* resposta sem JSON */ }
    if (!r.ok) {
      const msg = (corpo && (corpo.detail || corpo.erro)) || `HTTP ${r.status}`;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)); err.status = r.status; throw err;
    }
    return corpo;
  }

  // ------------------------------------------------------------------ status do banco
  let SAUDE = null;
  async function carregarSaude() {
    const el = $('#status');
    try {
      SAUDE = await api('/api/saude');
      el.className = 'status ok';
      el.querySelector('span').textContent = `Oracle conectado · ${SAUDE.alunos} alunos · scoring ${dataHora(SAUDE.dt_scoring)}`;
      el.title = SAUDE.banco;
      $('#offline-aviso').hidden = true;
      return true;
    } catch (e) {
      el.className = 'status erro';
      el.querySelector('span').textContent = 'Oracle indisponível';
      $('#offline-msg').textContent = e.message;
      $('#offline-aviso').hidden = false;
      return false;
    }
  }

  // ------------------------------------------------------------------ navegação
  const ABAS = ['fila', 'diretoria', 'tecnico'];
  function irPara() {
    const h = (location.hash || '#fila').slice(1).split('?')[0];
    const aba = ABAS.includes(h) ? h : 'fila';
    $$('.visao').forEach(s => { s.hidden = s.dataset.visao !== aba; });
    $$('.abas a').forEach(a => { if (a.dataset.aba !== aba) a.removeAttribute('aria-current'); else a.setAttribute('aria-current', 'page'); });
    if (aba === 'fila') carregarFila();
    if (aba === 'diretoria') carregarDiretoria();
    if (aba === 'tecnico') carregarTecnico();
    const q = new URLSearchParams(location.hash.split('?')[1] || '');
    if (q.get('aluno')) abrirAluno(q.get('aluno'));
  }
  window.addEventListener('hashchange', irPara);

  // ------------------------------------------------------------------ fila
  let escopo = 'fila';
  async function carregarFila() {
    const corpo = $('#fila-corpo');
    const faixa = $('#f-faixa').value;
    try {
      const d = await api(`/api/fila?escopo=${escopo}${faixa ? '&faixa=' + encodeURIComponent(faixa) : ''}&limite=300`);
      $('#c-fila').textContent = d.contagem.na_fila; $('#c-tratados').textContent = d.contagem.tratados; $('#c-todos').textContent = d.contagem.todos;
      if (SAUDE) $('#fila-meta').innerHTML = `Corte dos dados: <b>${data(SAUDE.dt_corte)}</b><br>Último scoring OML: <b>${dataHora(SAUDE.dt_scoring)}</b><br>Contatos gravados no banco: <b>${SAUDE.contatos}</b>`;
      if (!d.alunos.length) { corpo.innerHTML = `<tr><td colspan="7" class="vazio">${escopo === 'tratados' ? 'Nenhum contato registrado ainda. Abra um aluno da fila e registre o resultado.' : 'Ninguém aqui.'}</td></tr>`; return; }
      const GRUPOS = { 'Agir agora': 'risco alto e último acesso há até 30 dias: ainda dá para segurar', 'Atenção': 'risco médio: ritmo caindo', 'Resgate': 'risco alto e mais de 30 dias em silêncio: tentativa de reativação', 'Monitorar': 'risco baixo' };
      let grupoAnt = null;
      corpo.innerHTML = d.alunos.map((a, i) => {
        let sep = '';
        if (a.grupo_fila !== grupoAnt) {
          const n = d.alunos.filter(x => x.grupo_fila === a.grupo_fila).length;
          sep = `<tr class="grupo"><td colspan="7"><b>${esc(a.grupo_fila)}</b> · ${n} aluno(s) · ${esc(GRUPOS[a.grupo_fila] || '')}</td></tr>`;
          grupoAnt = a.grupo_fila;
        }
        const cap = a.capitulo_max_fase ? `cap. ${a.capitulo_max_fase}` : 'nenhum capítulo aberto';
        const f1 = a.fatores[0] ? a.fatores[0].texto : '';
        const tent = a.tentativas ? `<span class="sub">${a.tentativas} contato(s)</span>` : '';
        return sep + `<tr tabindex="0" data-aluno="${esc(a.nome)}">
          <td>${escopo === 'fila' ? i + 1 : a.posicao}</td>
          <td><span class="aluno-nome">${esc(a.nome)}</span><span class="sub">${esc(a.acao_sugerida || '')}</span></td>
          <td>${esc(a.nome_fase || '–')}<span class="sub">${cap}</span></td>
          <td class="num">${a.recencia_dias ?? '–'} d</td>
          <td><div class="barra"><span class="t"><i style="width:${Math.round(100 * a.prob_inativo_21d)}%;background:${corFaixa(a.faixa_risco)}"></i></span><b>${PCT(a.prob_inativo_21d)}</b></div><span class="chip f-${esc(a.faixa_risco)}">${esc(a.faixa_risco)}</span></td>
          <td class="porque">${esc(f1)}</td>
          <td><span class="chip s-${esc(a.status_atendimento)}">${STATUS[a.status_atendimento] || a.status_atendimento}</span>${tent}</td></tr>`;
      }).join('');
    } catch (e) {
      corpo.innerHTML = `<tr><td colspan="7" class="vazio">Não foi possível ler a fila do Oracle: ${esc(e.message)}</td></tr>`;
    }
  }
  $('#seg-escopo').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b) return;
    escopo = b.dataset.escopo;
    $$('#seg-escopo button').forEach(x => x.setAttribute('aria-pressed', x === b));
    carregarFila();
  });
  $('#f-faixa').addEventListener('change', carregarFila);
  $('#fila-corpo').addEventListener('click', ev => { const tr = ev.target.closest('tr[data-aluno]'); if (tr) abrirAluno(tr.dataset.aluno); });
  $('#fila-corpo').addEventListener('keydown', ev => { if (ev.key === 'Enter') { const tr = ev.target.closest('tr[data-aluno]'); if (tr) abrirAluno(tr.dataset.aluno); } });

  // ------------------------------------------------------------------ painel do aluno
  const gaveta = $('#gaveta'), veu = $('#veu');
  let ultimoFoco = null;
  function fecharAluno() {
    gaveta.classList.remove('aberta'); gaveta.setAttribute('aria-hidden', 'true'); veu.hidden = true;
    if (ultimoFoco) ultimoFoco.focus();
  }
  $('#g-fechar').addEventListener('click', fecharAluno);
  veu.addEventListener('click', fecharAluno);
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && gaveta.classList.contains('aberta')) fecharAluno(); });

  function sparkline(semanas) {
    const max = Math.max(1, ...semanas.map(s => s.eventos));
    const w = 560, h = 70, n = semanas.length, bw = w / n;
    const barras = semanas.map((s, i) => {
      const bh = Math.max(2, (s.eventos / max) * (h - 14));
      return `<rect x="${i * bw + 3}" y="${h - bh}" width="${bw - 6}" height="${bh}" rx="3" fill="${s.eventos ? 'var(--verde)' : '#DCE3EB'}"><title>Semana de ${data(s.semana + 'T12:00')}: ${s.eventos} ações</title></rect>` +
        (s.eventos ? `<text x="${i * bw + bw / 2}" y="${h - bh - 3}" text-anchor="middle" font-size="10" fill="#3A4A5C">${s.eventos}</text>` : '');
    }).join('');
    return `<svg class="spark" viewBox="0 0 ${w} ${h + 2}" role="img" aria-label="Ações no LMS por semana, últimas ${n} semanas">${barras}</svg>
      <div class="spark-leg"><span>${data(semanas[0].semana + 'T12:00')}</span><span>semana do corte (${data(semanas[n - 1].semana + 'T12:00')})</span></div>`;
  }

  function mensagemSugerida(a, resp) {
    const quem = resp ? resp.split(' ')[0] : '[seu nome]';
    const fase = a.num_fase_atual ? `da Fase ${a.num_fase_atual}` : 'do curso';
    const cap = a.capitulo_max_fase ? ` no capítulo ${a.capitulo_max_fase}` : '';
    if (a.recencia_dias > 14)
      return `Oi! Aqui é ${quem}, da tutoria do seu curso. Faz ${a.recencia_dias} dias que você não entra na plataforma e eu queria saber se está tudo bem. Se alguma parte ${fase}${cap} travou, te mando um resumo e a gente retoma juntos em 20 minutos. Qual o melhor horário pra falar hoje, entre 19h e 22h?`;
    return `Oi! Aqui é ${quem}, da tutoria. Vi que seu ritmo ${fase} caiu nas últimas semanas${cap}. Quer que eu te mande um resumo do que vem pela frente e um plano curto para esta semana? Posso te chamar entre 19h e 22h.`;
  }

  async function abrirAluno(nome) {
    ultimoFoco = document.activeElement;
    gaveta.classList.add('aberta'); gaveta.setAttribute('aria-hidden', 'false'); veu.hidden = false;
    const box = $('#g-conteudo');
    box.innerHTML = `<div class="g-topo"><h2 id="g-titulo">${esc(nome)}</h2><p>Lendo do Oracle…</p></div>`;
    let a;
    try { a = await api('/api/alunos/' + encodeURIComponent(nome)); }
    catch (e) { box.innerHTML = `<div class="g-topo"><h2 id="g-titulo">${esc(nome)}</h2><p class="msg erro">${esc(e.message)}</p></div>`; return; }
    let resp = '';
    try { resp = localStorage.getItem('retena.mvp.responsavel') || ''; } catch (e) { /* sem armazenamento local */ }
    box.innerHTML = `
      <div class="g-topo">
        <h2 id="g-titulo">${esc(a.nome)}</h2>
        <div class="chips"><span class="chip f-${esc(a.faixa_risco)}">Risco ${esc(a.faixa_risco)}</span>
          <span class="chip s-${esc(a.status_atendimento)}" id="g-status">${STATUS[a.status_atendimento] || a.status_atendimento}</span>
          <span class="chip s-PENDENTE">${esc(a.nome_fase || '')}${a.capitulo_max_fase ? ' · cap. ' + a.capitulo_max_fase : ''}</span></div>
      </div>
      <div class="g-bloco">
        <div class="g-num">
          <div><span>Risco 21 dias (RF)</span><b>${PCT(a.prob_inativo_21d)}</b></div>
          <div><span>Segunda opinião (GLM)</span><b>${PCT(a.prob_inativo_21d_glm)}</b></div>
          <div><span>Evasão na fase</span><b>${PCT(a.prob_evasao_fase)}</b></div>
        </div>
        <div class="live"><button class="btn sec" id="btn-live" type="button">Recalcular no Oracle agora</button><button class="btn sec" id="btn-ese" type="button">E se ele voltar esta semana?</button><span class="out" id="live-out" aria-live="polite"></span></div>
      </div>
      <div class="g-bloco">
        <h3>Por que está na fila</h3>
        <ul class="fatores">${a.fatores.map(f => `<li>${esc(f.texto)}</li>`).join('') || '<li>sem detalhes</li>'}</ul>
        <p class="nota" style="margin-top:6px">Os 3 fatores de maior peso para este aluno, explicados pelo próprio modelo (<code>PREDICTION_DETAILS</code>).</p>
      </div>
      <div class="g-bloco"><h3>Ações no LMS por semana</h3>${sparkline(a.atividade_semanal)}</div>
      <div class="g-bloco">
        <h3>O que fazer</h3>
        <p style="margin:2px 0 8px">${esc(a.acao_sugerida || '')} · melhor janela: <b>19h–22h, terça ou quarta</b> (pico de uso da turma).</p>
        <div class="mensagem" id="msg-sug">${esc(mensagemSugerida(a, resp))}</div>
        <div class="live"><button class="btn sec" id="btn-copiar" type="button">Copiar mensagem</button><span class="out" id="copiar-out"></span></div>
      </div>
      <div class="g-bloco">
        <h3>Registrar o resultado do contato</h3>
        <div class="res-btns" role="group" aria-label="Resultado do contato">
          ${Object.entries(RES).map(([k, [t, s]]) => `<button type="button" data-r="${k}" aria-pressed="false">${t}<small>${s}</small></button>`).join('')}
        </div>
        <div class="form-linha">
          <label>Canal<select id="r-canal">${Object.entries(CANAIS).map(([k, t]) => `<option value="${k}">${t}</option>`).join('')}</select></label>
          <label>Responsável<input id="r-resp" maxlength="60" placeholder="ex.: Mariana (tutoria)" value="${esc(resp)}"></label>
        </div>
        <label class="bl">Observação (opcional)<textarea id="r-obs" maxlength="400" placeholder="ex.: travou no cap. 2; mandei o resumo em PDF; retoma quarta"></textarea></label>
        <div class="live"><button class="primario" id="btn-gravar" type="button" disabled>Gravar no Oracle</button><span class="out" id="gravar-out" aria-live="polite">Escolha um resultado.</span></div>
        <div id="gravado"></div>
      </div>
      <div class="g-bloco"><h3>Histórico de contatos <small style="font-weight:400;color:var(--neutra)">CONTATO_RESULTADO</small></h3><ul class="hist" id="hist">${historico(a.contatos)}</ul></div>`;

    let escolhido = null;
    $$('.res-btns button', box).forEach(b => b.addEventListener('click', () => {
      escolhido = b.dataset.r;
      $$('.res-btns button', box).forEach(x => x.setAttribute('aria-pressed', x === b));
      $('#btn-gravar').disabled = false; $('#gravar-out').textContent = '';
    }));
    $('#r-resp').addEventListener('input', ev => { $('#msg-sug').textContent = mensagemSugerida(a, ev.target.value); });
    $('#btn-copiar').addEventListener('click', async () => {
      try { await navigator.clipboard.writeText($('#msg-sug').textContent); $('#copiar-out').textContent = 'Copiada.'; }
      catch (e) { $('#copiar-out').textContent = 'Selecione e copie manualmente.'; }
    });
    const live = async corpoSim => {
      const out = $('#live-out'); out.textContent = 'calculando no banco…';
      try {
        const p = await api(`/api/alunos/${encodeURIComponent(a.nome)}/predicao`, { method: 'POST', body: JSON.stringify(corpoSim || {}) });
        out.innerHTML = corpoSim
          ? `Se voltar esta semana: <b>${PCT(p.prob_rf)}</b> (hoje ${PCT(a.prob_inativo_21d)}) · ${p.ms} ms`
          : `Agora, no Oracle: <b>${PCT(p.prob_rf)}</b> (GLM ${PCT(p.prob_glm)}) · ${p.ms} ms`;
      } catch (e) { out.textContent = e.message; }
    };
    $('#btn-live').addEventListener('click', () => live(null));
    $('#btn-ese').addEventListener('click', () => live({ recencia_dias: 1, eventos_7d: Math.max(30, a.eventos_7d || 0), dias_ativos_28d: Math.min(28, (a.dias_ativos_28d || 0) + 3) }));
    $('#btn-gravar').addEventListener('click', async () => {
      const btn = $('#btn-gravar'); btn.disabled = true; $('#gravar-out').textContent = 'gravando no Oracle…';
      const resp2 = $('#r-resp').value.trim();
      try { localStorage.setItem('retena.mvp.responsavel', resp2); } catch (e) { /* ok */ }
      try {
        const r = await api('/api/contatos', { method: 'POST', body: JSON.stringify({ aluno: a.nome, resultado: escolhido, canal: $('#r-canal').value, responsavel: resp2 || null, observacao: $('#r-obs').value.trim() || null }) });
        $('#gravar-out').textContent = '';
        $('#gravado').innerHTML = `<div class="gravado"><b>Gravado no Oracle.</b> Contato nº ${r.id_contato} em <code>CONTATO_RESULTADO</code> · status da fila → <b>${STATUS[r.novo_status] || r.novo_status}</b> · ${dataHora(r.registro.dt_contato)}<br>Conferir: <code>${esc(r.sql_verificacao)}</code></div>`;
        $('#g-status').className = 'chip s-' + r.novo_status; $('#g-status').textContent = STATUS[r.novo_status] || r.novo_status;
        const novo = await api('/api/alunos/' + encodeURIComponent(a.nome));
        $('#hist').innerHTML = historico(novo.contatos);
        carregarSaude(); carregarFila();
      } catch (e) { $('#gravar-out').textContent = 'Erro: ' + e.message; }
      finally { btn.disabled = false; }
    });
    $('#g-fechar').focus();
  }
  function historico(lista) {
    if (!lista || !lista.length) return '<li style="color:var(--neutra)">Nenhum contato registrado para este aluno.</li>';
    return lista.map(c => `<li><b>${RES[c.resultado] ? RES[c.resultado][0] : c.resultado}</b> · ${CANAIS[c.canal] || c.canal} · ${dataHora(c.dt_contato)}${c.responsavel ? ' · ' + esc(c.responsavel) : ''}<span class="sub">nº ${c.id_contato} · risco no contato ${PCT(c.prob_no_contato)} (${esc(c.faixa_no_contato || '')})${c.observacao ? ' · ' + esc(c.observacao) : ''}</span></li>`).join('');
  }

  // ------------------------------------------------------------------ diretoria
  let ultimoResumo = null;
  async function carregarDiretoria(destacar) {
    try {
      const d = await api('/api/diretoria');
      const r = d.resumo;
      if (document.activeElement !== $('#ticket')) $('#ticket').value = r.ticket;
      const kpis = [
        ['c-coral', 'Alunos para chamar esta semana', NUM.format(r.na_fila), `${r.alunos_alto} em alto risco + ${r.alunos_medio} em médio, ainda sem contato resolvido`, 'na_fila'],
        ['c-ambar', 'Receita anual em risco', BRL.format(r.receita_anual_em_risco), `${r.alunos_alto} alunos de alto risco × ${BRL.format(r.ticket)} × ${r.meses} meses`, 'receita_anual_em_risco'],
        ['c-azul', 'Contatos registrados', NUM.format(r.contatos_registrados), `${r.alunos_contatados} aluno(s) contatado(s) · gravados em CONTATO_RESULTADO`, 'contatos_registrados'],
        ['c-verde', 'Receita preservada (estimativa)', BRL.format(r.receita_preservada_estimada), `${r.reativados} aluno(s) reativado(s) × ${BRL.format(r.ticket)} × ${r.meses} meses`, 'receita_preservada_estimada'],
      ];
      $('#kpis').innerHTML = kpis.map(([c, rot, v, s, k]) => `<div class="kpi ${c}" data-k="${k}"><div class="r">${rot}</div><div class="v">${v}</div><div class="s">${esc(s)}</div></div>`).join('');
      if (ultimoResumo && destacar !== false) kpis.forEach(k => { if (ultimoResumo[k[4]] !== r[k[4]]) $(`.kpi[data-k="${k[4]}"]`).classList.add('flash'); });
      ultimoResumo = r;
      const tot = r.alunos_contatados || 0;
      const itens = [['Reativado', r.reativados, 'var(--verde)'], ['Plano combinado', r.planos, 'var(--azul2)'], ['Sem resposta', r.sem_resposta, 'var(--ambar)'], ['Vai cancelar', r.vai_cancelar, 'var(--coral)']];
      $('#dir-resultados').innerHTML = (tot ? '' : '<p class="nota" style="margin:0 0 6px">Nenhum contato registrado ainda. Registre o resultado na visão da coordenação.</p>') +
        itens.map(([t, n, c]) => `<div class="hbar"><span>${t}</span><span class="t"><i style="width:${tot ? 100 * n / tot : 0}%;background:${c}"></i></span><b>${n}</b></div>`).join('') +
        `<p class="nota">Perda esperada no ano (Σ probabilidades × ticket × ${r.meses}): <b>${BRL.format(r.perda_esperada_anual)}</b>.</p>`;
      const pct = r.meta_reativacoes ? Math.min(100, 100 * r.reativados_alto / r.meta_reativacoes) : 0;
      $('#dir-meta').innerHTML = `<p style="margin:0">Meta: reengajar <b>${r.meta_pct}%</b> dos ${r.alunos_alto} alunos de alto risco em 30 dias = <b>${r.meta_reativacoes} reativações</b>.</p>
        <div class="progresso" role="progressbar" aria-valuemin="0" aria-valuemax="${r.meta_reativacoes}" aria-valuenow="${r.reativados_alto}"><i style="width:${pct}%"></i></div>
        <p style="margin:0"><b>${r.reativados_alto}</b> de ${r.meta_reativacoes} (${pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%). Ao bater a meta, o piloto converte em contrato anual.</p>`;
      const maxF = Math.max(1, ...d.risco_por_fase.map(f => f.alunos));
      $('#dir-fases').innerHTML = d.risco_por_fase.map(f => `<div class="hbar"><span>Fase ${f.fase} · ${f.alunos} alunos</span><span class="t" style="width:${100 * f.alunos / maxF}%"><i style="width:${100 * f.alto / f.alunos}%;background:var(--coral)"></i><i style="width:${100 * f.medio / f.alunos}%;background:var(--ambar)"></i></span><b>${f.alto + f.medio}</b></div>`).join('') +
        '<p class="nota">Vermelho = alto risco, âmbar = médio; número à direita = alunos em risco na fase.</p>';
    } catch (e) { $('#kpis').innerHTML = `<p class="msg erro">${esc(e.message)}</p>`; }
  }
  $('#form-ticket').addEventListener('submit', async ev => {
    ev.preventDefault();
    const v = Number($('#ticket').value);
    try { await api('/api/parametros', { method: 'PUT', body: JSON.stringify({ ticket_mensal: v }) }); $('#ticket-msg').textContent = `Gravado: ticket ${BRL.format(v)} em PARAMETRO_IES.`; carregarDiretoria(); }
    catch (e) { $('#ticket-msg').textContent = 'Erro: ' + e.message; }
  });

  // ------------------------------------------------------------------ técnico
  async function carregarTecnico() {
    await carregarSaude();
    if (!SAUDE) return;
    const s = SAUDE;
    $('#tec-banco').innerHTML = `<h2>Banco e modelos <small>${esc(s.usuario)}@${esc(s.dsn)}</small></h2>
      <dl class="kv"><dt>Banco</dt><dd>${esc(s.banco)}</dd><dt>Eventos do LMS</dt><dd>${NUM.format(s.eventos)} linhas em EVENTOS_LMS</dd>
      <dt>Alunos pontuados</dt><dd>${s.alunos} em RISCO_ALUNO_SNAPSHOT</dd><dt>Contatos gravados</dt><dd>${s.contatos} em CONTATO_RESULTADO</dd>
      <dt>Latência da consulta</dt><dd>${s.latencia_ms} ms</dd></dl>
      <table class="res"><thead><tr><th>Modelo OML</th><th>Algoritmo</th><th>AUC (teste)</th><th>Lift top 20%</th></tr></thead><tbody>
      ${s.modelos.map(m => `<tr><td>${esc(m.model_name)}</td><td>${esc(m.algorithm)}</td><td>${m.auc ?? '–'}</td><td>${m.lift_top20 ? m.lift_top20 + '×' : '–'}</td></tr>`).join('')}</tbody></table>
      <p class="nota">Validação temporal: treino até maio/2026, teste em cortes a partir de 01/06/2026 (métricas gravadas em <code>AVALIACAO_MODELOS</code> por <code>DBMS_DATA_MINING.COMPUTE_ROC</code>).</p>`;
    const j = s.job || {};
    $('#tec-job').innerHTML = `<dl class="kv"><dt>Job</dt><dd>${esc(j.job_name || '–')} (${esc(j.state || '–')})</dd><dt>Agenda</dt><dd>${esc(j.repeat_interval || '–')}</dd>
      <dt>Última execução</dt><dd>${dataHora(j.last_start)}</dd><dt>Próxima</dt><dd>${dataHora(j.next_run)}</dd><dt>Execuções</dt><dd>${j.run_count ?? '–'}</dd></dl>`;
    carregarExecucoes();
    if (!$('#provas').children.length) {
      const provas = await api('/api/sql');
      $('#provas').innerHTML = provas.map(p => `<button type="button" data-p="${p.id}" aria-pressed="false">${esc(p.titulo)}</button>`).join('');
    }
  }
  async function carregarExecucoes() {
    try {
      const ex = await api('/api/scoring/execucoes');
      $('#tec-execucoes').innerHTML = ex.length ? `<table class="res" style="margin-top:10px"><thead><tr><th>Execução</th><th>Início (relógio do banco)</th><th>Duração</th><th>Status</th></tr></thead><tbody>${ex.map(e => `<tr><td>${e.log_id}</td><td>${esc(e.inicio)}</td><td>${Math.round(e.segundos)} s</td><td>${esc(e.status)}</td></tr>`).join('')}</tbody></table>` : '';
    } catch (e) { /* sem histórico */ }
  }
  $('#btn-scoring').addEventListener('click', async () => {
    const b = $('#btn-scoring'), m = $('#scoring-msg'); b.disabled = true;
    const t0 = Date.now(); m.className = 'msg'; m.textContent = 'DBMS_SCHEDULER.RUN_JOB em execução: re-pontuando todos os alunos com o Random Forest in-database…';
    const tic = setInterval(() => { m.textContent = `Pontuando no Oracle… ${Math.round((Date.now() - t0) / 1000)} s`; }, 1000);
    try {
      const r = await api('/api/scoring', { method: 'POST' });
      m.className = 'msg ok'; m.textContent = `Concluído em ${r.segundos} s: ${r.alunos} alunos re-pontuados (${r.alto} alto, ${r.medio} médio). Novo carimbo: ${dataHora(r.dt_scoring)}. Status de atendimento preservado pelo MERGE.`;
      await carregarTecnico();
    } catch (e) { m.className = 'msg erro'; m.textContent = e.message; }
    finally { clearInterval(tic); b.disabled = false; }
  });
  const KW = /\b(SELECT|FROM|WHERE|ORDER BY|GROUP BY|FETCH FIRST|ROWS ONLY|JOIN|AS|AND|USING|ROUND|COUNT|PREDICTION_PROBABILITY|JSON_SERIALIZE|RETURNING|TO_CHAR|DESC)\b/g;
  $('#provas').addEventListener('click', async ev => {
    const b = ev.target.closest('button'); if (!b) return;
    $$('#provas button').forEach(x => x.setAttribute('aria-pressed', x === b));
    const out = $('#prova-saida'); out.innerHTML = '<p class="nota">executando no Oracle…</p>';
    try {
      const r = await api('/api/sql/' + b.dataset.p);
      const cols = r.linhas.length ? Object.keys(r.linhas[0]) : [];
      out.innerHTML = `<pre class="sql">${esc(r.sql).replace(KW, '<span class="kw">$1</span>')}</pre>
        <p class="nota" style="margin:0 0 6px">${r.linhas.length} linha(s) em ${r.ms} ms</p>
        ${cols.length ? `<div class="tabela-wrap"><table class="res"><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${r.linhas.map(l => `<tr>${cols.map(c => `<td>${esc(l[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p class="nota">Sem linhas (registre um contato na fila para ver o resultado aqui).</p>'}`;
    } catch (e) { out.innerHTML = `<p class="msg erro">${esc(e.message)}</p>`; }
  });

  // ------------------------------------------------------------------ início
  carregarSaude().then(irPara);
  setInterval(carregarSaude, 60000);
})();
