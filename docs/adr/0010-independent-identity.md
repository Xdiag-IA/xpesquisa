# 0010 — Resolução independente de DOI/PMID

Status: aceita.

## Problema

`EuropePMC.check_identifier` reconfirma id, título e DOI consultando a própria
Europe PMC de novo. Isso confirma consistência interna da base, não resolução
independente: um erro de metadado na Europe PMC não seria detectado.

## Decisão

Adicionar um módulo novo, `identity.py`, com verificação contra duas fontes
externas à Europe PMC, ambas públicas e sem chave obrigatória:

- DOI → `doi.org`, negociação de conteúdo CSL-JSON (mantido por
  Crossref/DataCite).
- PMID → NCBI E-utilities `esummary` (PubMed).

Cada fonte grava seu próprio status (`independent_doi_status`,
`independent_pmid_status`) em `Source`, em campos novos e opcionais com padrão
`"not_checked"` — registros antigos, persistidos como JSON na coluna `body`,
são lidos com o padrão sem precisar de migração de schema. A checagem por
Europe PMC (`identifier_status`) continua existindo sem alteração; a nova
checagem é um segundo sinal independente, não substitui o primeiro.

Comparação de título usa forma normalizada (minúsculas, sem acento, sem
pontuação) para não marcar `mismatch` só por diferença de formatação entre
fontes.

Seguimos as políticas de uso publicadas por cada fonte: identificação da
ferramenta (`User-Agent` descritivo e parâmetro `tool` no NCBI) e
espaçamento entre requisições (NCBI: até 3 req/s sem chave; DOI.org: sem
limite numérico publicado, adotado 1 req/s por cortesia, seguindo o mesmo
princípio do "polite pool" da Crossref).

## Consequências

Fontes externas indisponíveis marcam `unavailable` e não bloqueiam a
pesquisa nem apagam a checagem já feita na Europe PMC — o padrão de falha
parcial já usado no restante do pipeline. A resolução cobre apenas fontes
com DOI ou PMID; Crossref (metadados do depositante SciELO) e documentos
institucionais continuam sem verificação independente nesta entrega. Duas
novas dependências externas de rede em tempo de execução (doi.org,
eutils.ncbi.nlm.nih.gov); nenhuma nova biblioteca de terceiros.
