# ADR 0009 — Busca por conceitos e descoberta brasileira parcial

Status: aceita em 23/09/2026.

## Problema

Frases conversacionais em português produzem consultas inadequadas em índices internacionais. A expansão brasileira enfrenta restrições de acesso reais, que não devem ser ocultadas por integrações fictícias.

## Decisão

Adicionar vocabulário explícito de modalidade/anatomia/medidas, SBUS como fonte institucional e metadados do depositante FapUNIFESP/SciELO via API Crossref. Manter a identificação do intermediário e a busca direta SciELO como lacuna. Expor BVS e legislação pendentes com seus requisitos documentados. Não implementar parser BVS sem credencial e resposta real para validar contrato.

Crossref usa busca aproximada: examinar primeira página limitada e exigir correspondência lexical de conceitos antes de apresentar os candidatos. Sem abstract não há Evidence; título sozinho não sustenta achado clínico. Deduplicar extração por DOI sem apagar os registros de fontes distintas.

## Consequências

Perguntas contempladas recuperam fontes mais pertinentes, mas vocabulário limitado e seleção lexical podem perder resultados. Crossref não cobre toda a SciELO. SBUS pode fornecer só metadados ou anúncios. Nenhuma interpretação médica, valores normais ou força da evidência são inferidos. Não há novas dependências, cobrança, índice completo local ou motor geral web.
