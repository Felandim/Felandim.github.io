# Felandim.github.io

Site de evolução rodada a rodada do Brasileirão, com o portfólio profissional de Felipe Landim em páginas secundárias.

## Estrutura

- `index.html`: página principal do produto Rodada a Rodada.
- `brasileirao/`: classificação, artilharia, rankings, comparador, páginas de times e resumos por rodada.
- `brasileirao_2026/`: coleta de artilheiros e gerador das análises e páginas.
- `projetos.html`: seleção de projetos públicos.
- `dados-futebol.html`: estudo de caso e hub das competições.
- `artigos.html`: conteúdo técnico para busca orgânica.
- `style.css`: sistema visual compartilhado.
- `worldcup_2026/`, `serie_a_2026/` e `serie_b_2026/`: coletores e geradores das páginas de futebol.
- `docs/`: visualizações e páginas geradas.

## Atualizações automáticas

Os workflows do GitHub Actions atualizam a Copa do Mundo a cada quatro horas e as Séries A e B a cada seis horas. A atualização da Série A também consolida os autores dos gols, recalcula classificação, artilharia e movimentos de cada rodada e reescreve as páginas do produto.

## Validação

```bash
python3 -m py_compile worldcup_2026/main.py serie_a_2026/main.py serie_b_2026/main.py brasileirao_2026/build.py brasileirao_2026/update_scorers.py
```

```bash
pytest
```

## Publicidade

As páginas de maior tráfego possuem espaços de anúncio ocultos, prontos para integração depois da aprovação em uma rede de anúncios. Nenhum identificador de publicador fictício é mantido no repositório.

## Compartilhamento e audiência

O gerador cria imagens Open Graph de 1200 × 630 pixels para a página principal, classificação, artilharia, comparador, times e rodadas. O `site.js` carrega o Plausible Analytics apenas no domínio de produção, sem afetar a navegação local.
