-- =====================================================================
-- Montador de Itens de LoL — servidor das builds publicadas
-- O banco INTEIRO, na forma de hoje, num arquivo só (F13-T87, 26/10/2026;
-- o limite por IP desde a F13-T88; o card na hora desde a F13-T109).
--
-- Cole este arquivo inteiro no SQL Editor do Supabase e clique em Run.
-- Serve para as duas coisas:
--   • projeto novo: cria tudo do zero;
--   • projeto que já está no ar: pode colar de novo sem medo. Nenhuma build e
--     nenhum evento é apagado; as views e as funções são recriadas iguais.
--
-- Antes da T87 o banco era este arquivo MAIS runas_e_habilidades.sql e
-- rota.sql, rodados por cima. Colar só o antigo (como o README mandava)
-- derrubava as Públicas: a view voltava sem runas, habilidades e rota, o
-- "revoke" tirava o grant dessas colunas ("permission denied for table builds",
-- o bug de 20/09/2026) e nascia um segundo publicar_build ("function is not
-- unique"). Agora tudo está aqui; os dois arquivos ficam só como histórico.
--
-- REGRA para mudar o banco: a mudança entra AQUI (tabela, view, grant e
-- função), na forma final. Coluna nova na builds_publicas = coluna no grant
-- por coluna da seção 4 (senão a view inteira cai com "permission denied").
-- A limpeza diária dos eventos (pg_cron) mora em limpeza.sql — é opcional.
-- =====================================================================

create extension if not exists pgcrypto with schema extensions;   -- digest() e gen_random_bytes() vivem em "extensions" no Supabase

-- ---------------------------------------------------------------------
-- 1. As builds publicadas. O segredo de quem publicou fica só como hash:
-- quem tem o segredo (guardado no navegador do autor) pode atualizar e
-- apagar; todo o resto só lê.
-- ---------------------------------------------------------------------
create table if not exists public.builds (
  id             text primary key,                       -- id curto (6 caracteres), gerado aqui
  nome           text not null,
  descricao      text not null,
  campeao        jsonb,                                   -- {"key":"222","id":"Jinx","name":"Jinx"} ou null (todos)
  modo           text not null default '',
  marcadores     jsonb not null default '[]'::jsonb,      -- os 3 marcadores
  caixas         jsonb not null,                          -- categorias com itens (formato do Montador)
  patch          text not null,                           -- versão do catálogo na publicação (≠ atual → "desatualizada")
  versao         integer not null default 1,              -- soma 1 a cada publicação da mesma build
  autor          text not null default '',                -- F13-T83: o apelido opcional de quem publicou
  segredo_hash   text not null,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  visualizacoes  integer not null default 0,
  copias         integer not null default 0,
  layout         text not null default 'tabuleiro',       -- Fase 9: tabuleiro | nucleo | trilha | grade
  runas          jsonb not null default '{}'::jsonb,      -- F12 (20/09/2026): a página de runas
  habilidades    jsonb not null default '[]'::jsonb,      -- F12 (20/09/2026): a ordem de habilidades
  rota           text not null default ''                 -- F13-T69 (24/10/2026): '' (qualquer), top, selva, meio, atirador, suporte
);
-- Projeto criado antes de cada coluna: elas entram aqui, vazias. Nenhuma
-- build existente muda; ganha o valor na próxima vez que for publicada.
alter table public.builds add column if not exists layout text not null default 'tabuleiro';
alter table public.builds add column if not exists runas jsonb not null default '{}'::jsonb;
alter table public.builds add column if not exists habilidades jsonb not null default '[]'::jsonb;
alter table public.builds add column if not exists rota text not null default '';

-- ---------------------------------------------------------------------
-- 2. Os eventos, para o "popular hoje / da semana" (Fase 10, T15; Leo, 16/09/2026):
--   impressao   — a build apareceu na lista
--   detalhe     — alguém abriu os detalhes  (era "visualizacao"; o nome antigo continua valendo)
--   engajamento — qualquer interação: clique, favorito, filtro pela build
--   copia       — alguém copiou a build
-- ---------------------------------------------------------------------
create table if not exists public.eventos (
  id        bigserial primary key,
  build_id  text not null references public.builds(id) on delete cascade,
  tipo      text not null,
  quando    timestamptz not null default now()
);
alter table public.eventos drop constraint if exists eventos_tipo_check;
alter table public.eventos add constraint eventos_tipo_check
  check (tipo in ('impressao', 'detalhe', 'engajamento', 'copia', 'visualizacao'));
create index if not exists eventos_build_quando on public.eventos (build_id, quando desc);
create index if not exists eventos_quando on public.eventos (quando desc);

-- ---------------------------------------------------------------------
-- 2b. O limite por IP (F13-T88; Leo, 26/10/2026: "até 5 por IP"). O mesmo IP
-- conta a mesma build, no mesmo tipo, no máximo 5 vezes por dia. O IP nunca é
-- gravado: fica um código (sha256 do IP com o sal do dia, aleatório). O sal e
-- as contagens somem no primeiro evento do dia seguinte — sem o sal, o código
-- não volta a ser IP. Ninguém de fora lê nem escreve nestas duas tabelas.
-- ---------------------------------------------------------------------
create table if not exists public.sal_do_dia (
  dia  date primary key,
  sal  text not null
);
create table if not exists public.eventos_por_ip (
  dia       date not null,
  ip_hash   text not null,
  build_id  text not null references public.builds(id) on delete cascade,
  tipo      text not null,
  n         integer not null default 0,
  primary key (dia, ip_hash, build_id, tipo)
);

-- Quanto cada medida vale na popularidade. Cópia pesa mais porque custa mais
-- ao usuário; impressão pesa pouco porque acontece sozinha ao rolar a lista.
create or replace function public.peso_evento(p_tipo text) returns int
language sql immutable set search_path = public, extensions as $$
  select case p_tipo
    when 'impressao'   then 1
    when 'detalhe'     then 3
    when 'visualizacao' then 3
    when 'engajamento' then 4
    when 'copia'       then 8
    else 0 end;
$$;

-- A semana vai de domingo 09:00 a domingo 09:00 (Leo, 16/09/2026), no fuso de Brasília.
create or replace function public.inicio_semana() returns timestamptz
language plpgsql stable set search_path = public, extensions as $$
declare t timestamp; d int; base timestamp;
begin
  t := now() at time zone 'America/Sao_Paulo';
  d := extract(dow from t)::int;
  base := date_trunc('day', t) - make_interval(days => d) + interval '9 hours';
  if base > t then base := base - interval '7 days'; end if;
  return base at time zone 'America/Sao_Paulo';
end $$;

-- ---------------------------------------------------------------------
-- 3. Ninguém mexe nas tabelas direto: só pelas funções e pelas views.
-- ---------------------------------------------------------------------
alter table public.builds  enable row level security;
alter table public.eventos enable row level security;
-- ATENÇÃO: o "revoke all" tira também os grants POR COLUNA. Por isso a lista
-- inteira de colunas é dada de novo logo abaixo, no mesmo arquivo.
revoke all on public.builds  from anon, authenticated;
revoke all on public.eventos from anon, authenticated;
-- o limite por IP: sem política nenhuma e sem grant — só o registrar_evento mexe
alter table public.sal_do_dia     enable row level security;
alter table public.eventos_por_ip enable row level security;
revoke all on public.sal_do_dia, public.eventos_por_ip from anon, authenticated;

-- ---------------------------------------------------------------------
-- 4. O que o público lê. As views rodam com a permissão de quem lê
-- (security_invoker), como o verificador do Supabase pede; por isso o público
-- ganha SELECT só nas colunas públicas da tabela (o hash do segredo fica de
-- fora) e nos eventos.
-- ---------------------------------------------------------------------
drop policy if exists "leitura publica das builds" on public.builds;
create policy "leitura publica das builds" on public.builds for select to anon, authenticated using (true);
drop policy if exists "leitura publica dos eventos" on public.eventos;
create policy "leitura publica dos eventos" on public.eventos for select to anon, authenticated using (true);
-- Grant POR COLUNA: toda coluna que a builds_publicas mostra tem de estar aqui,
-- senão a view inteira responde "permission denied for table builds".
grant select (id, nome, descricao, campeao, modo, marcadores, caixas, patch, versao, autor, criado_em, atualizado_em,
              visualizacoes, copias, layout, runas, habilidades, rota)
  on public.builds to anon, authenticated;
grant select on public.eventos to anon, authenticated;

-- Pontos por build e por dia (fuso de Brasília), já com os pesos aplicados.
create or replace view public.pontos_por_dia with (security_invoker = true) as
select e.build_id,
       ((e.quando at time zone 'America/Sao_Paulo')::date) as dia,
       sum(public.peso_evento(e.tipo))::int as pontos
from public.eventos e
group by 1, 2;

-- Os dez do dia, dia a dia. Serve para o "popular hoje" e para contar os
-- três dias seguidos que promovem a build a "popular da semana".
create or replace view public.top_do_dia with (security_invoker = true) as
select dia, build_id, pontos,
       row_number() over (partition by dia order by pontos desc, build_id) as posicao
from public.pontos_por_dia;

-- Quem ficou no top 10 em três dias seguidos dentro da semana corrente leva o
-- selo "popular da semana" até o próximo domingo 09:00.
create or replace view public.destaques_semana with (security_invoker = true) as
with marcados as (
  select build_id, dia
  from public.top_do_dia
  where posicao <= 10
    and dia >= ((public.inicio_semana() at time zone 'America/Sao_Paulo')::date)
), seq as (
  select build_id, dia, (dia - (row_number() over (partition by build_id order by dia))::int) as grupo
  from marcados
)
select build_id, max(n) as dias_seguidos
from (select build_id, grupo, count(*)::int as n from seq group by 1, 2) t
group by build_id;

-- A view que a página lê: tudo menos o hash. Recriada inteira a cada Run (o
-- Postgres não deixa acrescentar coluna no meio de uma view); não guarda dado.
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
grant select on public.pontos_por_dia, public.top_do_dia, public.destaques_semana to anon, authenticated;

-- ---------------------------------------------------------------------
-- 5. Publicar (nova) ou atualizar (com o segredo). Regras do Leo: itens,
-- nome, descrição e 3 marcadores; senão, erro.
-- ---------------------------------------------------------------------
-- Só pode existir UM publicar_build: com duas versões no banco, uma chamada
-- casaria com as duas (os parâmetros novos têm default) e o PostgREST
-- responderia "function is not unique". Saem as de antes: 10 parâmetros
-- (Fase 8), 11 (o layout, Fase 9) e 13 (runas e habilidades, 20/09/2026).
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text);
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text);
drop function if exists public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text, jsonb, jsonb);
-- Os parâmetros novos têm default: um navegador com a página antiga continua
-- publicando, só que sem eles.
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

create or replace function public.apagar_build(p_id text, p_segredo text) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare v_n int;
begin
  delete from public.builds where id = p_id and segredo_hash = encode(digest(p_segredo, 'sha256'), 'hex');
  get diagnostics v_n = row_count;
  return v_n > 0;
end $$;

-- Registra o evento e mantém os dois contadores antigos (visualizacoes e copias),
-- que continuam existindo na tabela mas não aparecem mais na tela (F10-T15).
-- F13-T88: até 5 por IP, por build, por tipo, por dia (seção 2b); da 6ª em
-- diante a chamada é aceita e nada é registrado. O IP vem do cabeçalho do
-- Cloudflare (cf-connecting-ip: quem chama não consegue forjar nem tirar; chega
-- em todas as chamadas, conferido nos logs em 26/10/2026); o x-forwarded-for só
-- se ele faltar. Sem IP nenhum (chamada de dentro do banco), conta como antes.
create or replace function public.registrar_evento(p_id text, p_tipo text) returns void
language plpgsql security definer set search_path = public, extensions as $$
declare
  v_cab json; v_ip text; v_dia date; v_sal text; v_n int;
begin
  if p_tipo not in ('impressao', 'detalhe', 'engajamento', 'copia', 'visualizacao') then
    raise exception 'Tipo inválido.';
  end if;
  v_cab := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  v_ip := coalesce(nullif(trim(v_cab->>'cf-connecting-ip'), ''),
                   nullif(trim(split_part(coalesce(v_cab->>'x-forwarded-for', ''), ',', 1)), ''));
  if v_ip is not null then
    v_dia := (now() at time zone 'America/Sao_Paulo')::date;
    -- o sal do dia nasce no primeiro evento do dia; nessa hora o de antes e as
    -- contagens de antes vão embora (os códigos antigos não voltam mais a IP)
    insert into public.sal_do_dia (dia, sal) values (v_dia, encode(gen_random_bytes(16), 'hex'))
      on conflict (dia) do nothing;
    if found then
      delete from public.eventos_por_ip where dia < v_dia;
      delete from public.sal_do_dia where dia < v_dia;
    end if;
    select sal into v_sal from public.sal_do_dia where dia = v_dia;
    insert into public.eventos_por_ip as c (dia, ip_hash, build_id, tipo, n)
      values (v_dia, encode(digest(v_ip || '|' || v_sal, 'sha256'), 'hex'), p_id, p_tipo, 1)
      on conflict (dia, ip_hash, build_id, tipo) do update set n = c.n + 1
      returning c.n into v_n;
    if v_n > 5 then return; end if;
  end if;
  insert into public.eventos (build_id, tipo) values (p_id, p_tipo);
  if p_tipo in ('detalhe', 'visualizacao') then
    update public.builds set visualizacoes = visualizacoes + 1 where id = p_id;
  elsif p_tipo = 'copia' then
    update public.builds set copias = copias + 1 where id = p_id;
  end if;
end $$;

grant execute on function public.publicar_build(text, text, jsonb, text, jsonb, jsonb, text, text, text, text, text, jsonb, jsonb, text) to anon, authenticated;
grant execute on function public.apagar_build(text, text) to anon, authenticated;
grant execute on function public.registrar_evento(text, text) to anon, authenticated;
grant execute on function public.peso_evento(text), public.inicio_semana() to anon, authenticated;

-- ---------------------------------------------------------------------
-- 5b. O card na hora (F13-T109, 02/11/2026; a etapa 3 do card do Discord): publicar,
-- atualizar ou apagar uma build avisa o robô dos cards no GitHub (repository_dispatch
-- "build-publicada"), e o card fica pronto em um ou dois minutos — antes esperava a
-- rodada de meia em meia hora, que o GitHub atrasa por horas. O token do GitHub mora no
-- Vault com o nome github_cards e quem o guarda é o Leo (SQL Editor:
-- select vault.create_secret('<token>', 'github_cards');) — nunca aparece aqui, na
-- página nem no repositório. Sem o token, o gatilho não faz nada. O aviso nunca trava a
-- publicação: qualquer erro é engolido. O update só dispara pelas colunas de conteúdo —
-- os contadores (visualizacoes, copias) mudam a cada visita e não chamam o robô.
-- ---------------------------------------------------------------------
create extension if not exists pg_net;

create or replace function public.avisar_robo_dos_cards() returns trigger
language plpgsql security definer set search_path = public, extensions as $$
declare
  v_token text; v_id text;
begin
  v_id := case when tg_op = 'DELETE' then old.id else new.id end;
  begin
    select decrypted_secret into v_token from vault.decrypted_secrets where name = 'github_cards' limit 1;
    if coalesce(v_token, '') = '' then return null; end if;
    perform net.http_post(
      url := 'https://api.github.com/repos/Brelgo/forja/dispatches',
      body := jsonb_build_object('event_type', 'build-publicada', 'client_payload', jsonb_build_object('id', v_id, 'acao', lower(tg_op))),
      headers := jsonb_build_object('Authorization', 'Bearer ' || v_token, 'Accept', 'application/vnd.github+json',
                                    'X-GitHub-Api-Version', '2022-11-28', 'User-Agent', 'forja-robo-dos-cards', 'Content-Type', 'application/json'),
      timeout_milliseconds := 5000);
  exception when others then
    return null;
  end;
  return null;
end $$;

revoke all on function public.avisar_robo_dos_cards() from public, anon, authenticated;

drop trigger if exists avisar_cards_ao_publicar on public.builds;
create trigger avisar_cards_ao_publicar after insert on public.builds
  for each row execute function public.avisar_robo_dos_cards();
drop trigger if exists avisar_cards_ao_mudar on public.builds;
create trigger avisar_cards_ao_mudar after update of nome, descricao, campeao, modo, marcadores, caixas, patch, autor, layout, runas, habilidades, rota on public.builds
  for each row execute function public.avisar_robo_dos_cards();
drop trigger if exists avisar_cards_ao_apagar on public.builds;
create trigger avisar_cards_ao_apagar after delete on public.builds
  for each row execute function public.avisar_robo_dos_cards();

-- ---------------------------------------------------------------------
-- 6. Confere (rode à parte, se quiser):
-- select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.proname = 'publicar_build';            -- tem de ser 1
-- select id, nome, runas, habilidades, rota, engajamentos from public.builds_publicas limit 5;
-- ---------------------------------------------------------------------
