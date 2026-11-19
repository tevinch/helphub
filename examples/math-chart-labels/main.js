import {mathLabels} from './math-labels.js';

export const ORIGINAL_FORMULA = String.raw`\sqrt{cos(x^2)} + se(x^2)`;
const examples = [
  {
    heading: ORIGINAL_FORMULA,
    labels: [ORIGINAL_FORMULA, String.raw`\sqrt{x^{2}+1}`],
    values: [[1.4, 2, 1.3, 2.4, 1.8], [.8, 1.5, 2.2, 1.6, 2.8]],
  },
  {
    heading: String.raw`\sqrt{x^{2}+4}`,
    labels: [String.raw`\sqrt{x^{2}+4}`, String.raw`\sqrt{x^{2}+9}`],
    values: [[2.8, 2.1, 3.1, 2.7, 3.4], [1.1, 2.5, 1.8, 2.9, 2.3]],
  },
];
let active = 0;
export function currentExample() { return structuredClone(examples[active]); }

export const chart = new Chart(document.getElementById('chart'), {
  type: 'line',
  data: {
    labels: ['A', 'B', 'C', 'D', 'E'],
    datasets: [
      {label: examples[0].labels[0], accessibleLabel: 'first series', data: [...examples[0].values[0]], borderColor: '#ca465d', backgroundColor: '#fbe4e8', pointBackgroundColor: '#ca465d', borderWidth: 3, pointRadius: 4},
      {label: examples[0].labels[1], accessibleLabel: 'second series', data: [...examples[0].values[1]], borderColor: '#327eac', backgroundColor: '#e0eff8', pointBackgroundColor: '#327eac', borderWidth: 3, pointRadius: 4, hidden: true},
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      title: {display: false},
      legend: {display: false},
      'math-labels': {headingID: 'math-heading', legendID: 'math-legend', heading: examples[0].heading},
    },
    scales: {y: {beginAtZero: true, suggestedMax: 4}},
  },
  plugins: [mathLabels],
});

export function updateExample() {
  active = 1 - active;
  const example = examples[active];
  chart.options.plugins['math-labels'].heading = example.heading;
  chart.data.datasets.forEach((dataset, index) => {
    dataset.label = example.labels[index];
    dataset.data = [...example.values[index]];
  });
  chart.update();
  document.getElementById('update-status').textContent = 'Labels and values updated. Your series visibility is preserved.';
}
document.getElementById('update-example').addEventListener('click', updateExample);
