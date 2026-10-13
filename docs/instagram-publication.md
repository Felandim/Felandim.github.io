# Publicação no Instagram

O workflow `instagram-daily.yml` verifica diariamente às 10h de São Paulo
(`0 13 * * *`). Alterações no código executam somente os testes.

`instagram_schedule.py` ordena os jogos de cada rodada pelo início programado
e agrupa jogos consecutivos separados por até 48 horas, inclusive. O bloco só
é publicado na manhã seguinte ao seu último jogo e quando todos os jogos
daquele bloco têm resultado. Uma partida futura dentro do bloco impede a
publicação antecipada. A regra não exige os dez jogos da rodada concluídos.

Jogos remarcados para mais de 48 horas depois formam outro bloco. Partidas
sem data e partidas explicitamente marcadas como adiadas, suspensas ou
canceladas, sem resultado, não retêm o bloco principal. Ao voltarem à grade
com data e status válidos, seguem a mesma regra. Sem horário definido,
consideramos todo o dia possível e só separamos se a distância mínima entre
os jogos superar 48 horas. Um jogo sem resultado nem sinalização de adiamento
continua pendente e bloqueia seu bloco.

Exemplo: sábado, domingo e segunda geram um resumo na terça às 10h, com todos
os jogos do bloco. Uma partida remarcada para a semana seguinte gera outro
post após ser disputada. Um bloco de jogo único destaca seus pontos e a
posição atual dos envolvidos, sem atribuir a ele mudanças causadas por outros
jogos. Blocos de rodadas diferentes produzem posts separados.

O plano congela os jogos e a legenda usados no card e na publicação. O arquivo
`data/instagram_blocks_published.json` registra partidas publicadas para evitar
repetições em reexecuções. Tentativas com resultado incerto permanecem como
`started` e exigem conferir o Instagram antes de liberar nova tentativa; o
workflow fica com falha e registra o estado sanitizado. O job não recupera
automaticamente blocos históricos: seleciona apenas os encerrados na véspera.
