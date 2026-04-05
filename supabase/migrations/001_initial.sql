-- ============================================================
-- Crystal Presentes — Migration 001 — Schema Inicial
-- Executar no SQL Editor do Supabase
-- ============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ============================================================
-- TABELA: products
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name              TEXT        NOT NULL,
  supplier          TEXT,                             -- interno, nunca exibido ao público
  age_range         TEXT        NOT NULL
                    CHECK (age_range IN ('0-3', '3-6', '7-10', '10-12', '12+')),
  gender            TEXT        NOT NULL DEFAULT 'ambos'
                    CHECK (gender IN ('meninos', 'meninas', 'ambos')),
  description       TEXT,
  niche             TEXT        NOT NULL
                    CHECK (niche IN ('Educativo', 'Jogos', 'Bonecas', 'Cartelados', 'Festividades', 'Puzzle')),
  retail_price      NUMERIC(10,2) NOT NULL,           -- exibido no catálogo público
  wholesale_price   NUMERIC(10,2),                   -- restrito: painel + agente
  min_wholesale_qty INTEGER,                          -- qtd mínima para preço atacado
  photos            TEXT[]      DEFAULT '{}',         -- URLs Supabase Storage
  status            TEXT        NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'inactive', 'featured')),
  availability      TEXT        NOT NULL DEFAULT 'disponivel'
                    CHECK (availability IN ('disponivel', 'em_falta')),
  search_vector     TSVECTOR,                         -- full-text search
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABELA: pre_orders
-- ============================================================
CREATE TABLE IF NOT EXISTS pre_orders (
  id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_name    TEXT,
  customer_phone   TEXT         NOT NULL,
  customer_type    TEXT         CHECK (customer_type IN ('varejo', 'atacado')),
  items            JSONB        NOT NULL DEFAULT '[]', -- [{product_id, name, qty, unit_price}]
  total_retail     NUMERIC(10,2),
  total_wholesale  NUMERIC(10,2),
  status           TEXT         NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'attended', 'closed')),
  notes            TEXT,
  created_at       TIMESTAMPTZ  DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_products_niche        ON products(niche);
CREATE INDEX IF NOT EXISTS idx_products_age_range    ON products(age_range);
CREATE INDEX IF NOT EXISTS idx_products_gender       ON products(gender);
CREATE INDEX IF NOT EXISTS idx_products_status       ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_availability ON products(availability);
CREATE INDEX IF NOT EXISTS idx_products_search       ON products USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_pre_orders_status  ON pre_orders(status);
CREATE INDEX IF NOT EXISTS idx_pre_orders_created ON pre_orders(created_at DESC);

-- ============================================================
-- FULL-TEXT SEARCH — atualiza search_vector automaticamente
-- ============================================================
CREATE OR REPLACE FUNCTION update_product_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector(
    'portuguese',
    unaccent(COALESCE(NEW.name, '')) || ' ' || unaccent(COALESCE(NEW.description, ''))
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_search ON products;
CREATE TRIGGER trg_product_search
  BEFORE INSERT OR UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION update_product_search_vector();

-- ============================================================
-- UPDATED_AT automático
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE products   ENABLE ROW LEVEL SECURITY;
ALTER TABLE pre_orders ENABLE ROW LEVEL SECURITY;

-- products: anon lê apenas produtos ativos/destaque
DROP POLICY IF EXISTS "anon_read_active_products" ON products;
CREATE POLICY "anon_read_active_products"
  ON products FOR SELECT
  TO anon
  USING (status IN ('active', 'featured'));

-- products: service_role tem acesso total (bypassa RLS por padrão)

-- pre_orders: anon NÃO lê pedidos
DROP POLICY IF EXISTS "anon_no_read_pre_orders" ON pre_orders;
CREATE POLICY "anon_no_read_pre_orders"
  ON pre_orders FOR SELECT
  TO anon
  USING (false);

-- pre_orders: agente (service_role via n8n) cria pedidos — service_role bypassa RLS
-- Nenhuma policy adicional necessária para service_role

-- ============================================================
-- STORAGE — criar bucket via dashboard do Supabase:
-- Nome: product-images | Público: SIM | Max size: 5MB
-- Allowed MIME types: image/jpeg, image/png, image/webp
-- ============================================================
