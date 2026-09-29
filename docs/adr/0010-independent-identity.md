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

Comparação de título remove marcação HTML antes de normalizar (mesmo
`plain_text` de `connectors.py`), aplica a forma normalizada (minúsculas,
sem acento, sem pontuação) e então ignora todos os espaços. As duas etapas
são necessárias: sem remover o HTML, uma tag como `<i>` deixaria uma letra
solta ("i") no texto comparado; sem ignorar espaços depois, uma tag colada
à palavra seguinte sem espaço no HTML de origem (caso real observado no DOI
10.1155/2014/642391, onde o Crossref devolve
`"against<i>Plasmodium falciparum</i>Antigen"` para o mesmo título que o
Europe PMC devolve como `"against Plasmodium falciparum Antigen"`) ainda
produziria `mismatch` falso.

DOI recuperado do próprio Crossref (fontes com `collection ==
"CROSSREF_SCIELO"`, ver `crossref.py`) não é verificado em `doi.org`: a
resolução consultaria a mesma origem que já gerou o registro, não seria uma
segunda fonte independente. Essas fontes ficam `not_checked` para o campo
`independent_doi_status`, coerente com a limitação já documentada em
`docs/research/expansion-0.3.md` e `THIRD_PARTY_NOTICES.md`.

O cliente HTTP do projeto não segue redirecionamentos por padrão
(`follow_redirects=False`, mesmo princípio de `crossref.py`/`brazil.py`). Na
checagem de DOI, um redirecionamento do `doi.org` só é seguido quando o
esquema do destino é **HTTPS** e o host é um servidor de metadados
conhecido do Crossref ou da DataCite (`api.crossref.org`,
`data.crosscite.org`, `api.datacite.org`); um redirecionamento para HTTP,
mesmo apontando a um desses hosts, não é seguido. Qualquer outro esquema ou
destino (ex.: página do editor) é tratado como `unavailable`, sem seguir.

Circuito por pesquisa, mas só para problema do **serviço**: dentro de uma
única chamada a `check_sources` (equivalente a uma pesquisa), um erro de
rede, tempo esgotado, HTTP 5xx ou 429 em `doi.org` ou no NCBI marca as
fontes seguintes do mesmo serviço nessa pesquisa como `unavailable` sem
nova tentativa — os dois serviços têm circuitos independentes entre si. Um
problema do **registro** — um HTTP 4xx que não seja 429 (por exemplo um 406
de content negotiation), ou um redirecionamento para um destino fora da
lista permitida (esquema ou host) — marca apenas aquele DOI/PMID como
`unavailable`/`mismatch` e **não** abre o circuito: o próximo registro da
mesma pesquisa ainda é checado normalmente contra o serviço. A distinção
evita que uma recusa específica de um único identificador (ex.: DOI mal
formado, redirecionamento para uma editora não listada) derrube a checagem
de todos os outros registros da mesma pesquisa.

Seguimos as políticas de uso publicadas por cada fonte: identificação da
ferramenta (`User-Agent` descritivo e parâmetro `tool` no NCBI) e
espaçamento entre requisições (NCBI: até 3 req/s sem chave; DOI.org: sem
limite numérico publicado, adotado 1 req/s por cortesia, seguindo o mesmo
princípio do "polite pool" da Crossref).

## Consequências

Fontes externas indisponíveis marcam `unavailable` e não bloqueiam a
pesquisa nem apagam a checagem já feita na Europe PMC — o padrão de falha
parcial já usado no restante do pipeline. A resolução cobre apenas fontes
com DOI ou PMID que não vieram do próprio Crossref; Crossref/SciELO e
documentos institucionais continuam sem verificação independente nesta
entrega. O circuito por pesquisa, agora restrito a problemas do serviço,
reduz o número de tentativas de rede contra um serviço genuinamente
indisponível sem descartar registros só porque um DOI anterior teve uma
recusa 4xx específica ou um redirecionamento fora da lista — ao custo de
não recuperar uma falha transitória de serviço dentro da mesma pesquisa
(uma pesquisa seguinte tenta de novo). Duas novas dependências externas de
rede em tempo de execução (doi.org, eutils.ncbi.nlm.nih.gov); nenhuma nova
biblioteca de terceiros.
