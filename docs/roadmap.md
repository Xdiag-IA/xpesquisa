# Roadmap incremental

## Marco entregue

Fase 0: discovery, licenças, ADRs. Fase 1: núcleo executável, banco e interface. Fase 2: primeira busca real Europe PMC, interpretação limitada ao exemplo, query editável, recuperação e síntese extrativa. Incluída a base mínima da fase 3 (contratos e invariantes) porque não é seguro construir citações sem ela. A interface mínima serve a esse fluxo; não representa conclusão da fase 6.

## Próximos incrementos

1. Consolidar Evidence Engine: extração estruturada de população/amostra/desfecho, adjudicação humana e testes de entailment com especialistas; resolução independente DOI/PMID; versão de migração de schema.
2. Melhorar busca: vocabulário DeCS/MeSH com licenças documentadas, PICO/PECO editável, paginação, critérios de seleção e comparação entre conectores. Não confundir afinidade lexical com qualidade científica.
3. Brasil: base CFM/CRMs e publicações SBH/CBR integradas na versão 0.2. Próximo: ampliar legislação federal, BVS/LILACS, SciELO e demais sociedades, revisando acesso e direitos. Distinguir regulação, diretriz e estudo brasileiro; não inferir país de população pelo país de periódico ou da instituição.
4. Crítica/contraditório: módulos reviewer e cético com objetivos distintos, consultas opostas explícitas e conjunto de avaliação. Introduzir agentes concorrentes só se medirmos melhoria de cobertura, detecção de contradição ou confiabilidade.
5. UX: filtros clínicos somente quando houver dados confiáveis; pesquisa ampla, revisão, comparação, auditoria, diretrizes, Brasil, evidência, discordâncias e atualização como capacidades da API. Exportação de conteúdo depende de licença da fonte.

## Critérios de avanço

Cada conector precisa de testes sem rede para vazio, indisponibilidade, limites, deduplicação e identidade. Cada campo clínico precisa de trecho de suporte e estado desconhecido. Cada conclusão precisa de vínculo validado e estado semântico explícito. Avaliações devem medir falsos suportes, citações inexistentes, cobertura e custos; não só fluência do texto. Adicionar PostgreSQL/vector store apenas com demanda demonstrada. Produtos clínicos continuam desacoplados.
