# CRM com SQLite

Demo de CRM que conecta uma interface em JavaScript a uma API HTTP local em Python e a um banco SQLite. Permite cadastrar oportunidades fictícias, mudar a etapa, filtrar retornos vencidos ou previstos para hoje e excluir registros. O banco começa vazio e preserva as alterações entre reinicializações.

## Executar

Use Python 3.10+ e execute `python servidor.py`. Abra `http://127.0.0.1:8000` no navegador. Para escolher outra porta ou banco, use `--porta` e `--banco`.

A API expõe GET e POST em `/api/leads`, e PATCH e DELETE em `/api/leads/<id>`. POST e PATCH recebem JSON com `title`, `stage` e `date` no formato ISO. As etapas são Novo contato, Qualificação, Proposta enviada e Fechado. PATCH atualiza o registro usando os três campos. A interface usa apenas essa API local.

A aplicação escuta apenas em 127.0.0.1 e foi projetada para demonstração individual com dados fictícios. O diretório do banco não é servido pelo aplicativo.
