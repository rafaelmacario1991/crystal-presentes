# Projeto Crystal Presentes — Contexto Técnico e Operacional

## Visão Geral
A **Crystal Presentes** é uma loja de brinquedos localizada no centro do Recife-PE, atuando em varejo e atacado, com presença consolidada no Instagram (40.000 seguidores). O projeto contempla dois entregáveis principais:

1. **Site Catálogo + Painel Administrativo** — vitrine digital pública e interface restrita de gestão de produtos
2. **Agente de IA via WhatsApp** — atendente virtual integrado ao n8n + WhatsApp Business Cloud API, com montagem de pré-pedidos sem fechamento de pagamento

O catálogo é a fonte de dados central: alimenta o frontend público e o agente de IA.

---

## Stack

- **Backend:** FastAPI + Jinja2 (SSR) + Python 3.11
- **Frontend:** HTML/CSS + Alpine.js (sem framework JS pesado)
- **Banco de dados:** Supabase (PostgreSQL + Storage para imagens)
- **Agente de IA:** n8n + WhatsApp Business Cloud API + Supabase (service role key restrita ao n8n)
- **Infraestrutura:** VPS Hostinger (mesma do MK Report), Nginx, SSL Let's Encrypt / Certbot
- **Deploy:** `python deploy/_ssh_deploy.py` (paramiko SSH) — steps: 3 (git pull) + 6 (restart serviço). Não usar `deploy/setup_ssl.py` como nome para scripts novos (era `_ssl.py`, renomeado pois conflitava com o módulo builtin `_ssl` do Python).

---

## Repositório e Deploy

- **GitHub:** https://github.com/rafaelmacario1991/crystal-presentes
- **Domínio:** crystalpresentes.com.br (já adquirido, SSL ativo via Certbot)
- **Supabase URL:** https://qltfwxmflygyrobvwqxw.supabase.co
- **Supabase Anon Key:** sb_publishable_PtCxpU9f3M70teEyfS8u3A_dxSMeYi0
- **VPS:** mesma do MK Report (72.62.10.198)
- **App dir:** /home/crystal
- **Env file:** /home/crystal/backend/.env
- **Serviço systemd:** `crystalpresentes`
- **Nginx:** novo server block para crystalpresentes.com.br (não conflita com MK Report)
- **Deploy:** script PowerShell via SSH (a criar em `deploy/update-vps.ps1`)

---

## Estrutura do Banco (Supabase)

### Tabela: `products`
```sql
CREATE TABLE products (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name             TEXT NOT NULL,
  supplier         TEXT,                        -- interno, nunca exibido ao público
  age_range        TEXT NOT NULL,               -- '0-3' | '3-6' | '7-10' | '10-12' | '12+'
  gender           TEXT DEFAULT 'ambos',        -- 'meninos' | 'meninas' | 'ambos'
  description      TEXT,
  niche            TEXT NOT NULL,               -- ver lista de nichos abaixo
  retail_price     NUMERIC(10,2) NOT NULL,      -- exibido no catálogo público
  wholesale_price  NUMERIC(10,2),               -- restrito: painel admin + agente
  min_wholesale_qty INTEGER,                    -- quantidade mínima para preço atacado
  photos           TEXT[],                      -- URLs Supabase Storage (mín. 1, máx. 5)
  status           TEXT DEFAULT 'active',       -- 'active' | 'inactive' | 'featured'
  availability     TEXT DEFAULT 'disponivel',   -- 'disponivel' | 'em_falta' (setado pelo admin)
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabela: `pre_orders`
```sql
CREATE TABLE pre_orders (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_name     TEXT,
  customer_phone    TEXT NOT NULL,
  customer_type     TEXT,          -- 'varejo' | 'atacado'
  items             JSONB NOT NULL, -- [{product_id, name, qty, unit_price}]
  total_retail      NUMERIC(10,2),
  total_wholesale   NUMERIC(10,2),
  status            TEXT DEFAULT 'pending', -- 'pending' | 'attended' | 'closed'
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

### Boas práticas Supabase
- **RLS ativo:** acesso público retorna apenas campos visíveis (sem `wholesale_price`, `supplier`, `min_wholesale_qty`)
- **Acesso interno (agente/painel):** via service role key — nunca exposta ao cliente
- **Índices:** `niche`, `age_range`, `status`, `availability`, `gender`
- **Full-text search:** `tsvector` em `name + description` para busca por termo
- **Storage:** bucket público `product-images` para fotos dos produtos

---

## Painel Administrativo

- **Acesso:** 1 único usuário admin — credenciais em `.env` (`ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH`)
- **Autenticação:** login com e-mail + senha, sessão via JWT em cookie httpOnly (sem Supabase Auth)
- **Rota de acesso:** `/admin` (protegida, redireciona para `/admin/login` se não autenticado)

### Funcionalidades do painel
| Funcionalidade | Detalhe |
|---|---|
| CRUD de produtos | Criar, editar, excluir, visualizar |
| Status | Ativo / Inativo / Destaque |
| Disponibilidade | Disponível / Em Falta (campo manual, sem integração de estoque) |
| Upload de fotos | Múltiplas imagens → Supabase Storage (mín. 1, máx. 5) |
| Preview antes de publicar | Visualização do card como aparece no catálogo |
| Gestão de pré-pedidos | Listagem com status: Pendente / Atendido / Encerrado |

### Campos de cadastro de produto
| Campo | Tipo | Visibilidade |
|---|---|---|
| Nome | Texto | Público |
| Fornecedor | Texto livre | Somente admin |
| Faixa Etária | Select | Público |
| Gênero | Select | Público |
| Nicho | Select | Público |
| Descrição | Textarea | Público |
| Preço Varejo | Número | Público |
| Preço Atacado | Número | Somente admin + agente |
| Qtd. Mínima Atacado | Número | Somente admin + agente |
| Fotos | Upload múltiplo | Público |
| Status | Select | Somente admin |
| Disponibilidade | Select | Público (sem qty) |

---

## Site Catálogo (Frontend Público)

### Rotas previstas
| Rota | Descrição |
|---|---|
| `/` | Landing page pública do catálogo |
| `/catalogo` | Grid de produtos com filtros |
| `/produto/{id}` | Página de detalhe do produto |
| `/admin/login` | Login do painel |
| `/admin` | Dashboard admin |
| `/admin/produtos` | Listagem e gestão de produtos |
| `/admin/produtos/novo` | Cadastro de produto |
| `/admin/produtos/{id}/editar` | Edição de produto |
| `/admin/pedidos` | Listagem de pré-pedidos recebidos |

### Funcionalidades do catálogo
- Grid responsivo com cards de produto
- Filtros por: nicho, faixa etária, gênero, disponibilidade
- Busca por texto (nome/descrição)
- Paginação (100–500 produtos — 20 por página)
- Badge "Destaque" e "Em Falta"
- Link compartilhável por produto (para o agente enviar no WhatsApp)
- Preço de atacado **nunca** exibido no frontend público

---

## Nichos, Gênero e Faixas Etárias

### Nichos (categorias principais)
- Educativo
- Jogos
- Bonecas
- Cartelados
- Festividades
- Puzzle

> Sugestão: pesquisar categorias padrão do mercado (ex: ABBrinq, grandes redes) antes do cadastro em massa para validar ou expandir essa lista.

### Gênero
- Meninos
- Meninas
- Ambos (padrão)

### Faixa Etária
- 0–3 anos
- 3–6 anos
- 7–10 anos
- 10–12 anos
- 12+

> Sugestão: verificar se as faixas do INMETRO/ABNT para classificação de brinquedos coincidem com as acima antes de fixar no banco.

---

## Identidade Visual e Design

| Papel | Cor | Descrição |
|---|---|---|
| Background | `#fdf6f8` | Branco rosado suave |
| Surface | `#fff0f4` | Rosa muito claro |
| Accent primário | `#e8728a` | Rosa médio elegante |
| Accent hover | `#d45570` | Rosa mais profundo |
| Texto | `#2d1f24` | Quase preto rosado |
| Texto muted | `#7a6068` | Cinza rosado |

- **Mobile-first** — maioria dos acessos via celular
- **Modo claro** como padrão; modo escuro é opcional
- **Tipografia:** display arredondado/amigável para headings + sans-serif limpa para corpo
- **Sensação:** leve, moderno, acolhedor — evitar visual "brinquedoteca genérica"

---

## Agente de IA (WhatsApp)

### Stack do agente
- n8n (instância existente) — reaproveitamento e adaptação de agentes
- WhatsApp Business Cloud API (WABA a criar/aprovar — responsabilidade do Rafael)
- Supabase (consulta via service role key, restrita ao ambiente n8n)
- LLM para linguagem natural (ajuste sobre agentes já existentes)

### Capacidades do agente
1. Recepcionar e qualificar o cliente (varejo ou atacado)
2. Identificar interesse por nicho, faixa etária ou produto específico
3. Consultar Supabase e retornar produtos filtrados
4. Compartilhar link do catálogo e/ou detalhes de produtos específicos
5. Montar carrinho virtual durante a conversa
6. Exibir resumo do pré-pedido ao finalizar
7. Salvar pré-pedido na tabela `pre_orders`
8. **Notificar equipe via WhatsApp** (número da Crystal) ao criar pré-pedido
9. Encaminhar para atendimento humano finalizar (sem processar pagamento)

### Qualificação de cliente atacado
- Sem obrigatoriedade de CNPJ
- Critério: **quantidade mínima de peças** (definida por produto no campo `min_wholesale_qty`)
- O agente pergunta a quantidade desejada e, se atingir o mínimo, aplica preço atacado

### Limitações (by design)
- Não fecha pedidos
- Não recebe pagamentos
- Não confirma disponibilidade em tempo real (campo `availability` é manual)
- Service role key do Supabase nunca exposta ao cliente

### Fluxo resumido
```
Cliente inicia conversa no WhatsApp
  ↓
Agente saúda e identifica: varejo ou atacado?
  ↓ [Se atacado] → pergunta quantidade desejada → aplica preço correto
Agente pergunta: nicho, faixa etária ou produto específico?
  ↓
Consulta Supabase → retorna produtos filtrados
  ↓
Apresenta produtos com descrição, disponibilidade e preço adequado
  ↓
Cliente seleciona → agente adiciona ao carrinho virtual
  ↓
"Deseja adicionar mais itens?"
  ↓
[Finalizar] → exibe resumo do pré-pedido
  ↓
Salva em pre_orders → notifica equipe Crystal via WhatsApp
  ↓
Atendimento humano assume para pagamento e entrega
```

---

## Infraestrutura e Hospedagem

| Componente | Tecnologia | Status |
|---|---|---|
| VPS | Hostinger (mesma do MK Report) | Existente |
| Domínio | crystalpresentes.com.br | Adquirido |
| SSL | Let's Encrypt / Certbot via Nginx | A configurar |
| Banco de dados | Supabase (cloud) | A configurar (novo projeto ou schema separado) |
| Storage de imagens | Supabase Storage | A configurar |
| Agente de IA | n8n (instância existente) | A adaptar |
| WhatsApp | WhatsApp Business Cloud API | WABA a criar/aprovar (Rafael) |

> **Atenção:** o site Crystal rodará em server block Nginx separado do MK Report, sem conflito de portas. Usar porta distinta para o processo uvicorn (ex: 8001 se MK Report usa 8000).

---

## Marcos e Fases

| Fase | Entregável | Estimativa |
|---|---|---|
| Fase 1 | Estrutura Supabase: tabelas, RLS, Storage | Semana 1 |
| Fase 2 | Painel administrativo com CRUD de produtos | Semanas 1–2 |
| Fase 3 | Site catálogo público (frontend) | Semanas 2–3 |
| Fase 4 | Deploy VPS + domínio + SSL + Nginx | Semana 3 |
| Fase 5 | Agente n8n adaptado + integração Supabase | Semanas 3–4 |
| Fase 6 | Testes integrados + ajustes finos | Semana 4–5 |
| Fase 7 | Go-live + monitoramento inicial | Semana 5 |

---

## Pendências e Decisões em Aberto

| # | Pendência | Impacto |
|---|---|---|
| P1 | ~~Criar repositório GitHub `crystal-presentes`~~ **criado e em uso** | Resolvido |
| P2 | ~~Definir porta uvicorn~~ **porta 8002 (não 8001 — conflito)** | Resolvido |
| P3 | ~~Criar projeto Supabase~~ **projeto criado, migration `source` executada** | Resolvido |
| P4 | WABA criado e aprovado pela Meta | Bloqueia Fase 5 |
| P5 | Quantidade mínima de peças por produto para atacado | Impacta agente e cadastro |
| P6 | Validar lista de nichos com práticas do mercado (ABBrinq/ABNT) | Impacta cadastro em massa |
| P7 | Número WhatsApp da equipe Crystal para notificações | Impacta n8n |
| P8 | Levantar lista de produtos para cadastro inicial | Impacta Fase 2 |

---

## Regras para a IA

- Sempre responder em português brasileiro
- Stack definida: **não sugerir frameworks alternativos** sem solicitação explícita
- `wholesale_price` e `supplier` **nunca** devem aparecer em rotas públicas ou respostas de API sem autenticação
- Antes de qualquer migração de banco, verificar RLS e testar isoladamente
- Nunca inventar dados de produtos, preços ou disponibilidade — se não souber, perguntar
- Deploy sempre via `python deploy/_ssh_deploy.py <step>` — steps 3 (git pull) e 6 (restart) são os mais usados no dia a dia
- Manter consistência visual com a paleta definida — não alterar cores sem solicitação

## Armadilhas Conhecidas

- **Jinja2 + dict com chave `items`:** `pedido.items` resolve para o método `.items()` do dicionário Python. Sempre usar `pedido['items']` para acessar o campo JSONB do banco.
- **Alpine.js + botão dentro de `<a>`:** usar `@click.stop` para evitar que o clique borbulhe para o link pai. Nunca usar `|tojson` dentro de atributos `@click="..."` — as aspas duplas quebram o atributo HTML. Solução correta: `x-data` no botão + `@click.stop` + `$el.dataset.*` para passar dados.
- **`deploy/_ssl.py`:** renomeado para `deploy/setup_ssl.py` pois o nome `_ssl` conflita com o módulo builtin C do Python, causando circular import no paramiko.
- **Supabase key format:** versão `supabase>=2.8` é necessária para aceitar chaves no formato `sb_publishable_*`. Versão 2.7.4 rejeita silenciosamente.
