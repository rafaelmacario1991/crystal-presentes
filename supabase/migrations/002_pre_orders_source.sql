-- Adiciona campo source em pre_orders para rastrear origem do pedido
ALTER TABLE pre_orders
  ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'whatsapp';

-- Atualiza pedidos antigos sem source
UPDATE pre_orders SET source = 'whatsapp' WHERE source IS NULL;
