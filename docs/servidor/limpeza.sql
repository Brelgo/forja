-- =====================================================================
-- Limpeza dos eventos antigos: impressões e detalhes com mais de 30 dias.
-- Eles só servem para o "popular hoje / da semana", então 30 dias basta.
-- CUIDADO (25/10/2026): os ENGAJAMENTOS ficam — o número que a tela mostra é
-- contado direto dos eventos, de todo o tempo (a view builds_publicas). A
-- versão antiga deste arquivo apagava tudo com mais de 30 dias e derrubaria
-- 703 dos 866 engajamentos; foi corrigida antes de rodar.
-- RODADO em 25/10/2026, com a autorização do Leo: a opção B (o pg_cron
-- instalado e a tarefa 'limpeza-eventos' agendada).
--
-- Opção A — à mão, quando quiser: cole só a linha abaixo no SQL Editor e Run.
-- =====================================================================
delete from public.eventos where quando < now() - interval '30 days' and tipo in ('impressao', 'detalhe', 'visualizacao');

-- =====================================================================
-- Opção B — automático, uma vez por dia (03:00 UTC). Cole este bloco inteiro
-- e Run uma única vez; depois é só esquecer. Para desligar: select cron.unschedule('limpeza-eventos');
-- =====================================================================
create extension if not exists pg_cron with schema extensions;
select cron.schedule(
  'limpeza-eventos',
  '0 3 * * *',
  $$ delete from public.eventos where quando < now() - interval '30 days' and tipo in ('impressao', 'detalhe', 'visualizacao') $$
);

-- Conferir o tamanho quando quiser:
-- select count(*) as eventos, pg_size_pretty(pg_total_relation_size('public.eventos')) as tamanho from public.eventos;
