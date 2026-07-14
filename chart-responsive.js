window.addEventListener('load', () => {
  const node = document.querySelector('.chart-container .item');
  const chart = node && window.echarts?.getInstanceByDom(node);
  if (!chart) return;

  const resize = () => chart.resize();
  window.addEventListener('resize', resize);
  new ResizeObserver(resize).observe(node);
});
