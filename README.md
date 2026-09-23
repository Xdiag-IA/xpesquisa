# XPesquisa

**Plataforma open source de pesquisa e verificação de evidências para profissionais de saúde.**

Projeto da Xdiag Tecnologias, criado no Brasil. Nome provisório. Pesquisa, educação e atualização científica; não é um sistema autônomo de diagnóstico nem substitui julgamento clínico.

## Como este projeto funciona

O GitHub reúne o código, a documentação, as tarefas e as propostas de alteração. O aplicativo roda na máquina de quem o instala e é aberto pelo navegador. A busca consulta o Europe PMC; o histórico fica no banco local. Hospedagem de um serviço compartilhado é uma etapa futura.

O repositório está em desenvolvimento **privado**, acessível apenas a pessoas autorizadas. Apache-2.0 é a licença escolhida para o código; isso não torna o repositório público automaticamente. Uma abertura pública futura depende de decisão da Xdiag. Colaboradores convidados poderão discutir melhorias em Issues e propor alterações por pull requests, seguindo [CONTRIBUTING.md](CONTRIBUTING.md).

Status: MVP exploratório funcional, uso local. Busca real no Europe PMC, metadados, trechos literais de abstracts, citações vinculadas, histórico SQLite, rastreabilidade e exportação de metadados. Veja [estado do projeto](docs/STATUS.md), [panorama](docs/research/landscape.md) e [decisões](docs/adr/0001-project-architecture.md).

## Executar

Python 3.10 ou superior. Não exige Node, conta externa ou API paga.

```powershell
git clone https://github.com/Xdiag-IA/xpesquisa.git
cd xpesquisa
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -c requirements.lock -e ".[dev]"
xpesquisa serve
```

macOS/Linux: use `source .venv/bin/activate` para ativar o ambiente; demais comandos são iguais. Se o PowerShell impedir ativação, execute `.venv\Scripts\python -m pip install -e ".[dev]"` e `.venv\Scripts\python -m xpesquisa.cli serve`.

Abra http://127.0.0.1:8765. Contrato da API em `/docs`. As variáveis em `.env.example` devem ser definidas no ambiente do processo; não há leitura automática de `.env`.

Se a porta estiver ocupada, use `xpesquisa serve --port 8787`. Nesta primeira execução, o aplicativo ficou disponível em **http://127.0.0.1:8787**. O processo que já utilizava 8765 foi preservado.

## Primeira pesquisa

Use o exemplo “Qual é a evidência atual sobre elastografia hepática para avaliação de fibrose?” e clique em **Investigar literatura**. A estratégia usa vocabulário explícito em inglês e registros MED do Europe PMC. Não é um conector direto NCBI/PubMed. Outras perguntas usam a consulta literal; edite a query em inglês para melhores resultados. O planejamento geral com PICO e tradução ainda não está implementado.

Abra **Síntese e achados**, **Fontes** e **Rastreabilidade**. Cada achado liga a um trecho e a um artigo. A consulta de identidade compara ID, título e DOI quando presente, novamente na mesma base. DOI não é resolvido independentemente. Trecho conferido não significa que a fonte sustenta uma inferência, que o estudo tem baixo risco de viés ou que o resultado se aplica à população brasileira.

O padrão não usa LLM: produz uma síntese extrativa, com achados no idioma da fonte e texto explicativo em português. Não produz avaliação clínica integrada. Para experimentar rascunhos em português com um modelo **já instalado** no Ollama:

```powershell
$env:XPESQUISA_PROVIDER="ollama"
$env:XPESQUISA_MODEL="nome-do-seu-modelo-local"
xpesquisa serve --port 8787
```

No macOS/Linux, use `export XPESQUISA_PROVIDER=ollama` e `export XPESQUISA_MODEL=nome-do-seu-modelo-local`. O adapter aceita apenas loopback; nenhuma transferência de modelo ou chamada paga é feita pelo XPesquisa. Provider sem resposta ou com citações inválidas gera fallback extrativo registrado. Nenhum provider pode aprovar validade semântica automaticamente.

## Dados locais e exportação

Banco em `data/xpesquisa.db`, fora do Git. `XPESQUISA_DATA_DIR` muda o diretório. Faça backup com o servidor parado, preservando a pasta de dados. Use somente uma instância por banco. Pesquisas interrompidas são marcadas como falhas no reinício. Histórico mostra as 50 mais recentes; a API por ID preserva acesso às demais.

A exportação JSON contém metadados, IDs, vínculos, consultas, timestamps e hashes; omite abstracts, trechos, textos de afirmações e prompts com conteúdo científico. Não é formato de importação. Os artigos mantêm seus direitos e a licença do código não autoriza republicação. Não contorna paywalls, não busca PDFs e não faz scraping. Internet é necessária para consultas à base; histórico e interface são locais.

## Docker

```text
docker compose up --build
```

Publica somente na interface local, porta 8765, com volume persistente. Para usar outra porta altere o lado esquerdo do mapeamento no Compose. Imagem não validada nesta máquina porque o engine Docker estava indisponível. Não exponha o serviço publicamente: o MVP não tem autenticação multiusuário.

## Limitações atuais

- Seleção pela primeira página da busca, até 20 registros; sem revisão sistemática, ranking metodológico ou garantia de cobertura.
- Sem avaliação GRADE, risco de viés, retratações, extração clínica de população/amostra ou inferência de país. Estudos animais podem aparecer; leia título, tipo e abstract.
- Sem integração brasileira, busca ativa de contraditório ou comparação longitudinal. A interface identifica essas lacunas.
- Busca sem resultados não implica ausência de evidência. Falha de serviço é apresentada como falha, não como resultado vazio.
- Verificação semântica exige revisão humana. LLM opcional produz rascunhos, nunca conclusões validadas.
- Termos e copyright de cada fonte devem ser revistos antes de distribuir conteúdo. Páginas Europe PMC de referência devolveram bloqueio neste ambiente; apenas a API oficial foi utilizada.

## Desenvolvimento

```text
python -m pytest
```

Testes usam mocks sintéticos, sem chamadas externas ou pagas. A prova real está em [docs/validation.md](docs/validation.md); é separada da suíte padrão. `requirements.lock` fixa as versões verificadas; instalação com `-c` aplica essas restrições. CI multiplataforma foi preparada, mas ainda não executada remotamente.

Arquitetura: FastAPI + Pydantic → planejamento → Europe PMC → seleção → extração → verificação → provider → SQLite → interface pt-BR. Módulos em `src/xpesquisa/`; contratos em `models.py`; interface sem CDN em `web/`. Consulte os ADRs para alternativas e consequências. A API é independente de fornecedores de IA e de produtos clínicos da Xdiag.

## Contribuir e licença

[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Código Apache-2.0, conforme [LICENSE](LICENSE); nomes e marcas conforme [TRADEMARKS.md](TRADEMARKS.md). Artigos científicos e dependências mantêm suas próprias licenças. Nenhum projeto externo foi copiado. Repositório: [Xdiag-IA/xpesquisa](https://github.com/Xdiag-IA/xpesquisa), inicialmente privado. O envio do código não publica o aplicativo como serviço web.
