# BRIEF DO PROJETO — Startup One / Enterprise Challenge Oracle (FIAP, 4ESOA-2026)

## Contexto acadêmico
- Curso: Engenharia de Software, 4º ano (FIAP). Atividade de fase (Fase 6): "Refinamento, Validação e Estruturação do MVP".
- O mesmo projeto é o Startup One e o Enterprise Challenge Oracle. Exigência: usar ao menos uma tecnologia/serviço Oracle, como decisão estratégica.
- Entregáveis: documento estruturado (Partes 1–4), diagramas atualizados, evidência de integração Oracle, vídeo pitch (≤5 min, YouTube não listado), tudo em um ZIP que funcione localmente.
- Formulário da Banca Final (13/09/2026): link do vídeo; 4 respostas de até 300 caracteres (problema+para quem; como funciona; diferencial e por que não foi resolvido assim antes; monetização); link de protótipo (opcional).
- Roteiro sugerido do pitch: Público → Problema → Oportunidade → Solução → Demonstração → Diferencial → Monetização → Mercado → Fechamento.
- Responsável pela equipe: Lucas (líder). Demais integrantes: placeholders a preencher.
- Idioma de TODOS os entregáveis: português do Brasil. Tom: profissional, direto, credível para banca de executivos Oracle/FIAP.

## Tema definido pelo usuário
"Plataforma de machine learning para métricas em instituições educacionais conseguirem calcular turnover (evasão) de alunos e adaptar conteúdo para evitar que alunos desistam do curso."
Dois pilares: (1) prever/medir risco de evasão por aluno a partir do comportamento no LMS; (2) diagnosticar atrito de conteúdo e recomendar adaptações (formato, ritmo, intervenções) para reter.

## Base de dados real disponível (Base-Anônima.xlsx → logs.csv)
- Export de logs do LMS (FIAP ON, estilo Moodle) de um curso em 5 fases sequenciais. 684.723 eventos, 15/01/2026 → 26/08/2026.
- Colunas: Hora, Nome completo (anonimizado "Aluno NNNN"), Usuário afetado, Contexto do Evento (ex.: "Player HTML: Cap 3 - ..."), Componente, Nome do evento, Descrição, Origem (web/cli/ws).
- 203 alunos distintos. Presença por fase: F1=175, F2=174, F3=179, F4=166, F5=161 (F5 ainda em andamento no export).
- 153 alunos (75%) ativos nas 5 fases; 9 só na F1 (abandono precoce); 8 param após F4; outros padrões intermitentes.
- Funil dos ativos em F1: F2 94,3% → F3 94,3% → F4 92,0% → F5 88,0% (perda acumulada de 12% dos ingressantes em ~7 meses).
- Inatividade (ref. 26/08): 61 alunos >14 dias sem acesso (30%), 47 >30 dias (23%), 35 >60 dias (17%).
- Conteúdo: Player HTML domina (≈323 mil eventos) vs PDF (≈18,6 mil), vídeo/áudio quase nulos. Capítulos por fase: 10–12 (F5 tem 8).
- Alcance de capítulo: maioria chega ao último capítulo; cauda de alunos travados nos capítulos 1–3 (na F5, 25 alunos parados nos caps 1–2).
- Eventos principais: "Progresso de conteúdo atualizado" (501k), "Conteúdo HTML visualizado" (110k), questionários (tentativas iniciadas 6,3k / entregues 5,8k), notas, tarefas, envios.
- Horário: pico 19h–22h (aluno trabalhador, estuda à noite); segunda a quinta > fim de semana.
- Sinais úteis para features: eventos/semana, dias ativos, recência (dias desde último acesso), progressão de capítulos, tentativas de quiz, entregas, tendência (últimas 2 semanas vs. anteriores), mix de conteúdo, horário.

## Mercado (fontes públicas 2025–2026, citar exatamente assim)
- INEP, Censo da Educação Superior 2024 (divulgado 22/09/2025): 10,2 milhões de matrículas na graduação (+30,5% em 10 anos); EAD 5.189.391 (50,7%) superou presencial 5.037.482 pela primeira vez; 2.561 IES, das quais 2.244 privadas (87,6%) com 79,8% das matrículas (8,1 milhões de alunos). Fonte: https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias/censo-da-educacao-superior/inep-divulga-resultado-do-censo-superior-2024
- Instituto Semesp, 16º Mapa do Ensino Superior no Brasil 2026 (mar/2026), https://www.semesp.org.br/mapa/edicao-16/brasil/ : taxa de desistência 2024 — EAD 41,6% (privada 41,9%; pública 32,2%); presencial 24,8% (privada 26,6%). Desistência acumulada do ciclo 2020–2024 na rede privada: 64,7% (EAD privada: 68,1%). Rede privada concentra 95,9% das matrículas EAD. 1,4% das mantenedoras reúnem 47,1% dos estudantes (mega grupos). Concluintes presenciais caíram 6,9% em 2024.
- Consequência econômica (raciocínio próprio, rotular como estimativa): com ~5,2 milhões de alunos EAD e desistência anual de ~41%, mais de 2 milhões de matrículas EAD são perdidas por ano; a um ticket médio EAD estimado de R$ 250–450/mês, cada aluno retido por mais 12 meses preserva R$ 3–5 mil de receita. Custo de aquisição de aluno (CAC) em EAD frequentemente supera R$ 1.000 (estimativa de mercado; rotular).

## Oracle (nomes atuais 2026)
- Oracle AI Database 26ai (novo nome do 23ai; long-term release). Oracle Autonomous AI Database (Serverless) na OCI.
- Oracle Machine Learning (OML): OML4SQL/DBMS_DATA_MINING (modelos in-database: GLM, Random Forest, XGBoost, SVM, clustering), OML4Py, AutoML, OML Notebooks; Data Science Agent.
- Select AI (linguagem natural → SQL), AI Vector Search, JSON Relational Duality Views, Oracle APEX (low-code dashboards), OCI Object Storage, OCI Data Science, OCI Generative AI, OCI Functions, OCI API Gateway, Oracle Analytics Cloud.
- Evidência prática produzida neste projeto: Oracle Database Free (imagem gvenzl/oracle-free) em Docker local, conexão via python-oracledb, tabelas de features, modelo treinado in-database com DBMS_DATA_MINING e scoring com PREDICTION_PROBABILITY em SQL. Em produção: Autonomous AI Database (Always Free para o MVP).

## Restrições de honestidade
- Não inventar entrevistas reais. Parte 2 deve trazer: instrumento (roteiro de entrevista + formulário), validação quantitativa com a base real, validação secundária (fontes), e campos claramente marcados para a equipe registrar as entrevistas reais. Hipóteses e aprendizados devem ser rotulados como derivados dos dados/fontes.
- Não inventar nomes de integrantes, nem clientes/pilotos reais. Usar placeholders explícitos onde necessário.
