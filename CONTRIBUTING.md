# Contribuir

Leia README, docs/STATUS.md e ADRs. Crie uma branch com alteração pequena, explique problema, solução, limitações e validação. Rode `python -m pytest`. Mudanças no contrato científico precisam de testes para referências inexistentes, ausência de dados e falhas de fontes. Não use APIs pagas em testes padrão.

Contribuições intencionais seguem Apache-2.0. Só submeta material que possa licenciar; registre origem, versão e licença de dependências em THIRD_PARTY_NOTICES.md. Não envie abstracts, PDFs, dados de pacientes ou chaves em fixtures: use dados sintéticos claramente identificados. Fixtures sintéticas não devem aparecer como resultados reais na interface. Não use scores automáticos como prova de qualidade clínica. Mudanças arquiteturais exigem ADR.

## Colaboração no GitHub privado

É necessário convite de acesso ao repositório [Xdiag-IA/xpesquisa](https://github.com/Xdiag-IA/xpesquisa). O mantenedor concede acesso somente às pessoas escolhidas; não é preciso tornar o projeto público para colaborar.

1. Leia o estado do projeto e abra uma Issue com a proposta ou problema, sem dados sensíveis.
2. Clone o repositório e crie uma branch, por exemplo `feat/nome-da-melhoria`.
3. Implemente uma alteração delimitada, atualize documentação e rode os testes locais.
4. Envie a branch e abra um pull request para `main`, explicando o que mudou e como validou.
5. Aguarde revisão antes da integração. Esta é uma convenção da equipe; proteção obrigatória de branch ainda não foi configurada.

O workflow de testes pode ser iniciado manualmente na aba Actions por quem tiver permissão. Nesta etapa privada ele não roda automaticamente a cada envio, para evitar consumo não planejado de minutos. A execução de CI e seus limites devem ser definidos pelo mantenedor antes de habilitar disparos automáticos. Não publique o repositório, distribua dados locais ou convide terceiros sem autorização da Xdiag.
