# 0006 — Provenance

Status: aceita. Cada pesquisa guarda pergunta, interpretação, queries exatas, endpoint, parâmetros, timestamps UTC, hash SHA-256 da resposta, IDs recuperados/selecionados, vínculos, provider e versão do pipeline. Eventos salvos durante execução, inclusive falhas. Dados normalizados e abstracts ficam no SQLite local; a resposta bruta não é redistribuída. Hash documenta integridade, não permite reconstruir a resposta original nem prova validade científica.

Reexecutar uma query pode produzir resultados diferentes: o índice é mutável. Exportação sem textos protegidos é o padrão. Banco local contém perguntas; não usar dados identificáveis de pacientes. Tarefas interrompidas pelo processo são marcadas como falhas na próxima inicialização; fila durável distribuída fica fora do marco.
