-- =====================================================================
-- Eventos que o roteiro de QA registrou no servidor de verdade (F13-T56)
-- RODADO em 25/10/2026, com a autorização do Leo: a limpeza do trecho 4 apagou
-- 4.724 impressões e 130 detalhes repetidos (os engajamentos não foram tocados).
-- =====================================================================
-- O que aconteceu: até 19/10/2026 ~16:10, o grupo "públicas" do
-- docs/qa_roteiro.py abria a aba Públicas sem barrar o registrar_evento.
-- O Chrome do roteiro nasce com a memória limpa a cada rodada, então o
-- "uma vez por dia por navegador" do app (jaContouHoje) não segurava nada:
-- cada rodada completa registrava uma 'impressao' (1 ponto) para cada build
-- da lista (até 50) e um 'detalhe' (3 pontos) para a primeira, a que fica
-- selecionada. Desde a F13-T56 o roteiro segura esses eventos na página.
--
-- A tabela public.eventos guarda só build_id, tipo e quando — nada diz quem
-- registrou. O que denuncia o roteiro: o mesmo navegador nunca conta duas
-- impressões (ou dois detalhes) da mesma build no mesmo dia; o roteiro conta
-- de novo a cada rodada. Então o que passa de UM por build, por tipo e por dia
-- veio de outro navegador — quase sempre o roteiro (ou uma visita sua de
-- outro aparelho/janela anônima, ou de outra pessoa).
--
-- COMO USAR: rode este arquivo inteiro no SQL Editor do Supabase. Ele SÓ LÊ:
-- as limpezas estão comentadas (com "--" na frente) e só rodam se você tirar
-- os "--" de propósito, depois de olhar os números.
-- Nada aqui mexe nos engajamentos (o único número que aparece na tela) nem
-- nas cópias.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Só leitura — o retrato: eventos por dia e por tipo
-- ---------------------------------------------------------------------
select (quando at time zone 'America/Sao_Paulo')::date as dia,
       tipo,
       count(*)                 as eventos,
       count(distinct build_id) as builds
from public.eventos
group by 1, 2
order by 1 desc, 2;


-- ---------------------------------------------------------------------
-- 2. Só leitura — as rajadas: cada minuto em que 10 ou mais builds
--    ganharam impressão (uma aba Públicas aberta, sua ou do roteiro).
--    As rodadas completas do roteiro que eu sei a hora (fim da rodada; a aba
--    Públicas é o último grupo, então a rajada fica nos minutos de antes):
--      18/10: 18:54, 21:17, 22:09   ·   19/10: 08:29, 08:45, 09:14, 09:27
--    Houve outras, desde 16/09/2026, sem hora anotada.
-- ---------------------------------------------------------------------
select date_trunc('minute', quando at time zone 'America/Sao_Paulo') as minuto,
       count(*)                 filter (where tipo = 'impressao')                    as impressoes,
       count(distinct build_id) filter (where tipo = 'impressao')                    as builds,
       count(*)                 filter (where tipo in ('detalhe', 'visualizacao'))  as detalhes,
       count(*)                 filter (where tipo = 'engajamento')                  as engajamentos,
       count(*)                 filter (where tipo = 'copia')                        as copias
from public.eventos
group by 1
having count(distinct build_id) filter (where tipo = 'impressao') >= 10
order by 1 desc;


-- ---------------------------------------------------------------------
-- 3. Só leitura — a prévia da limpeza: quanto sairia, por dia e por tipo,
--    se ficasse UM evento de cada build por tipo e por dia (o primeiro).
--    Só impressões e detalhes, e só de antes da barreira do roteiro.
-- ---------------------------------------------------------------------
with numerados as (
  select id, tipo, (quando at time zone 'America/Sao_Paulo')::date as dia,
         row_number() over (partition by build_id, tipo, (quando at time zone 'America/Sao_Paulo')::date
                            order by quando) as n
  from public.eventos
  where tipo in ('impressao', 'detalhe', 'visualizacao')
    and quando < timestamptz '2026-10-19 16:10:00-03'
)
select dia, tipo, count(*) as sairiam
from numerados
where n > 1
group by 1, 2
order by 1 desc, 2;


-- ---------------------------------------------------------------------
-- 4. A LIMPEZA — comentada. Só rode depois de olhar o 3 e concordar.
--    Apaga exatamente o que o 3 contou e devolve quanto apagou, por tipo.
--    Para rodar: tire os "--" das linhas abaixo (só delas) e rode só este
--    trecho. Não dá para desfazer.
-- ---------------------------------------------------------------------
-- with numerados as (
--   select id,
--          row_number() over (partition by build_id, tipo, (quando at time zone 'America/Sao_Paulo')::date
--                             order by quando) as n
--   from public.eventos
--   where tipo in ('impressao', 'detalhe', 'visualizacao')
--     and quando < timestamptz '2026-10-19 16:10:00-03'
-- ), apagados as (
--   delete from public.eventos e
--   using numerados x
--   where e.id = x.id and x.n > 1
--   returning e.tipo
-- )
-- select tipo, count(*) as apagados from apagados group by tipo;
