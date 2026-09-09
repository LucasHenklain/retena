# Respostas para o formulário "4ESOA Enterprise Challenge Oracle — Envio do Vídeo Pitch"

Prazo: 13/09/2026. Cada resposta abaixo tem no máximo 300 caracteres (contagem indicada). Copiar e colar exatamente.

## 1. Link do vídeo pitch
https://youtu.be/HZrcLvIJCC4 — vídeo não listado, 4 min 48 s; testar em janela anônima antes de enviar. Arquivo de origem: `07_Video_Pitch/Retena_Pitch_Banca_Final.mp4`.

Equipe: Lucas Dalmas (RM551178, líder) · Lucas Emanuel (RM97881) · Kayque Moraes (RM97592) · Lucas Henklain (RM99350) · Vinicius Pinheiro (RM99198).

## 2. Qual problema a solução resolve, e para quem (≤300)
> Coordenadores e diretores de IES privadas com EAD só descobrem a evasão quando a mensalidade para: 41,6% dos alunos EAD desistiram em 2024 (Semesp). A Retena antecipa em semanas quem vai sumir, lendo os sinais que o LMS já registra, e diz quem contatar, por quê e o que ajustar no curso.

(≈287 caracteres)

## 3. Como a solução funciona, de forma objetiva (≤300)
> Os logs do LMS entram no Oracle AI Database; features semanais (recência, tendência, capítulo travado, quizzes) são calculadas em SQL e um modelo Oracle Machine Learning pontua o risco de cada aluno in-database. Toda segunda, a coordenação recebe a fila de intervenção e o mapa de atrito.

(≈299 caracteres)

## 4. Diferencial e por que não foi resolvido assim antes (≤300)
> BI mostra o passado e CRM cobra tarde. A Retena junta risco por aluno, atrito por capítulo e resultado da intervenção em R$, sem o dado sair da IES (LGPD) e sem time de ciência de dados, porque o ML roda dentro do banco. Ficou viável agora: ML in-database maduro e EAD como maioria desde 2024.

(≈292 caracteres)

## 5. Como a solução se sustenta como negócio (≤300)
> SaaS B2B por aluno ativo/mês: R$ 6 (até 10 mil alunos), R$ 4 (10–50 mil) e R$ 3 (megagrupos), mínimo R$ 5 mil/mês e setup de R$ 10–25 mil. Piloto de 90 dias em uma fase com meta de rematrícula. Uma IES de 12 mil alunos paga R$ 576 mil/ano e se paga retendo 137 alunos (1,1% da base).

(≈283 caracteres)

## 6. Link do protótipo, repositório ou aplicação publicada (opcional)
https://lucashenklain.github.io/retena/ — landing page publicada no GitHub Pages, com o dashboard do MVP (`/dashboard/`), as evidências Oracle (`/evidencias/evidencias.html`) e os diagramas (`/diagramas/`). Repositório: https://github.com/LucasHenklain/retena. Versões locais no ZIP: `04_Landing_Page/index.html` e `05_MVP/dashboard/index.html`.
