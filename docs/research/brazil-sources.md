# Fontes brasileiras — acesso e limites

Este documento registra o incremento 0.2. Para a atualização 0.3 (SBUS, metadados SciELO via Crossref e diagnóstico de acesso BVS/legislação), consulte [ampliação 0.3](expansion-0.3.md). Busca direta SciELO permanece pendente.

Verificado em 2026-09-23. Não há licença presumida para republicar conteúdo; acesso público/robots não equivale a concessão de direitos. O código dos conectores é original, usa HTTPX existente e biblioteca padrão Python. Nenhuma biblioteca nova ou prompt de terceiros incorporado.

| Fonte | Acesso observado | Implementação | Limites |
|---|---|---|---|
| [CFM e CRMs](https://portal.cfm.org.br/buscar-normas-cfm-e-crm/) | Busca HTML pública, parâmetros texto, tipo[] e uf; robots permite essa rota | Ementas e metadados de resoluções/pareceres; situação informada pela base | Não lê íntegra, não confirma vigência independente nem cobre todas as leis |
| [SBH](https://sbhepatologia.org.br/) | API pública WordPress; robots sem proibição da rota | Busca e leitura de posts/pages públicos | Cursos, eventos e anúncios podem aparecer; não rotular como guideline automaticamente |
| [CBR](https://cbr.org.br/) | API pública WordPress; robots sem proibição da rota | Busca e leitura de posts/pages públicos | Alguns documentos podem falhar; falhas individuais registradas |
| [BVS/LILACS](https://search.bvsalud.org/) | robots retornou 403 com proteção de acesso na inspeção | Lacuna e link manual | Nenhuma tentativa de contorno, nenhum resultado atribuído à BVS |
| [SciELO](https://search.scielo.org/) | Não integrado neste incremento | Lacuna e link manual | Não apresentar como fonte pesquisada |
| [Legislação federal](https://www.planalto.gov.br/ccivil_03/) | Não integrado neste incremento | Lacuna e link oficial | Não confundir resoluções dos conselhos com cobertura da legislação federal |

Robots oficiais inspecionados: [CFM](https://portal.cfm.org.br/robots.txt), [SBH](https://sbhepatologia.org.br/robots.txt), [CBR](https://cbr.org.br/robots.txt). O aplicativo consulta novamente antes do acesso, por pesquisa. [Política de privacidade do CFM](https://portal.cfm.org.br/politica-de-privacidade/) examinada; não estabelece licença geral de conteúdo. Licenças de publicações institucionais permanecem desconhecidas quando não explicitadas. Sem extração de conteúdo de associados, login ou paywall. Exportação omite textos.

Contrato de API consultado: [WordPress Search Results](https://developer.wordpress.org/rest-api/reference/search-results/). Busca `wp/v2/search`, depois endpoint do próprio documento, aceitando apenas domínio institucional e posts/pages públicos. Nenhum código WordPress incorporado.

Descoberta futura para sites sem busca: [API SearXNG](https://docs.searxng.org/dev/search_api.html), estudada somente como alternativa de arquitetura. A operação e os termos dos mecanismos subjacentes precisam ser avaliados antes da ativação. Não há servidor de busca geral ou contratação de API nesta entrega.
