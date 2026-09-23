# 0008 — Direcionamento por assunto e cobertura brasileira

Status: aceita, versão 0.2.0, 2026-09-23.

Problema: mandar uma pergunta normativa em português para uma base de artigos não consulta a autoridade competente. O pipeline deve planejar fontes e queries separadamente e preservar falhas parciais.

Decisão: SearchTask para cada conector e Coverage para seu resultado. Regras explícitas reconhecem termos normativos, hepáticos e de imagem; usuário pode selecionar escopo e UF. Catálogo inicial: Europe PMC, base pública CFM/CRMs, SBH e CBR. Perguntas normativas não acionam Europe PMC por padrão. UF selecionada consulta também o CFM nacional. O catálogo não pretende cobrir todas as sociedades.

Normas são recuperadas na busca pública do CFM (resoluções e pareceres), com ementa, jurisdição, número e situação declarada. Não baixar ou interpretar automaticamente a íntegra. Sociedades usam a API pública WordPress de busca e documentos. Artigo, norma e publicação institucional possuem tipos distintos. Encontrar anúncio de diretriz não significa ter recuperado a diretriz.

Ausência de motor visível no site não implica ausência de mecanismo público: priorizar API oficial; depois busca pública ou sitemap permitido, com adapter testado. Não usar scraping de Google/Bing nem simular APIs oficiais. Para sites sem adapter, registrar lacuna e link manual; motor de descoberta geral por domínio é uma extensão futura, não uma capacidade já entregue. A API SearXNG foi estudada como opção local futura; nenhum código/servidor foi instalado e nenhuma chamada foi realizada.

Robots consultado antes de acessar cada domínio, redirects restritos à mesma origem HTTPS, leitura limitada a 3 MB, respeito a intervalo indicado e paralelismo baixo. Bloqueios 401/403/429 interrompem a fonte, sem tentar endpoint alternativo. Conteúdo protegido não é extraído. Links de PDFs são apenas referências para leitura manual, não resultados integralmente verificados.

Falha de uma fonte não descarta as outras. Todas falhando resulta em pesquisa falha; sucesso parcial permanece concluído com painel de lacunas. `completed` não significa cobertura completa nem validade clínica/jurídica. BVS/LILACS, SciELO e legislação federal são explicitamente não integradas. A BVS bloqueou a inspeção automatizada inicial; não foi contornada.

Schema 0.2 acrescenta campos com defaults; registros 0.1 continuam legíveis e conservam versão/conteúdo originais. Campo `abstract` permanece como armazenamento compatível do texto normalizado; `content_kind` distingue abstract, ementa e texto institucional. Exportação continua omitindo esse conteúdo.
