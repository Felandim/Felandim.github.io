# Felandim.github.io

Site pessoal e portfólio de Felipe Landim, com foco em dados, crédito e automação.

## Estrutura

- `index.html`: página principal do portfólio.
- `projetos.html`: seleção de projetos públicos.
- `dados-futebol.html`: estudo de caso e hub das competições.
- `artigos.html`: conteúdo técnico para busca orgânica.
- `style.css`: sistema visual compartilhado.
- `worldcup_2026/`, `serie_a_2026/` e `serie_b_2026/`: coletores e geradores das páginas de futebol.
- `docs/`: visualizações e páginas geradas.

## Atualizações automáticas

Os workflows do GitHub Actions atualizam a Copa do Mundo a cada quatro horas e as Séries A e B a cada seis horas. Os geradores salvam dados em JSON e reescrevem o HTML apenas quando há mudança.

## Validação

```bash
python3 -m py_compile worldcup_2026/main.py serie_a_2026/main.py serie_b_2026/main.py
```

```bash
pytest
```

## Publicidade

As páginas de maior tráfego possuem espaços de anúncio ocultos, prontos para integração depois da aprovação em uma rede de anúncios. Nenhum identificador de publicador fictício é mantido no repositório.
