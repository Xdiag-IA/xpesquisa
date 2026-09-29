# Validação do XPesquisa

## Incremento — resolução independente de DOI/PMID

Validação em 28/09/2026, terceira rodada da mesma revisão de PR (mesmo dia): **85 testes passaram** (80 anteriores mais 5 novos em `tests/test_identity.py` desta rodada), todos sem rede. Cobertura acumulada: resolução DOI casando/não casando título, DOI não encontrado (404) tratado como `mismatch`, falha de rede tratada como `unavailable` sem interromper a pesquisa, resolução PMID via `esummary` com verificação do parâmetro `tool`, DOI e PMID checados de forma independente na mesma fonte, fonte sem DOI/PMID marcada `not_checked` sem chamar rede, registro antigo sem os campos novos carregado com o padrão, e normalização de título absorvendo diferenças de acentuação/pontuação/maiúsculas.

Correções da segunda rodada, com teste dedicado cada uma:
- **Marcação HTML no título**: `"Effects of <i>Helicobacter pylori</i>..."` bate com o mesmo título sem a tag — comparação passa por `plain_text` (parser HTML do conector Europe PMC) antes de normalizar. `test_html_markup_in_title_does_not_cause_false_mismatch`.
- **DOI do próprio Crossref não é verificado**: fontes com `collection == "CROSSREF_SCIELO"` ficam `not_checked` para `independent_doi_status`, sem nenhuma chamada de rede — doi.org resolveria a mesma origem do depósito. `test_crossref_scielo_doi_is_not_checked_not_independent`.
- **Redirecionamento de DOI controlado**: o cliente não segue redirecionamentos por padrão; a checagem de DOI segue, no máximo, um redirecionamento do doi.org e só para `api.crossref.org`/`data.crosscite.org`/`api.datacite.org`. `test_doi_redirect_to_allowed_metadata_host_is_followed`, `test_doi_redirect_to_untrusted_host_is_not_followed`.

Correções desta terceira rodada, com teste dedicado cada uma:
- **Tag colada sem espaço**: caso real do DOI 10.1155/2014/642391 — Crossref devolve `"against<i>Plasmodium falciparum</i>Antigen"` (sem espaço entre a tag e a palavra seguinte), Europe PMC devolve o mesmo título com espaço. A comparação agora ignora todos os espaços depois de remover HTML e normalizar (`titles_match`), então esse caso bate como `matched`. `test_html_tag_glued_to_word_does_not_cause_false_mismatch`.
- **Circuito só abre por problema do serviço, não do registro**: um redirecionamento para um destino fora da lista permitida ou um 4xx isolado (ex.: 406) marcam só aquele DOI como `unavailable`/`mismatch`, sem abrir o circuito — o DOI seguinte da mesma pesquisa ainda é checado normalmente. Só erro de rede, tempo esgotado, 5xx ou 429 abrem o circuito. `test_4xx_or_redirect_outside_allowlist_marks_only_that_doi_not_the_circuit` (DOI "a" com redirecionamento para editora, DOI "b" resolvido normalmente: `a` fica `unavailable`, `b` fica `matched`), `test_406_marks_only_that_doi_not_the_circuit`, `test_5xx_and_429_open_the_circuit` (confirma que a segunda fonte não tenta a rede quando a primeira responde 503).
- **Redirecionamento só é seguido em HTTPS**: um `Location: http://api.crossref.org/...`, mesmo apontando a um host permitido, não é seguido — fica `unavailable` sem segunda chamada de rede. `test_doi_redirect_to_http_is_not_followed_even_to_allowed_host`.

Registros antigos (JSON persistido sem os novos campos) continuam válidos: `independent_doi_status`/`independent_pmid_status` assumem o padrão `"not_checked"` ao carregar, sem necessidade de migração de schema — confirmado por `test_old_source_json_without_new_fields_loads_with_default` e pelo teste pré-existente `test_old_runs_remain_readable`.

Identificação da ferramenta e limite de requisições, conforme políticas publicadas:
- doi.org: `User-Agent: XPesquisa/0.3 (...)`, espaçamento cortês de 1 req/s (sem limite numérico oficial publicado por doi.org), redirecionamento restrito a servidores de metadados Crossref/DataCite conhecidos, exigindo HTTPS.
- NCBI E-utilities: parâmetro `tool=xpesquisa`, espaçamento de até 3 req/s (limite documentado sem chave de API).

Limitações: a resolução independente cobre apenas fontes com DOI ou PMID que não vieram do próprio Crossref (registros Europe PMC tipicamente MED/PMC). Crossref/SciELO e documentos institucionais (CFM/CRMs, SBH, CBR, SBUS) continuam sem verificação independente nesta entrega. O circuito por pesquisa, restrito a problemas do serviço (rede, tempo esgotado, 5xx, 429), reduz tentativas de rede contra um serviço já sabidamente indisponível na mesma execução sem descartar registros seguintes só por uma recusa 4xx isolada ou redirecionamento fora da lista — ao custo de não recuperar uma falha transitória de serviço dentro da mesma pesquisa (uma pesquisa nova tenta de novo). Não houve chamada de rede real nos testes; a integração real com doi.org e NCBI não foi exercida neste ambiente (sem acesso à rede externa durante a validação).

Data: 2026-09-28. Ambiente: Linux, Python 3.14.7 (ambiente virtual isolado para instalar dependências; repositório não foi alterado fora da branch de trabalho). Testes usam dados sintéticos e não acionam a rede.

## Incremento 0.3 — pergunta de punho e descoberta brasileira

Validação em 23/09/2026: **62 testes passaram**, com o aviso conhecido do TestClient. JavaScript verificado sintaticamente; pacote 0.3 instalado em modo editável. Testes adicionais cobrem query por conceitos, anatomias distintas, escopo manual, respostas Crossref inválidas versus vazias, origem do depositante, sinônimos, ausência de resumo, redirects, DOI duplicado e cartas “de próprio punho” fora da síntese. Europe PMC tem repetição limitada para respostas incompletas, coberta por teste.

Pergunta original: “Quero investigar medidas chave em ultrassom de punho”. Registro anterior `0efbda84-f935-4a10-9580-84480c0067bf` retornava zero fontes com pergunta literal. Execução final pela interface `2da9401c-878d-48d8-8c79-8be06c3ef835`: **12 fontes, 9 trechos**, sendo 8 artigos Europe PMC, 1 registro do depositante SciELO via Crossref, 1 publicação CBR e 2 SBUS. A síntese utilizou apenas os 9 registros científicos; páginas institucionais sem texto ou sem os conceitos ficaram fora. CBR teve falha parcial de leitura, preservada no painel. BVS e SciELO direto permaneceram não integrados.

Execuções intermediárias preservadas mostram instabilidade externa: uma recuperou 13 candidatos antes do ajuste de pertinência; outra teve falhas Europe PMC/CBR e preservou 3 registros das demais fontes. Não se apagou ou reescreveu histórico para aparentar sucesso. A versão final foi confirmada no navegador, na mesma porta 8788 e no banco já utilizado. Interface exibiu os 12 registros e as lacunas. Não houve chamada paga, LLM, leitura integral de normas ou interpretação clínica validada.

Consulte [diagnóstico de acesso e requisitos pendentes](research/expansion-0.3.md). Esta entrega amplia a descoberta, mas não conclui BVS/LILACS, SciELO direto ou legislação federal.

Data: 2026-09-23. Ambiente: Windows, Python 3.10.11 e Node 22.19.0 apenas para checagem de sintaxe JavaScript. Versões Python resolvidas em requirements.lock. Testes usam dados sintéticos e não acionam a rede.

## Incremento 0.2 — fontes brasileiras

- **49 testes passaram**; sintaxe JavaScript e `git diff --check` passaram. Cobertura adicional: roteamento normativo, seleção de sociedades, consulta nacional e estadual, robots, bloqueios, redirects externos, respostas comprimidas, resultados vazios versus HTML inesperado, classificação institucional e compatibilidade com pesquisas antigas.
- Pergunta original sobre legislação de IA na medicina, incluindo o erro de digitação “artifical”, executada pela interface. Registro `7671326f-3485-4102-ac83-0b07aa70cd52`: 8 candidatos do CFM/CRMs, 1 trecho selecionado da ementa da Resolução CFM 2454/2026. Outros candidatos ficam nas fontes, sem entrar automaticamente na síntese. Seleção lexical não equivale a validação semântica. Íntegra, vigência independente e legislação federal não verificadas.
- Pesquisa hepática integrada `00d68eac-619a-440b-9a80-958b7c66ebf8`: 5 artigos Europe PMC, 5 publicações SBH e 7 trechos. CBR falhou com HTTPStatusError; cobertura registrou a falha sem apagar os resultados disponíveis. Em teste isolado anterior, CBR retornou 2 documentos legíveis e 1 falha de documento. Disponibilidade externa não é garantida.
- Navegador confirmou a síntese normativa, consulta realizada, lacuna de legislação federal e caminho até a fonte original. Nenhuma chamada paga ou LLM foi utilizada.
- BVS/LILACS, SciELO, legislação federal e outras sociedades não estão integradas. Não existe motor geral de descoberta web neste incremento.
- Prévia em `http://127.0.0.1:8788/`, com cópia do histórico em `data/preview-0.2/xpesquisa.db`. A instância anterior em 8787 foi preservada após bloqueio automático da tentativa de reinício. Os dois históricos não são sincronizados.

As seções seguintes registram a validação histórica do primeiro marco 0.1.

## Prova real

Pesquisa realizada pela interface local: “Qual é a evidência atual sobre elastografia hepática para avaliação de fibrose?”. Execução inicial `d499834a-1ede-47f1-9cd7-8d50ab9280b5`, preservada no SQLite local, fora do Git. Resultado: 8 fontes, 7 trechos e 7 afirmações extrativas; 8 identificadores/metadados reconfirmados pela mesma base. Uma fonte não tinha abstract. Não houve chamada paga ou modelo LLM. Reexecução após a correção de normalização: `f2730115-e808-404a-94db-8b9d5d63ad13`; o primeiro registro não foi reescrito retroativamente.

Query: `(elastography OR "liver stiffness") AND (liver OR hepatic) AND fibrosis AND SRC:MED`.

Esta prova valida acesso e rastreabilidade, não qualidade clínica da resposta. Os registros incluem desenhos e populações distintos, inclusive estudo animal; não são automaticamente elegíveis para responder uma pergunta clínica. País da população, qualidade e nível de evidência não foram inferidos. Referências com data editorial posterior à consulta podem aparecer no índice; a data recebida é exibida sem inferir data de disponibilização.

## Verificações

- Suíte unitária/integração: **30 testes passaram**. Schemas, limites, planejamento, conectores mockados, persistência/reabertura, recuperação após interrupção, fallback LLM, citações inventadas, trechos adulterados, IDs duplicados, falhas versus busca vazia, proteção de origem/Host e exportação sem textos.
- Checagem de sintaxe do JavaScript: passou.
- Navegador real: pergunta de exemplo, envio, progresso, resultado concluído, histórico e abas fontes/síntese/rastreabilidade.
- Sanitização corrigida após inspeção: HTMLParser preserva sinais `<` e `>` em comparações científicas; teste específico adicionado.
- `pip check`: nenhuma dependência incompatível. Wheel construído com assets e licenças; configuração Compose validada sintaticamente.

## Ainda não validado

- Modelo Ollama real: adapter coberto por mocks, sem modelo instalado/configurado para este teste.
- Docker: engine local indisponível; configuração fornecida, imagem não construída.
- Windows/macOS/Linux em CI: workflow preparado, não executado no primeiro marco. Posteriormente foi autorizado enviar o código para um repositório privado; o workflow permanece manual e a matriz remota ainda não foi validada.
- Avaliação clínica, GRADE, verificação semântica e contraditório: não implementados.

Aviso conhecido de dependência: Starlette 1.7 recomenda httpx2 para seu TestClient. A suíte com HTTPX 0.28 passa; migração futura do cliente de testes deverá verificar licença e compatibilidade, sem alterar o conector por causa apenas do aviso.
