-- HISTÓRICO — NÃO RODE ESTE ARQUIVO (F13-T109, 02/11/2026). DESFEITO no mesmo dia.
-- Rodado em 02/11/2026 (a migração mapa_da_build) e desfeito horas depois (desfaz_mapa_da_build): o Leo
-- quer o mapa "publicado totalmente à parte e exclusivo do site, não atrelado às builds". O banco voltou ao
-- do rota.sql (publicar_build de 14 parâmetros, a view sem o mapa, sem a coluna). Os planos de mapa terão
-- tabela própria (F13-T110). A linha abaixo para o Run antes de qualquer coisa.
do $trava$ begin raise exception 'Arquivo histórico: já está no supabase.sql. Não rode este arquivo.'; end $trava$;

-- =====================================================================
-- Build publicada leva também as marcas do mapa (F13-T109, 02/11/2026; Leo:
-- "sim, pode fazer os três" — o texto, o link e a publicação levam as sentinelas
-- da aba Mapa, F13-T108).
--
-- Pode rodar mais de uma vez: tudo é "if not exists", "create or replace" ou
-- "drop … if exists". Nenhuma build existente é alterada: a coluna nasce vazia
-- ({"visao": []}) e a build ganha as marcas na próxima vez que for publicada.
-- Enquanto isto não rodar, o Montador publica sem o mapa (o resto vai igual).
-- Lido do banco antes de escrever (02/11/2026): o publicar_build de hoje é o do
-- rota.sql (14 parâmetros) e a view é a de lá, com security_invoker.
-- =====================================================================

-- 1. a coluna nova ---------------------------------------------------
alter table public.builds add column if not exists mapa jsonb not null default '{"visao": []}'::jsonb;

-- 2. publicar_build passa a aceitá-la ----------------------------------
-- A versão de antes (14 parâmetros, do rota.sql) PRECISA sair: com as duas no
-- banco, uma chamada sem p_mapa casaria com as duas e o PostgREST responderia
-- "function is not unique".
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text, jsonb, jsonb, text);
-- p_mapa tem default: um navegador com a página antiga continua publicando,
-- só que sem o mapa.
create or replace function public.publicar_build(
  p_nome text, p_descricao text, p_campeao jsonb, p_modo text, p_marcadores jsonb, p_caixas jsonb,
  p_patch text, p_autor text, p_segredo text, p_id text default null, p_layout text default 'tabuleiro',
  p_runas jsonb default '{}'::jsonb, p_habilidades jsonb default '[]'::jsonb, p_rota text default '',
  p_mapa jsonb default '{"visao": []}'::jsonb
) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare
  v_id text; v_hash text; v_versao int; v_itens int; v_rota text; v_mapa jsonb; v_marca jsonb;
begin
  if coalesce(trim(p_nome), '') = '' then raise exception 'A build precisa de nome.'; end if;
  if coalesce(trim(p_descricao), '') = '' then raise exception 'A build precisa de descrição.'; end if;
  if jsonb_typeof(p_marcadores) <> 'array' or jsonb_array_length(p_marcadores) < 3 then raise exception 'A build precisa dos 3 marcadores.'; end if;
  if jsonb_typeof(p_caixas) <> 'array' then raise exception 'Caixas inválidas.'; end if;
  select coalesce(sum(jsonb_array_length(c->'items')), 0) into v_itens from jsonb_array_elements(p_caixas) c;
  if v_itens = 0 then raise exception 'A build precisa de itens.'; end if;
  if coalesce(p_segredo, '') = '' then raise exception 'Segredo ausente.'; end if;
  v_hash := encode(digest(p_segredo, 'sha256'), 'hex');

  -- runas e habilidades são opcionais: build sem elas publica igual
  if jsonb_typeof(coalesce(p_runas, '{}'::jsonb)) <> 'object' then raise exception 'Runas inválidas.'; end if;
  if jsonb_typeof(coalesce(p_habilidades, '[]'::jsonb)) <> 'array' then raise exception 'Ordem de habilidades inválida.'; end if;
  -- a rota: uma das cinco, ou vazia (qualquer)
  v_rota := coalesce(p_rota, '');
  if v_rota not in ('', 'top', 'selva', 'meio', 'atirador', 'suporte') then raise exception 'Rota inválida.'; end if;
  -- o mapa: {"visao": [{"t": "sentinela"|"controle", "x": n, "z": n}, …]}, até 40 marcas dentro de
  -- Summoner's Rift (a grade do jogo vai de ~0 a ~14.850 nos dois eixos; folga até 15.000)
  v_mapa := coalesce(p_mapa, '{"visao": []}'::jsonb);
  if jsonb_typeof(v_mapa) <> 'object' or jsonb_typeof(coalesce(v_mapa->'visao', '[]'::jsonb)) <> 'array' then raise exception 'Mapa inválido.'; end if;
  if jsonb_array_length(coalesce(v_mapa->'visao', '[]'::jsonb)) > 40 then raise exception 'Mapa com marcas demais (no máximo 40).'; end if;
  for v_marca in select * from jsonb_array_elements(coalesce(v_mapa->'visao', '[]'::jsonb)) loop
    if jsonb_typeof(v_marca) <> 'object' or coalesce(v_marca->>'t', '') not in ('sentinela', 'controle')
       or jsonb_typeof(v_marca->'x') <> 'number' or jsonb_typeof(v_marca->'z') <> 'number'
       or (v_marca->>'x')::numeric not between -100 and 15000 or (v_marca->>'z')::numeric not between -100 and 15000 then
      raise exception 'Marca do mapa inválida.';
    end if;
  end loop;
  v_mapa := jsonb_build_object('visao', coalesce(v_mapa->'visao', '[]'::jsonb));

  if p_id is null then
    loop
      v_id := lower(substr(encode(gen_random_bytes(6), 'hex'), 1, 6));
      exit when not exists (select 1 from public.builds where id = v_id);
    end loop;
    insert into public.builds (id, nome, descricao, campeao, modo, marcadores, caixas, patch, autor, segredo_hash, layout, runas, habilidades, rota, mapa)
    values (v_id, trim(p_nome), trim(p_descricao), p_campeao, coalesce(p_modo, ''), p_marcadores, p_caixas, p_patch, coalesce(p_autor, ''), v_hash,
            coalesce(p_layout, 'tabuleiro'), coalesce(p_runas, '{}'::jsonb), coalesce(p_habilidades, '[]'::jsonb), v_rota, v_mapa);
    v_versao := 1;
  else
    update public.builds
       set nome = trim(p_nome), descricao = trim(p_descricao), campeao = p_campeao, modo = coalesce(p_modo, ''),
           marcadores = p_marcadores, caixas = p_caixas, patch = p_patch, autor = coalesce(p_autor, ''),
           layout = coalesce(p_layout, 'tabuleiro'), runas = coalesce(p_runas, '{}'::jsonb),
           habilidades = coalesce(p_habilidades, '[]'::jsonb), rota = v_rota, mapa = v_mapa,
           versao = versao + 1, atualizado_em = now()
     where id = p_id and segredo_hash = v_hash
     returning id, versao into v_id, v_versao;
    if v_id is null then raise exception 'Build não encontrada ou o segredo não confere.'; end if;
  end if;
  return jsonb_build_object('id', v_id, 'versao', v_versao);
end $$;

-- 3. a view pública mostra o mapa --------------------------------------
-- Recriada inteira (o Postgres não deixa acrescentar coluna no meio de uma
-- view). É a do rota.sql (24/10/2026), mais o mapa.
drop view if exists public.builds_publicas;
create view public.builds_publicas with (security_invoker = true) as
select
  b.id, b.nome, b.descricao, b.campeao, b.modo, b.marcadores, b.caixas, b.patch, b.versao, b.autor,
  b.criado_em, b.atualizado_em, b.visualizacoes, b.copias, b.layout,
  b.runas, b.habilidades, b.rota, b.mapa,
  -- o único número que aparece na tela (Leo, 16/09/2026): interações de verdade
  coalesce((select count(*) from public.eventos e
             where e.build_id = b.id and e.tipo = 'engajamento'), 0)::int as engajamentos,
  -- popularidade do dia: zera à meia-noite de Brasília, com os pesos de peso_evento
  coalesce((select sum(public.peso_evento(e.tipo))::int from public.eventos e
             where e.build_id = b.id
               and (e.quando at time zone 'America/Sao_Paulo')::date
                   = ((now() at time zone 'America/Sao_Paulo')::date)), 0)::int as pop_dia,
  -- >= 3 dias seguidos no top 10 desta semana; vale até domingo 09:00
  coalesce((select d.dias_seguidos from public.destaques_semana d where d.build_id = b.id), 0)::int as dias_no_top,
  coalesce((select d.dias_seguidos >= 3 from public.destaques_semana d where d.build_id = b.id), false) as popular_semana
from public.builds b;

grant select on public.builds_publicas to anon, authenticated;

-- 3b. o grant da coluna nova (o select do anon em public.builds é por coluna, e
-- sem isto a view inteira cai com "permission denied")
grant select (mapa) on public.builds to anon, authenticated;

-- 4. confere ----------------------------------------------------------
-- select id, nome, mapa from public.builds_publicas limit 5;
-- select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.proname = 'publicar_build';   -- tem de ser 1

-- RODADO em 02/11/2026 pelo Forjador, com a permissão do Leo ("sim, pode fazer os três"),
-- no projeto okifbriwwxohkjxhqzfc, como a migração mapa_da_build. Conferido: um publicar_build só
-- (15 parâmetros; execução para anon e authenticated como antes); a view com security_invoker; as 45
-- públicas legíveis, todas com o mapa vazio; o anon lê a coluna mapa.
-- DESFEITO em 02/11/2026 pelo Forjador, com a escolha do Leo ("Desfazer e criar a dos mapas"): migração
-- desfaz_mapa_da_build. Conferido: um publicar_build só (14 parâmetros), a view com security_invoker, as 45
-- públicas, nenhuma coluna mapa em public.builds.
