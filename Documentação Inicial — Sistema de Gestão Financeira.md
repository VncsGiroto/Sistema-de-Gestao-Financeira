# Sistema de Gestão Financeira

Sistema web para centralizar, importar, categorizar e analisar dados financeiros pessoais, permitindo ao usuário acompanhar receitas, despesas, contas futuras, investimentos e patrimônio ao longo do tempo.

O projeto será desenvolvido inicialmente como uma **aplicação web responsiva**, deixando a possibilidade de criação de aplicativos mobile para uma segunda etapa.

---

## 1. Objetivo

Criar uma plataforma de gestão financeira pessoal capaz de reunir informações de diferentes fontes, como:

- Contas bancárias;
- Cartões;
- Investimentos;
- Arquivos OFX;
- Holerites;
- APIs bancárias;
- Agregadores financeiros.

O sistema deverá transformar essas informações em uma visão consolidada da situação financeira do usuário.

### Objetivos principais

- Centralizar informações financeiras;
- Automatizar a importação de movimentações;
- Evitar lançamentos duplicados;
- Categorizar receitas e despesas;
- Acompanhar contas futuras;
- Acompanhar investimentos;
- Comparar receitas previstas e recebidas;
- Apresentar indicadores financeiros;
- Permitir consultas por diferentes períodos.

---

# 2. Escopo inicial

## 2.1 Autenticação

O sistema deverá possuir:

- Cadastro de usuário;
- Login;
- Logout;
- Recuperação de senha;
- Alteração de senha;
- Rotas protegidas;
- Controle de sessão;
- Controle de acesso aos próprios dados;
- Criptografia de informações sensíveis.

### Requisitos de segurança

- Senhas armazenadas utilizando hash seguro;
- Nunca armazenar senha em texto puro;
- Tokens/sessões com expiração;
- HTTPS em produção;
- Proteção contra SQL Injection;
- Proteção contra XSS;
- Proteção contra CSRF quando aplicável;
- Rate limiting para autenticação;
- Logs de segurança;
- Separação dos dados entre usuários.

---

# 3. Importação de dados

A importação de dados será uma das partes centrais do sistema.

Inicialmente serão avaliadas quatro possibilidades principais.

## 3.1 Agregadores financeiros

Exemplos:

- Pluggy;
- Belvo;
- Outros agregadores disponíveis no mercado.

### Possíveis vantagens

- Integração com diversos bancos;
- Atualização automática;
- Menor necessidade de implementar integração individual com cada banco;
- Possibilidade de sincronização recorrente.

### Possíveis desvantagens

- Custo;
- Dependência de terceiro;
- Limitações de planos;
- Dependência da disponibilidade das instituições;
- Questões relacionadas a consentimento e segurança.

---

## 3.2 Importação OFX

Permitir que o usuário faça upload de arquivos:

```text
arquivo.ofx
```

O sistema deverá interpretar:

- Data;
- Valor;
- Descrição;
- Identificação da transação;
- Conta;
- Banco;
- Tipo de movimentação;
- Saldo, quando disponível.

### Objetivo

A importação OFX deverá funcionar como uma alternativa independente dos agregadores.

Isso também permitirá que o usuário utilize o sistema mesmo quando determinado banco não estiver disponível em um agregador.

---

## 3.3 APIs dos bancos

Avaliar integração direta com APIs disponibilizadas pelas instituições financeiras.

Essa alternativa deverá ser analisada considerando:

- Disponibilidade da API;
- Autenticação;
- OAuth;
- Open Finance;
- Custos;
- Limitações;
- Manutenção;
- Segurança;
- Necessidade de homologação.

### Observação

Não assumir que cada banco possui uma API pública adequada para integração de aplicativos de terceiros.

Antes da implementação deverá ser levantado banco por banco quais APIs e padrões estão disponíveis.

---

# 4. Sugestões adicionais para importação

Além das opções iniciais, o sistema deverá ser projetado utilizando uma camada de **conectores de importação**.

Exemplo:

```text
                    ┌──────────────┐
                    │   Sistema    │
                    │ Financeiro   │
                    └──────┬───────┘
                           │
                 ┌─────────┴─────────┐
                 │ Importação        │
                 │ / Conectores      │
                 └─────────┬─────────┘
                           │
       ┌───────────┬───────┼────────┬───────────┐
       │           │       │        │           │
      OFX       Pluggy   Belvo    API Banco   Holerite
```

Isso permitirá adicionar novas fontes sem alterar o restante do sistema.

### Interface conceitual

Cada fonte deverá possuir um processo semelhante:

```text
Fonte
 ↓
Importador
 ↓
Normalização
 ↓
Validação
 ↓
Detecção de duplicidade
 ↓
Classificação
 ↓
Persistência
```

---

# 5. Normalização das transações

Independentemente da origem, os dados deverão ser convertidos para um formato interno padrão.

Exemplo:

```json
{
  "date": "2026-09-22",
  "description": "SUPERMERCADO XYZ",
  "amount": 250.5,
  "type": "EXPENSE",
  "account_id": 123,
  "source": "OFX",
  "external_id": "ABC123"
}
```

Dessa forma, o restante do sistema não precisa saber se a informação veio de:

- OFX;
- Pluggy;
- Belvo;
- Banco;
- Holerite;
- Entrada manual.

---

# 6. Detecção de duplicidade

O sistema deverá impedir que uma mesma transação seja importada várias vezes.

Exemplo:

```text
OFX
 ↓
Transação:
22/09/2026
SUPERMERCADO XYZ
R$ 250,50
 ↓
Banco já possui:
22/09/2026
SUPERMERCADO XYZ
R$ 250,50
 ↓
Possível duplicidade
 ↓
Sistema solicita confirmação
```

A identificação poderá considerar uma combinação de:

- ID externo;
- Banco;
- Conta;
- Data;
- Valor;
- Descrição;
- Tipo da transação.

---

# 7. Dashboard financeiro

O sistema deverá possuir um dashboard principal.

## Indicadores

### Saldo

Visualizar:

- Saldo atual;
- Saldo mensal;
- Saldo anual;
- Saldo total.

---

## Receitas

Visualizar:

- Receita mensal;
- Receita anual;
- Receita total;
- Evolução das receitas;
- Origem das receitas.

Exemplo:

```text
Receitas - Setembro/2026

Salário       R$ 8.000,00
Freelance     R$ 1.500,00
Investimentos R$   300,00
-------------------------
Total         R$ 9.800,00
```

---

# 8. Despesas

Visualizar:

- Despesas mensais;
- Despesas anuais;
- Despesas totais;
- Evolução das despesas;
- Despesas por categoria;
- Despesas por estabelecimento;
- Despesas por conta/cartão.

Exemplo:

```text
Despesas - Setembro/2026

Moradia        R$ 2.000
Alimentação    R$ 1.200
Transporte     R$   500
Lazer          R$   400
Outros         R$   300
-----------------------
Total          R$ 4.400
```

---

# 9. Categorias

As transações deverão possuir categorias.

Exemplos:

```text
Moradia
Alimentação
Transporte
Saúde
Educação
Lazer
Assinaturas
Impostos
Investimentos
Salário
Outras receitas
Outras despesas
```

O usuário deverá poder:

- Criar categorias;
- Editar categorias;
- Excluir categorias;
- Alterar categoria de uma transação;
- Criar regras de categorização automática.

---

# 10. Regras automáticas

Uma funcionalidade futura importante será permitir regras.

Exemplo:

```text
Se descrição contém:

IFOOD

então:

Categoria = Alimentação
```

Outro exemplo:

```text
Se descrição contém:

UBER

então:

Categoria = Transporte
```

Isso permitirá que o sistema aprenda progressivamente com as classificações realizadas pelo usuário.

---

# 11. Contas a pagar

O usuário poderá cadastrar contas futuras.

Exemplo:

```text
Internet
Valor: R$ 120
Periodicidade: Mensal
Vencimento: Dia 10
```

Tipos:

- Fixas;
- Variáveis;
- Únicas;
- Recorrentes.

---

# 12. Compras parceladas

O sistema deverá permitir cadastrar compras parceladas.

Exemplo:

```text
Notebook
Valor total: R$ 6.000
Parcelas: 12
Valor parcela: R$ 500
```

O sistema deverá gerar:

```text
Mês 1 → R$ 500
Mês 2 → R$ 500
Mês 3 → R$ 500
...
Mês 12 → R$ 500
```

Essas parcelas deverão aparecer nos respectivos meses como compromissos futuros.

---

# 13. Receitas

O usuário poderá cadastrar receitas manualmente.

Exemplos:

- Salário;
- Freelance;
- Aluguel recebido;
- Dividendos;
- Juros;
- Outras receitas.

Também deverá ser possível cadastrar receitas recorrentes.

---

# 14. Holerites

O sistema deverá permitir importar informações de holerites.

Possíveis formatos:

- PDF;
- CSV;
- XML;
- Integração futura com sistemas de folha.

Informações possíveis:

```text
Salário bruto
INSS
IRRF
Outros descontos
Benefícios
Salário líquido
Data de pagamento
```

---

# 15. Comparação Holerite x Banco

Quando o sistema importar um holerite e já existir uma movimentação bancária correspondente, deverá identificar uma possível duplicidade.

Exemplo:

```text
Holerite

Salário líquido:
R$ 7.850,00

Banco

Crédito:
R$ 7.850,00

Data:
05/09/2026
```

O sistema deverá apresentar:

> Foi encontrada uma possível movimentação correspondente ao salário. Deseja considerar o lançamento do holerite como duplicado?

Opções:

```text
[ Manter ambos ]

[ Descartar lançamento do holerite ]

[ Descartar movimentação bancária ]

[ Revisar ]
```

O sistema **não deverá excluir automaticamente** uma informação sem confirmação do usuário.

---

# 16. Investimentos

O sistema deverá possuir uma área específica para investimentos.

Possíveis tipos:

- Ações;
- ETFs;
- FIIs;
- Renda fixa;
- Tesouro;
- Fundos;
- Criptomoedas;
- Outros ativos.

## Indicadores

Visualizar:

- Patrimônio investido;
- Valor atual;
- Rentabilidade;
- Rendimentos;
- Aportes;
- Resgates;
- Evolução mensal;
- Evolução anual;
- Evolução total.

Exemplo:

```text
Investimentos

Total investido       R$ 50.000
Valor atual            R$ 55.200
Rendimento             R$  5.200
Rentabilidade              10,4%
```

---

# 17. Patrimônio

Uma evolução natural do projeto será possuir uma visão consolidada do patrimônio.

```text
Patrimônio

Conta corrente       R$ 10.000
Poupança              R$  5.000
Investimentos         R$ 55.200
Bens                  R$ 20.000
-----------------------------
Patrimônio bruto      R$ 90.200

Dívidas               R$ 15.000
-----------------------------
Patrimônio líquido    R$ 75.200
```

---

# 18. Histórico financeiro

Todas as movimentações deverão possuir histórico.

O usuário poderá filtrar por:

- Período;
- Categoria;
- Conta;
- Cartão;
- Tipo;
- Origem;
- Valor;
- Descrição.

Exemplo:

```text
01/09/2026 → 30/09/2026

Categoria: Alimentação

Total: R$ 1.250,30
```

---

# 19. Arquitetura inicial

A arquitetura deverá permitir crescimento futuro.

Proposta inicial:

```text
                  ┌─────────────────┐
                  │    Frontend     │
                  │ Web Application │
                  └────────┬────────┘
                           │
                          HTTPS
                           │
                  ┌────────▼────────┐
                  │      API        │
                  │    Backend      │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼─────┐ ┌───▼──────┐
        │ PostgreSQL│ │  Redis   │ │ Storage  │
        │           │ │          │ │ arquivos │
        └───────────┘ └──────────┘ └──────────┘
```

---

# 20. Tecnologia

As tecnologias ainda deverão ser definidas.

## Frontend

Avaliar:

- React;
- Vue;
- Angular;
- Next.js.

Critérios:

- Manutenção;
- Performance;
- Ecossistema;
- Facilidade de desenvolvimento;
- Possibilidade de reutilização futura para aplicativo.

---

## Backend

Avaliar:

- Python + FastAPI;
- Python + Django;
- Node.js + NestJS;
- Java + Spring Boot;
- .NET.

O backend deverá disponibilizar uma API REST.

---

## Banco de dados

Proposta inicial:

**PostgreSQL**

Motivos:

- Open source;
- Robusto;
- Excelente suporte transacional;
- Relacionamentos complexos;
- Bom suporte para consultas analíticas;
- Ecossistema maduro.

---

# 21. API

A API deverá seguir padrões REST.

Exemplos:

```http
POST /api/auth/login

GET /api/accounts

GET /api/transactions

POST /api/transactions

GET /api/categories

GET /api/investments

GET /api/dashboard

GET /api/reports
```

---

# 22. Documentação da API

A API deverá possuir documentação utilizando:

**OpenAPI / Swagger**

A documentação deverá permitir:

- Visualizar endpoints;
- Visualizar parâmetros;
- Visualizar respostas;
- Testar endpoints;
- Visualizar autenticação;
- Visualizar modelos de dados.

Exemplo:

```text
/api/docs
```

---

# 23. Modelo de dados inicial

Entidades principais:

```text
User
 ├── Accounts
 ├── Transactions
 ├── Categories
 ├── RecurringBills
 ├── Installments
 ├── Income
 ├── Investments
 ├── Importations
 └── Documents
```

Possível estrutura:

### users

```text
id
name
email
password_hash
created_at
updated_at
```

### accounts

```text
id
user_id
name
bank
account_type
balance
created_at
updated_at
```

### transactions

```text
id
user_id
account_id
category_id
date
description
amount
type
source
external_id
created_at
updated_at
```

### categories

```text
id
user_id
name
type
created_at
```

### installments

```text
id
user_id
description
total_amount
installments
installment_amount
first_due_date
```

### investments

```text
id
user_id
asset
ticker
quantity
average_price
current_price
```

### imports

```text
id
user_id
source
file_name
status
created_at
processed_at
```

---

# 24. Processamento de importações

As importações deverão possuir status.

```text
RECEIVED
   ↓
PROCESSING
   ↓
VALIDATED
   ↓
IMPORTED
```

Em caso de problema:

```text
FAILED
```

Também deverá existir histórico para permitir auditoria.

---

# 25. Segurança

Dados financeiros são considerados sensíveis.

O projeto deverá adotar segurança desde o início.

### Requisitos

- HTTPS;
- Hash de senha;
- Criptografia de dados sensíveis;
- Controle de sessão;
- Expiração de tokens;
- Controle de acesso;
- Logs;
- Rate limiting;
- Validação de entrada;
- Sanitização;
- Proteção contra ataques comuns;
- Backups;
- Política de retenção de dados.

Credenciais de APIs bancárias **não deverão ser armazenadas em texto puro**.

---

# 26. Testes

O projeto deverá possuir testes automatizados desde o início.

## Testes unitários

Testar individualmente:

- Regras de negócio;
- Cálculos;
- Categorizações;
- Parcelamentos;
- Detecção de duplicidade;
- Importação OFX;
- Processamento de holerites.

---

## Testes de integração

Validar:

```text
API
 ↓
Banco de dados
 ↓
Serviços
```

Exemplos:

- Login;
- Criação de conta;
- Importação;
- Criação de transação;
- Consulta de dashboard.

---

## Testes E2E

Simular o comportamento real do usuário.

Exemplo:

```text
Cadastro
 ↓
Login
 ↓
Criar conta
 ↓
Importar OFX
 ↓
Validar transações
 ↓
Classificar despesas
 ↓
Visualizar dashboard
```

Tecnologias a avaliar:

- Playwright;
- Cypress.

---

# 27. Docker

Todo o ambiente deverá ser executável utilizando Docker.

Exemplo:

```text
docker compose up -d
```

Serviços iniciais:

```text
frontend
backend
postgres
redis
```

Em desenvolvimento:

```text
Docker Compose
```

Em produção:

```text
Docker
+
Reverse Proxy
+
HTTPS
```

---

# 28. CI/CD

O projeto deverá utilizar:

**GitHub Actions**

Pipeline inicial:

```text
Push
  ↓
Lint
  ↓
Testes unitários
  ↓
Testes integração
  ↓
Build
  ↓
Testes E2E
  ↓
Build Docker
  ↓
Deploy
```

---

# 29. Qualidade de código

O projeto deverá utilizar:

- Linter;
- Formatter;
- Type checking quando aplicável;
- Testes automatizados;
- Conventional Commits;
- Pull Requests;
- Code Review;
- Variáveis de ambiente;
- Secrets do GitHub;
- Versionamento semântico.

---

# 30. Ambientes

Deverão existir inicialmente três ambientes:

```text
Development
     ↓
Staging
     ↓
Production
```

### Development

Ambiente local dos desenvolvedores.

### Staging

Ambiente para validação antes da publicação.

### Production

Ambiente utilizado pelos usuários.

---

# 31. Estrutura inicial do projeto

Uma possível estrutura:

```text
finance-manager/
│
├── frontend/
│
├── backend/
│
├── infrastructure/
│   ├── docker/
│   └── nginx/
│
├── tests/
│   ├── e2e/
│   └── integration/
│
├── docs/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── .github/
    └── workflows/
        ├── tests.yml
        └── deploy.yml
```

---

# 32. MVP

Para evitar que o projeto fique grande demais inicialmente, o MVP deverá se concentrar em:

### Obrigatório

- Cadastro/login;
- Contas;
- Receitas;
- Despesas;
- Categorias;
- Importação OFX;
- Detecção de duplicidade;
- Dashboard;
- Contas futuras;
- Parcelamentos;
- PostgreSQL;
- Docker;
- Swagger;
- Testes;
- GitHub Actions.

### Posterior

- Pluggy;
- Belvo;
- APIs bancárias;
- Holerites;
- Investimentos automatizados;
- Aplicativo mobile;
- Regras inteligentes;
- Automação de categorização.

---

# 33. Princípios do projeto

O desenvolvimento deverá seguir alguns princípios:

### 1. Dados pertencem ao usuário

O sistema deve permitir exportar os dados do usuário.

### 2. Não alterar dados automaticamente sem transparência

Importações e possíveis duplicidades devem possuir histórico.

### 3. Segurança desde o início

Segurança não deverá ser uma etapa posterior.

### 4. Fonte independente do sistema

OFX, agregador, banco ou holerite devem ser apenas fontes de dados.

### 5. Arquitetura extensível

Novas fontes de dados devem poder ser adicionadas sem reescrever o sistema.

### 6. Testabilidade

As regras financeiras deverão ser separadas da camada de apresentação.

---

# 34. Documentação

O projeto deverá possuir:

```text
README.md
ARCHITECTURE.md
DATABASE.md
API.md
SECURITY.md
CONTRIBUTING.md
```

O `README.md` deverá conter:

- Descrição;
- Objetivo;
- Tecnologias;
- Como executar;
- Como executar os testes;
- Como executar Docker;
- Link para ambiente de demonstração;
- Link para Swagger;
- Roadmap.

---

# 35. Links

Após a publicação:

```text
Aplicação:
https://...

API:
https://api....

Swagger:
https://api.... /docs

GitHub:
https://github.com/...
```

---

# 36. Decisões ainda pendentes

Antes de iniciar o desenvolvimento definitivo, deverão ser decididos:

| Item          | Decisão             |
| ------------- | ------------------- |
| Frontend      | A definir           |
| Backend       | A definir           |
| Banco         | PostgreSQL sugerido |
| Cache         | A definir           |
| Autenticação  | A definir           |
| JWT/Session   | A definir           |
| Hospedagem    | A definir           |
| Cloud         | A definir           |
| Agregador     | A avaliar           |
| OFX           | Sim                 |
| API bancária  | A avaliar           |
| Open Finance  | A avaliar           |
| Investimentos | A definir escopo    |
| Mobile        | Pós-MVP             |
| CI/CD         | GitHub Actions      |
| Containers    | Docker              |
| API           | REST/OpenAPI        |
| E2E           | Playwright/Cypress  |

---

# 37. Próxima etapa

A próxima etapa recomendada é transformar este documento em uma **especificação técnica do MVP**, definindo:

1. Stack definitiva;
2. Arquitetura;
3. Modelo do banco;
4. Endpoints da API;
5. Fluxo de autenticação;
6. Fluxo de importação OFX;
7. Algoritmo de detecção de duplicidade;
8. Estrutura do frontend;
9. Estratégia de testes;
10. Docker Compose;
11. Pipeline GitHub Actions;
12. Backlog de desenvolvimento.

A partir disso, o projeto poderá ser iniciado pelo repositório e pelo ambiente Docker, antes de começar as funcionalidades financeiras.
