-- HISTÓRICO — NÃO RODE ESTE ARQUIVO (F13-T87, 26/10/2026).
-- Ele já foi rodado no projeto em 20/09/2026 e está dentro do supabase.sql, que é o
-- banco inteiro na forma de hoje. Rodá-lo de novo recriaria uma versão velha
-- do publicar_build ao lado da atual ("function is not unique") e uma view
-- sem as colunas mais novas. A linha abaixo para o Run antes de qualquer coisa;
-- o resto fica como registro do que foi feito e por quê.
do $trava$ begin raise exception 'Arquivo histórico: já está no supabase.sql. Não rode este arquivo.'; end $trava$;

-- =====================================================================
-- Build publicada leva também a página de runas e a ordem de habilidades
-- (Leo, 20/09/2026: "no card de builds publicadas não aparecem as runas
-- nem a ordem das habilidades básicas").
--
-- Pode rodar mais de uma vez: tudo é "if not exists" ou "create or replace".
-- Nenhuma build existente é alterada; as duas colunas nascem vazias e a
-- build volta a ter runas na próxima vez que for publicada.
-- =====================================================================

-- 1. as duas colunas novas -------------------------------------------
alter table public.builds add column if not exists runas jsonb not null default '{}'::jsonb;
alter table public.builds add column if not exists habilidades jsonb not null default '[]'::jsonb;

-- 2. publicar_build passa a aceitá-las --------------------------------
-- A versão antiga (11 parâmetros) PRECISA sair: com as duas no banco, uma
-- chamada sem os parâmetros novos casaria com as duas (ambas têm default) e o
-- PostgREST responderia "function is not unique". Rodado em 20/09/2026.
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text);
-- Os dois parâmetros têm default, então um navegador com a página antiga
-- continua publicando normalmente, só que sem runas.
create or replace function public.publicar_build(
  p_nome text, p_descricao text, p_campeao jsonb, p_modo text, p_marcadores jsonb, p_caixas jsonb,
  p_patch text, p_autor text, p_segredo text, p_id text default null, p_layout text default 'tabuleiro',
  p_runas jsonb default '{}'::jsonb, p_habilidades jsonb default '[]'::jsonb
) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare
  v_id text; v_hash text; v_versao int; v_itens int;
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

  if p_id is null then
    loop
      v_id := lower(substr(encode(gen_random_bytes(6), 'hex'), 1, 6));
      exit when not exists (select 1 from public.builds where id = v_id);
    end loop;
    insert into public.builds (id, nome, descricao, campeao, modo, marcadores, caixas, patch, autor, segredo_hash, layout, runas, habilidades)
    values (v_id, trim(p_nome), trim(p_descricao), p_campeao, coalesce(p_modo, ''), p_marcadores, p_caixas, p_patch, coalesce(p_autor, ''), v_hash,
            coalesce(p_layout, 'tabuleiro'), coalesce(p_runas, '{}'::jsonb), coalesce(p_habilidades, '[]'::jsonb));
    v_versao := 1;
  else
    update public.builds
       set nome = trim(p_nome), descricao = trim(p_descricao), campeao = p_campeao, modo = coalesce(p_modo, ''),
           marcadores = p_marcadores, caixas = p_caixas, patch = p_patch, autor = coalesce(p_autor, ''),
           layout = coalesce(p_layout, 'tabuleiro'), runas = coalesce(p_runas, '{}'::jsonb),
           habilidades = coalesce(p_habilidades, '[]'::jsonb),
           versao = versao + 1, atualizado_em = now()
     where id = p_id and segredo_hash = v_hash
     returning id, versao into v_id, v_versao;
    if v_id is null then raise exception 'Build não encontrada ou o segredo não confere.'; end if;
  end if;
  return jsonb_build_object('id', v_id, 'versao', v_versao);
end $$;

-- 3. a view pública mostra as duas -----------------------------------
-- Recriada inteira porque o Postgres não deixa acrescentar coluna no meio
-- de uma view existente. É a mesma da Fase 10 (popularidade), mais duas.
drop view if exists public.builds_publicas;
create view public.builds_publicas with (security_invoker = true) as
select
  b.id, b.nome, b.descricao, b.campeao, b.modo, b.marcadores, b.caixas, b.patch, b.versao, b.autor,
  b.criado_em, b.atualizado_em, b.visualizacoes, b.copias, b.layout,
  b.runas, b.habilidades,
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

-- 3b. E O GRANT DAS DUAS COLUNAS NOVAS -------------------------------
-- BUG DE PRODUÇÃO, achado pelo Leo em 20/09/2026: "permission denied for
-- table builds" na aba Públicas. A view é security_invoker, então quem lê é o
-- anon — e o SELECT do anon em public.builds é **por coluna** (o hash do
-- segredo fica de fora de propósito). Acrescentar coluna na tabela e na view
-- sem acrescentar no grant derruba a view inteira, não só as colunas novas.
-- Regra: toda coluna nova que entrar na builds_publicas entra aqui também.
grant select (runas, habilidades) on public.builds to anon, authenticated;

-- 4. confere ----------------------------------------------------------
-- select id, nome, runas, habilidades from public.builds_publicas limit 5;
-- select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.proname = 'publicar_build';   -- tem de ser 1

-- RODADO no projeto okifbriwwxohkjxhqzfc em 20/09/2026, com o Leo autorizando.
-- Conferido: publicar com runas grava e volta pela view; publicar sem runas
-- (navegador com a página antiga) continua funcionando. As duas provas foram
-- feitas dentro de blocos que abortam no fim, então nada ficou no banco.
