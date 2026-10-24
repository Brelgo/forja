-- =====================================================================
-- Build publicada leva também a rota (F13-T69, 24/10/2026; Leo: "seletor na
-- barra da build" — a rota que o cadeado lê).
--
-- Pode rodar mais de uma vez: tudo é "if not exists", "create or replace" ou
-- "drop … if exists". Nenhuma build existente é alterada: a coluna nasce vazia
-- ('' = qualquer rota) e a build ganha a rota na próxima vez que for publicada.
-- Enquanto isto não rodar, o Montador publica sem a rota (o resto vai igual).
-- =====================================================================

-- 1. a coluna nova ---------------------------------------------------
alter table public.builds add column if not exists rota text not null default '';

-- 2. publicar_build passa a aceitá-la ----------------------------------
-- A versão de antes (13 parâmetros, de runas_e_habilidades.sql) PRECISA sair:
-- com as duas no banco, uma chamada sem p_rota casaria com as duas e o
-- PostgREST responderia "function is not unique".
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text, jsonb, jsonb);
-- p_rota tem default: um navegador com a página antiga continua publicando,
-- só que sem a rota.
create or replace function public.publicar_build(
  p_nome text, p_descricao text, p_campeao jsonb, p_modo text, p_marcadores jsonb, p_caixas jsonb,
  p_patch text, p_autor text, p_segredo text, p_id text default null, p_layout text default 'tabuleiro',
  p_runas jsonb default '{}'::jsonb, p_habilidades jsonb default '[]'::jsonb, p_rota text default ''
) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare
  v_id text; v_hash text; v_versao int; v_itens int; v_rota text;
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

  if p_id is null then
    loop
      v_id := lower(substr(encode(gen_random_bytes(6), 'hex'), 1, 6));
      exit when not exists (select 1 from public.builds where id = v_id);
    end loop;
    insert into public.builds (id, nome, descricao, campeao, modo, marcadores, caixas, patch, autor, segredo_hash, layout, runas, habilidades, rota)
    values (v_id, trim(p_nome), trim(p_descricao), p_campeao, coalesce(p_modo, ''), p_marcadores, p_caixas, p_patch, coalesce(p_autor, ''), v_hash,
            coalesce(p_layout, 'tabuleiro'), coalesce(p_runas, '{}'::jsonb), coalesce(p_habilidades, '[]'::jsonb), v_rota);
    v_versao := 1;
  else
    update public.builds
       set nome = trim(p_nome), descricao = trim(p_descricao), campeao = p_campeao, modo = coalesce(p_modo, ''),
           marcadores = p_marcadores, caixas = p_caixas, patch = p_patch, autor = coalesce(p_autor, ''),
           layout = coalesce(p_layout, 'tabuleiro'), runas = coalesce(p_runas, '{}'::jsonb),
           habilidades = coalesce(p_habilidades, '[]'::jsonb), rota = v_rota,
           versao = versao + 1, atualizado_em = now()
     where id = p_id and segredo_hash = v_hash
     returning id, versao into v_id, v_versao;
    if v_id is null then raise exception 'Build não encontrada ou o segredo não confere.'; end if;
  end if;
  return jsonb_build_object('id', v_id, 'versao', v_versao);
end $$;

-- 3. a view pública mostra a rota ------------------------------------
-- Recriada inteira (o Postgres não deixa acrescentar coluna no meio de uma
-- view). É a de runas_e_habilidades.sql (20/09/2026), mais a rota.
drop view if exists public.builds_publicas;
create view public.builds_publicas with (security_invoker = true) as
select
  b.id, b.nome, b.descricao, b.campeao, b.modo, b.marcadores, b.caixas, b.patch, b.versao, b.autor,
  b.criado_em, b.atualizado_em, b.visualizacoes, b.copias, b.layout,
  b.runas, b.habilidades, b.rota,
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

-- 3b. o grant da coluna nova (a regra de runas_e_habilidades.sql: toda coluna
-- nova que entra na builds_publicas entra aqui também — o select do anon em
-- public.builds é por coluna, e sem isto a view inteira cai com "permission denied")
grant select (rota) on public.builds to anon, authenticated;

-- 4. confere ----------------------------------------------------------
-- select id, nome, rota from public.builds_publicas limit 5;
-- select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.proname = 'publicar_build';   -- tem de ser 1

-- RODADO em 24/10/2026 pelo Forjador, com a permissão do Leo ("pode rodar o
-- Supabase"), no projeto okifbriwwxohkjxhqzfc, como a migração rota_da_build.
-- Conferido: um publicar_build só (14 parâmetros, execução para anon e
-- authenticated como antes); a view com security_invoker e as 69 públicas
-- legíveis como anon, todas com rota ''; a REST com a chave publishable responde
-- 200 com a coluna; a chamada com p_rota chega à função (recusada pelo nome vazio,
-- sem gravar nada).
