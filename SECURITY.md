# Segurança

Versão experimental para uma pessoa em máquina confiável, ligada a loopback por padrão. Sem autenticação ou isolamento entre usuários: não exponha à internet. Não insira dados identificáveis de pacientes. Perguntas e resultados ficam no disco local; cópias e permissões são responsabilidade do operador.

Não publique segredos ou exploração ativa em relatórios públicos. Ainda não há canal privado de segurança definido: entre em contato por canal privado já conhecido com o mantenedor Xdiag antes de transmitir detalhes sensíveis. Não há SLA de correção nesta fase.

Fontes e saídas LLM são dados não confiáveis. Interface usa textContent, URLs de fontes são construídas a partir de identificadores, nenhuma ferramenta executa código de documentos. Referências devem pertencer ao catálogo recuperado. Texto conferido não significa conclusão clínica validada. Providers externos futuros exigem revisão de privacidade; não há telemetria neste projeto.
