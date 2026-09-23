# XPesquisa

**Plataforma open source de pesquisa e verificação de evidências para profissionais de saúde.**

Projeto da Xdiag Tecnologias, criado no Brasil. Nome provisório. Pesquisa, educação e atualização científica; não é um sistema autônomo de diagnóstico nem substitui julgamento clínico.

Status: desenvolvimento inicial, uso local. Veja [estado do projeto](docs/STATUS.md), [panorama](docs/research/landscape.md) e [decisões](docs/adr/0001-project-architecture.md).

## Executar

Python 3.10 ou superior. Não exige Node, conta externa ou API paga.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
xpesquisa serve
```

macOS/Linux: use `source .venv/bin/activate` para ativar o ambiente; demais comandos são iguais. Se o PowerShell impedir ativação, execute `.venv\Scripts\python -m pip install -e ".[dev]"` e `.venv\Scripts\python -m xpesquisa.cli serve`.

Abra http://127.0.0.1:8765. Contrato da API em `/docs`. As variáveis em `.env.example` devem ser definidas no ambiente do processo; não há leitura automática de `.env`.

## Desenvolvimento

```text
python -m pytest
```

Testes usam mocks, sem chamadas pagas. Arquitetura: FastAPI + Pydantic → pipeline modular → conectores oficiais → SQLite → interface web pt-BR. Consulte os ADRs para alternativas e consequências. A API é independente de fornecedores de IA e de produtos clínicos da Xdiag.

## Contribuir e licença

[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Código Apache-2.0, conforme [LICENSE](LICENSE); nomes e marcas conforme [TRADEMARKS.md](TRADEMARKS.md). Artigos científicos e dependências mantêm suas próprias licenças. Nenhum projeto externo foi copiado. Não há repositório remoto ou publicação configurados.
