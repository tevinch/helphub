import { createHtmlLegend } from './legend.mjs';
const legend = createHtmlLegend(document.getElementById('legend'), index =>
  index === 0 ? { font: 'italic 700 20px Arial, sans-serif', color: '#c22020' }
    : { font: 'normal 400 12px Georgia, serif', color: '#17652f' });
const chart = new Chart(document.getElementById('chart'), {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      { label: 'Number 1', data: [10, 20, 30, 40, 50, 60], borderColor: '#c22020', fill: false },
      { label: 'Number 2', data: [60, 50, 40, 30, 20, 10], borderColor: '#17212c', fill: false },
    ],
  },
  options: { responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { display: false } } },
  plugins: [legend],
});
document.getElementById('update').addEventListener('click', () => {
  chart.data.datasets.forEach(dataset => { dataset.data = dataset.data.map(value => value + 1); });
  chart.update();
});
