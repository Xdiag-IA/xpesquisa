# Estado do XPesquisa

## Discovery — concluído (2026-09-23)
- Diretório inicialmente vazio; nenhum arquivo do usuário removido.
- Feynman, PaperQA e Open Deep Research estudados; licenças verificadas.
- Panorama e sete ADRs criados antes da implementação.
- Decisões: Python/FastAPI, SQLite, frontend sem build, Apache-2.0, provider extrativo e Ollama opcional.
- Próximo passo: skeleton executável e testes, seguido de integração real Europe PMC.
- Limitação conhecida: páginas de documentação/copyright Europe PMC bloquearam acesso neste ambiente; endpoint oficial responde. Nenhum contorno utilizado.

## Skeleton — concluído
- Pacote instalável, CLI `xpesquisa serve`, FastAPI e interface local funcionando em 127.0.0.1:8787 (8765 já ocupada por outro processo, preservado).
- Primeiro teste de API passou; inventário de dependências e governança adicionados.
- Git local inicializado com identidade já configurada pelo usuário; nenhum remoto criado na etapa inicial.
- Dockerfile/Compose adicionados. Docker instalado, porém engine indisponível; imagem ainda não validada.
- Próximo passo: conector Europe PMC, schemas, provenance persistente e interface de pesquisa.

## Primeira pesquisa real e base de evidência — concluídas
- Conector Europe PMC oficial; recorte MED no exemplo hepático. Não há conector NCBI direto.
- Planejamento explícito do exemplo e query editável; perguntas gerais usam busca literal.
- Contratos versionados Source, Evidence e Claim, referências validadas, conferência de trechos com offsets, consulta de identidade e persistência por etapa.
- Prova real pela interface: 8 artigos, 8 identidades reconfirmadas na mesma base, 7 trechos e afirmações extrativas. Resultado preservado no histórico local. Veja docs/validation.md.
- Interface própria pt-BR: nova pesquisa, progresso, histórico, síntese extrativa, fontes, filtros documentais, vínculos auditáveis e exportação de metadados.
- Providers: extrativo sem IA e Ollama local opcional com saída estruturada, rejeição de IDs inventados e fallback. Ollama real não foi acionado.
- Código original Apache-2.0; versões fixadas e inventário de licenças incluído. Sem publicação externa no primeiro marco.
- Validação final: 30 testes passaram, JavaScript sem erro de sintaxe, dependências consistentes e wheel construído. Compose validado sintaticamente. Detalhes em docs/validation.md.

## O que falta / problemas conhecidos
- Extração clínica estruturada, PICO geral, tradução, avaliação metodológica, GRADE, verificação semântica e retratações.
- Expansão além das primeiras fontes brasileiras, classificação de país/população e módulo de contraditório.
- Busca limitada à primeira página. Resultados podem misturar estudo animal, revisão, carta e estudo clínico. Identificador válido não implica elegibilidade.
- Filtragem clínica depende da extração futura; não existem filtros fictícios por tamanho amostral ou país.
- Persistência local para uma instância; sem autenticação ou infraestrutura de produção. Interrupções são registradas no reinício, sem retomada automática.
- Docker sem engine para validação de imagem; Ollama testado com mocks; CI ainda não rodou em outras plataformas.
- Aviso de depreciação do TestClient da versão resolvida de Starlette, documentado na validação.

## Próximo passo recomendado
Revisar com profissionais de saúde o conjunto recuperado e definir uma pequena avaliação de extração clínica/entailment. Em seguida, implementar resolução independente DOI/PMID e ampliar conectores brasileiros/documentos normativos integrais com revisão de acesso. Consulte docs/roadmap.md. Este marco não declara concluídas todas as fases do produto.

## Colaboração privada no GitHub
- O usuário autorizou criar o repositório privado `Xdiag-IA/xpesquisa` e enviar o código existente.
- README explica a diferença entre repositório e aplicativo local; CONTRIBUTING descreve Issues, branches e pull requests.
- CI permanece disponível por acionamento manual, sem execução automática neste envio.
- Não foram autorizados convites a colaboradores nem mudança para público. Não há implantação web nesta etapa.

## Incremento 0.2 — fontes brasileiras e roteamento
- Perguntas normativas consultam CFM/CRMs; temas hepáticos/imagem incluem SBH/CBR. Escopo manual e UF disponíveis.
- Metadados distinguem norma, publicação institucional e literatura científica. Ementa não equivale a íntegra e situação declarada não equivale a vigência verificada.
- Painel de cobertura distingue fonte consultada, vazia, falha, bloqueada e não integrada. Falhas parciais não apagam outras fontes.
- BVS/LILACS, SciELO e legislação federal permanecem lacunas visíveis. O catálogo de sociedades ainda é limitado.
- Busca real dos três conectores verificada; 49 testes passaram, incluindo bloqueios, redirects, texto comprimido, jurisdição, classificação e compatibilidade histórica. O CBR apresentou falha HTTP em uma execução integrada; resultados das outras fontes foram preservados.
- Revisão automática bloqueou reinício do processo anterior sem motivo detalhado. Prévia 0.2 iniciada em **127.0.0.1:8788**, com cópia SQLite em **data/preview-0.2/xpesquisa.db**. A porta 8787 mantém a instância anterior. Novas pesquisas da prévia ficam nesse banco separado, não são sincronizadas automaticamente com o original.
