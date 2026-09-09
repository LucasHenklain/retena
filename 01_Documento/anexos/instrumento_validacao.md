# Instrumento de Validação — Entrevistas e Formulário

> Uso: a equipe deve aplicar este roteiro com 5 a 8 potenciais usuários (coordenadores de curso EAD/híbrido, tutores, gestores acadêmicos e alunos) e registrar as respostas na planilha `registro_entrevistas.csv`. Os campos marcados **[A PREENCHER PELA EQUIPE]** no documento principal devem ser completados com as respostas reais. Não preencha com respostas hipotéticas.

## 1. Perfis a entrevistar (mínimo)

| # | Perfil | Por quê | Meta |
|---|--------|---------|------|
| 1 | Coordenador(a) de curso EAD ou híbrido (IES privada) | Compradora/usuária principal; dona da meta de retenção | 3 entrevistas |
| 2 | Tutor(a) / professor(a) mediador(a) | Executa as intervenções; sente a sobrecarga | 2 entrevistas |
| 3 | Gestor(a) acadêmico / diretor(a) de operações EAD | Decide orçamento; mede evasão financeiramente | 1 entrevista |
| 4 | Aluno(a) EAD adulto(a) trabalhador(a) | Beneficiário final; valida percepção das intervenções | 2 entrevistas |

## 2. Roteiro de entrevista semiestruturada (30 min)

**Abertura (3 min)** — apresentar objetivo (entender como a instituição acompanha o engajamento e a evasão), garantir anonimato, pedir permissão para anotar.

**Bloco A — Contexto e dor (8 min)**
1. Como você descobre hoje que um aluno está "sumindo" do curso? Quanto tempo depois do primeiro sinal?
2. Quais indicadores você acompanha (acessos, notas, entregas)? Com que frequência? Em que ferramenta?
3. Conte a última vez que perdeu um aluno que "dava para salvar". O que faltou?
4. Quantos alunos por tutor/coordenador? Quanto tempo por semana vai para acompanhamento manual?

**Bloco B — Processo atual e alternativas (7 min)**
5. Existe algum relatório do LMS (Moodle/Canvas/Blackboard/plataforma própria) que você usa? Ele chega a tempo?
6. Já testaram alguma solução de analytics/retenção? Por que não ficou?
7. Como decidem quem contatar primeiro quando há muitos alunos inativos?

**Bloco C — Reação à proposta (8 min)** — mostrar o protótipo (dashboard) por 2 minutos, sem explicar demais.
8. O que chamou sua atenção primeiro? O que parece confuso ou irrelevante?
9. Se recebesse toda segunda-feira uma lista dos 20 alunos em maior risco com o motivo e uma ação sugerida, o que faria com ela? Quem executaria?
10. O mapa de atrito de conteúdo (capítulos onde os alunos travam) mudaria algo na produção de conteúdo?
11. Que integração é obrigatória para vocês usarem (LMS, SIS/ERP acadêmico, WhatsApp, e-mail)?

**Bloco D — Valor e disposição a pagar (4 min)**
12. Quanto custa hoje um aluno que evade (mensalidade média × meses restantes; custo de captação)?
13. Um modelo por aluno ativo/mês faz sentido? Qual faixa seria aceitável (R$ 0,50 / 1,00 / 2,00 / 3,00)? Quem aprova essa compra?
14. Que resultado precisaria ver em 90 dias para renovar?

**Encerramento** — pedir indicação de mais 1 pessoa para entrevistar; agradecer.

## 3. Formulário de validação (Google Forms / Microsoft Forms) — 12 perguntas

1. Seu papel na instituição (coordenação / tutoria / gestão / docência / aluno).
2. Modalidade predominante dos cursos (EAD / híbrido / presencial).
3. Porte aproximado (até 1 mil alunos / 1–5 mil / 5–20 mil / >20 mil).
4. Hoje, quanto tempo leva para perceber que um aluno parou de acessar? (mesmo dia / 1 semana / 2–4 semanas / só no fim do módulo / não percebemos).
5. Escala 1–5: "Temos um processo claro para agir quando um aluno dá sinais de evasão."
6. Escala 1–5: "Sabemos quais conteúdos fazem os alunos travarem ou desistirem."
7. Quais dados vocês já têm acesso? (logs do LMS / notas / frequência / financeiro / pesquisas de satisfação).
8. Qual ação vocês conseguem executar em escala? (mensagem automática / ligação do tutor / ajuste de prazo / mentoria / bolsa).
9. Quão útil seria uma lista semanal de alunos em risco com motivo e ação sugerida? (1–5).
10. Quão útil seria um mapa dos capítulos com maior atrito e recomendações de redesenho? (1–5).
11. Qual faixa de preço por aluno ativo/mês seria aceitável? (até R$ 0,50 / R$ 0,51–1,00 / R$ 1,01–2,00 / R$ 2,01–3,00 / acima).
12. Aceita participar de um piloto de 90 dias com dados anonimizados? (sim / talvez / não) + contato opcional.

## 4. Hipóteses a validar (matriz)

| Hipótese | Métrica de validação | Evidência atual (dados/fontes) | Resultado das entrevistas |
|----------|----------------------|--------------------------------|---------------------------|
| H1. A instituição descobre a evasão tarde (semanas) | ≥60% respondem "2–4 semanas" ou pior na Q4 | Base real: 61 de 203 alunos (30%) com >14 dias sem acesso e sem sinalização | **[A PREENCHER PELA EQUIPE]** |
| H2. Sinais comportamentais do LMS antecipam a evasão | AUC do modelo ≥0,75 no teste temporal | Ver `05_MVP/outputs/RESULTADOS.md` | **[A PREENCHER PELA EQUIPE]** |
| H3. Tutores não conseguem priorizar quem contatar | ≥50% relatam priorização manual/intuitiva (Q7) | Semesp 2026: desistência EAD 41,6%; equipes reduzidas | **[A PREENCHER PELA EQUIPE]** |
| H4. Conteúdo tem pontos de atrito identificáveis | Concentração de queda em capítulos específicos | Base real: cauda de alunos parados nos caps. 1–3 em todas as fases | **[A PREENCHER PELA EQUIPE]** |
| H5. Há disposição a pagar por aluno ativo/mês | Mediana da Q11 ≥ R$ 1,00 | Estimativa: aluno retido preserva R$ 3–5 mil/ano | **[A PREENCHER PELA EQUIPE]** |
| H6. A integração via export/API do LMS é aceitável | ≥70% possuem logs do LMS acessíveis (Q7) | Base real é um export padrão de logs | **[A PREENCHER PELA EQUIPE]** |

## 5. Registro (modelo `registro_entrevistas.csv`)

```
data,perfil,instituicao_porte,modalidade,tempo_para_perceber_inatividade,processo_claro_1a5,conhece_atrito_conteudo_1a5,dados_disponiveis,acoes_em_escala,utilidade_lista_risco_1a5,utilidade_mapa_atrito_1a5,faixa_preco,piloto,citacao_marcante,aprendizado
```
