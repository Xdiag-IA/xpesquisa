# Validação do XPesquisa

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
