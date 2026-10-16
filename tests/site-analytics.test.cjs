const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const source = readFileSync(join(__dirname, '..', 'site.js'), 'utf8');

function load(hostname, alreadyLoaded = false) {
  const scripts = [];
  const document = {
    querySelectorAll: () => [],
    querySelector: (selector) => alreadyLoaded && selector === 'script[data-domain="felandim.github.io"]' ? {} : null,
    createElement: () => ({ dataset: {} }),
    head: { append: (script) => scripts.push(script) },
  };
  runInNewContext(source, { document, location: { hostname } });
  return scripts;
}

test('carrega uma vez nos domínios de produção e mantém o painel existente', () => {
  for (const hostname of ['brasileiraoemrodadas.com.br', 'www.brasileiraoemrodadas.com.br', 'felandim.github.io']) {
    const scripts = load(hostname);
    assert.equal(scripts.length, 1);
    assert.equal(scripts[0].src, 'https://plausible.io/js/script.js');
    assert.equal(scripts[0].dataset.domain, 'felandim.github.io');
    assert.equal(scripts[0].defer, true);
    assert.equal(load(hostname, true).length, 0);
  }
});

test('não conta acessos de desenvolvimento nem domínios desconhecidos', () => {
  for (const hostname of ['localhost', '127.0.0.1', '', 'preview.example', 'brasileiraoemrodadas.com.br.example']) {
    assert.equal(load(hostname).length, 0);
  }
});
