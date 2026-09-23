# Validação do primeiro marco

Data: 2026-09-23. Ambiente: Windows, Python 3.10.11 e Node 22.19.0 apenas para checagem de sintaxe JavaScript. Versões Python resolvidas em requirements.lock. Testes usam dados sintéticos e não acionam a rede.

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
