# Ampliação brasileira e busca por conceitos — 0.3

Diagnóstico em 23/09/2026. A pesquisa “Quero investigar medidas chave em ultrassom de punho” enviava a frase inteira ao Europe PMC e termos conversacionais ao CBR. Ambas retornaram zero. O histórico original foi preservado.

## Entregue

- Vocabulário explícito de ultrassonografia, anatomia e medidas. Punho, ombro, joelho, tornozelo e cotovelo contemplados. Sem inferência de diagnóstico ou valores normais. Query manual e escopo somente literatura preservados.
- [SBUS](https://sbus.org.br/): API WordPress pública, mesma política de robots, domínio, tamanho, bloqueios e proteção do conector institucional. Busca por punho retornou uma publicação específica; seu corpo estava vazio, portanto não gera evidência. Não há leitura de área de associados ou PDFs.
- [API Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/): metadados públicos, sem autenticação. Consulta ao catálogo de membros confirmou o ID 530 como FapUNIFESP (SciELO). Endpoint `/members/530/works`, filtro journal-article, até 20 candidatos e limite solicitado de selecionados. Resultados aproximados passam por seleção lexical, com sinônimos iniciais. Isso reduz resultados sem os conceitos, mas não valida pertinência clínica.
- Rótulo explícito “Crossref — depositante SciELO Brasil”. Não equivale a consultar o portal SciELO, nem comprova indexação atual, origem da população ou cobertura de toda a coleção. Sem acesso ao portal bloqueado. DOI aponta à publicação para abertura manual; não é resolvido automaticamente.
- Resumos ausentes não são inventados; título não vira trecho científico. Mesmo DOI recuperado por duas fontes não gera trechos duplicados. Registros e consultas permanecem rastreáveis.

## Dependências ainda não resolvidas

| Integração | Evidência observada | Próximo requisito |
|---|---|---|
| BVS/LILACS | [Contrato oficial BIREME](https://github.com/bireme/api-docs/blob/main/apis/bibliographic-en.yaml) descreve `/bibliographic/v1/search/`, parâmetro q e autenticação apikey no cabeçalho. API sem credencial restringe acesso; robots do portal respondeu 403 | Obter acesso autorizado e validar resposta real antes de implementar parser. Nenhuma chave solicitada em conversa ou armazenada no projeto; conector não apresentado como pronto |
| SciELO direto | Portal de busca respondeu 403. [ArticleMeta oficial](https://github.com/scieloorg/articles_meta/blob/master/docs/source/index.rst) oferece recuperação por identificadores e acervos, não um substituto comprovado da busca textual | Definir acesso autorizado ou índice local a partir de acervo licenciado; não baixar coleção inteira neste incremento |
| Legislação federal | [Senado documenta LexML SRU](https://www12.senado.leg.br/dados-abertos/legislativo/legislacao/acervo-do-portal-lexml), mas robots negou a rota SRU. Domínio legis.senado.leg.br respondeu 403 ao robots | Viabilizar canal oficial de consulta; não contornar restrições nem confundir proposições legislativas com leis vigentes |

Nenhuma dessas restrições foi contornada. BVS, busca direta SciELO e legislação federal continuam explicitamente pendentes. Esta entrega não conclui toda a etapa Brasil.

## Direitos e operação

A API Crossref permite reutilizar metadados; abstracts podem manter copyright de autores/editoras. Exportação do XPesquisa continua omitindo conteúdo textual. Publicações SBUS mantêm direitos próprios. Nenhuma biblioteca nova ou código de terceiros incorporado; implementação original com HTTPX e biblioteca padrão.

Busca automática agora inclui descoberta brasileira mesmo sem Brasil na pergunta, exceto quando o usuário escolhe somente literatura. Normas continuam roteadas separadamente. O usuário pode inspecionar cada consulta. Termos de busca são enviados às fontes; não usar dados de pacientes.
