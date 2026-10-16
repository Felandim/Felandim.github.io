# Medição de audiência

## Integração

Em 15/10/2026, o carregamento do Plausible passou a incluir o domínio personalizado e sua variante `www`, além do endereço GitHub Pages. O identificador de painel existente, `felandim.github.io`, foi preservado: ele identifica o site dentro do Plausible e pode receber tráfego de mais de um domínio.

Painel: https://plausible.io/felandim.github.io

**Estado:** integração do site corrigida; cadastro, assinatura ativa e recepção de eventos ainda precisam ser confirmados no painel autenticado. A presença do script ou uma resposta HTTP 202 isolada não comprovam que houve armazenamento. Nenhuma assinatura foi contratada nesta alteração.

## Métricas para crescimento

- Visitantes únicos e visualizações por dia e semana.
- Fontes de tráfego, sites de origem e campanhas.
- Páginas de entrada, páginas mais visitadas e conteúdos por time.
- Dispositivos e interação disponibilizada pelo painel.

As métricas usam a contagem do Plausible, sem cookies. Bloqueadores e filtros podem reduzir os totais. A integração não recupera visitas anteriores à coleta efetiva.

## Links de divulgação

Os parâmetros UTM (marcadores de origem e campanha no endereço) permitem comparar ações. Usar nomes em minúsculas, sem dados pessoais.

| Canal | Exemplo |
| --- | --- |
| Bio do Instagram | `https://brasileiraoemrodadas.com.br/?utm_source=instagram&utm_medium=social&utm_campaign=bio` |
| Story da rodada | `https://brasileiraoemrodadas.com.br/?utm_source=instagram&utm_medium=social&utm_campaign=rodada_31&utm_content=story` |
| Carrossel de memes | `https://brasileiraoemrodadas.com.br/?utm_source=instagram&utm_medium=social&utm_campaign=rodada_31&utm_content=memes` |

Esses exemplos não alteram automaticamente os links nas redes sociais. Para distinguir campanhas, cada publicação precisa usar seu link correspondente em um local clicável.

## Confirmação da coleta

1. Entrar na conta do Plausible e conferir o site `felandim.github.io`. Se o identificador não existir, cadastrar o domínio atual e substituir o identificador no `site.js` pelo snippet fornecido no painel.
2. Abrir o site em um navegador sem bloqueador e conferir a visualização em tempo real no painel. Identificar essa visita como teste.
3. Abrir um link UTM de teste e confirmar a origem/campanha, além da página visitada. Não tratar essa visita de validação como crescimento orgânico.

Referências: https://plausible.io/docs/add-website e https://plausible.io/docs/events-api.
