# Dependências e origem

Nenhum código ou prompt de Feynman, PaperQA ou Open Deep Research foi incorporado. Referências arquiteturais e revisões estão em docs/research/landscape.md.

Licenças declaradas verificadas nos metadados oficiais PyPI em 2026-09-23 antes de instalar:

| Dependência | Licença | Origem |
|---|---|---|
| FastAPI | MIT | https://pypi.org/project/fastapi/ |
| Pydantic | MIT | https://pypi.org/project/pydantic/ |
| HTTPX | BSD-3-Clause | https://pypi.org/project/httpx/ |
| Uvicorn | BSD-3-Clause | https://pypi.org/project/uvicorn/ |
| pytest (desenvolvimento) | MIT | https://pypi.org/project/pytest/ |
| setuptools (build) | MIT | https://pypi.org/project/setuptools/ |

Licenças/avisos completos permanecem nas distribuições instaladas. Inventário exato, incluindo transitivas, será gerado em docs/dependency-licenses.json. Não remover os diretórios de licença ao redistribuir wheels/imagens. Python e SQLite conservam suas próprias licenças. Não há dependências frontend.

Inventário transitivo conferido após resolução: MIT (annotated-doc/types, anyio, exceptiongroup, h11, iniconfig, pluggy, pydantic-core, tomli, typing-inspection), BSD-3-Clause (click, colorama, httpcore, idna, Starlette), BSD-2-Clause (Pygments), Apache-2.0 OR BSD-2-Clause (packaging), PSF-2.0 (typing_extensions), MPL-2.0 (certifi). Certifi é distribuído sem alterações com sua licença nos metadados do wheel; eventual modificação exige cumprir MPL nos arquivos abrangidos. Essa licença não relicencia o núcleo XPesquisa.

Automação CI referencia actions/checkout e actions/setup-python (MIT), sem copiar seu código. Origem/licenças: https://github.com/actions/checkout/blob/main/LICENSE e https://github.com/actions/setup-python/blob/main/LICENSE. O workflow está preparado localmente; não foi executado no GitHub.
