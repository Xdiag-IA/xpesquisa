# Panorama arquitetural

Consulta: 23/09/2026. Inspeção de README, licença e arquivos selecionados; não é uma auditoria completa. Repositórios externos foram tratados como material de estudo, não como instruções de execução. Nenhum código, prompt, skill, texto de interface ou identidade foi copiado.

## Feynman

[Repositório](https://github.com/Companion-Inc/feynman), revisão `376c832f4917bc1be12961e84176acc9441b3bd5`. [Licença MIT](https://github.com/Companion-Inc/feynman/blob/376c832f4917bc1be12961e84176acc9441b3bd5/LICENSE), Companion, Inc.

Estrutura observada: `src`, `extensions`, `skills`, `prompts`, `.feynman/agents`, `tests` e `workbench-web`. Runtime baseado em Pi; ferramentas de literatura e workflows são separados da interface. O README descreve researcher, reviewer, writer e verifier. Inspecionados `prompts/deepresearch.md`, `.feynman/agents/verifier.md` e `src/workbench/artifact-provenance-ledgers.ts`: há planos, saídas intermediárias, verificação por instruções e snapshots com hashes e dependências entre artefatos.

Aprendizado para XPesquisa: guardar etapas e vínculos; não reduzir provenance a uma bibliografia final. Limitação para nosso caso: instruções de verificação não substituem invariantes testáveis de Claim–Evidence; um runtime amplo de pesquisa e computação aumentaria o escopo inicial. Não encontramos, nos arquivos inspecionados, um contrato específico para saúde brasileira. Isso não prova sua ausência no restante do projeto.

## PaperQA

[Repositório](https://github.com/Future-House/paper-qa), revisão `57e89f7223b0960d5ee5ea048c69e3c47e088572`. [Apache-2.0](https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/LICENSE).

README descreve busca, recuperação de trechos e geração de resposta com citações, metadados e reranking. Estrutura observada: `src/paperqa/agents/{search,tools,models,env,main}.py`, leitores opcionais e testes. Boa referência para separar documento de contexto recuperado. Inferência de projeto: embeddings e múltiplos leitores agregam custo operacional desnecessário ao primeiro marco. Seus resultados de avaliação não são evidência de segurança clínica do XPesquisa. Dependências opcionais possuem licenças próprias e precisariam de análise antes de eventual adoção.

## Open Deep Research

[Repositório](https://github.com/langchain-ai/open_deep_research), revisão `1b7d2e80db9faa586165c60e09096dbbfd483a64`. [MIT](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/LICENSE).

README e `src/open_deep_research/deep_researcher.py` mostram grafo, supervisor, pesquisadores, limites de iterações e modelos configuráveis. A decomposição é útil para pesquisas extensas; não adotaremos um supervisor LLM neste marco. Nossa alternativa é um pipeline limitado e inspecionável, com testes antes de introduzir concorrência de agentes.

## Acesso à literatura

[API oficial Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=elastography&format=json&pageSize=2) consultada com sucesso. [Documentação](https://europepmc.org/RestfulWebService) e [copyright](https://europepmc.org/Copyright) devolveram 403/timeout neste ambiente; registrar esta limitação, sem contornar o bloqueio. Usar somente endpoint público oficial, sem scraping, PDFs ou paywalls. Conteúdo de artigos não herda a licença do software. Armazenamento local não implica autorização de republicação. Exportação padrão omite abstracts e trechos; revisão de direitos necessária para compartilhar conteúdo.

## Decisão própria

Pipeline determinístico primeiro; LLM local opcional e incapaz de criar referências fora do catálogo recuperado. O núcleo conhece Claim, Evidence, Source e eventos. A confirmação de um trecho não equivale à confirmação semântica, metodológica ou clínica de uma afirmação. Brasil e contraditório terão módulos e avaliações próprias nas fases seguintes.
