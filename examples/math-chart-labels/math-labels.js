// Adapted from Chart.js's MIT-licensed HTML legend sample; see LICENSE.
function renderMath(tex, target) {
  katex.render(tex, target, {output: 'htmlAndMathml', throwOnError: false, trust: false});
}

export const mathLabels = {
  id: 'math-labels',
  afterUpdate(chart, args, options) {
    const heading = document.getElementById(options.headingID);
    const legend = document.getElementById(options.legendID);
    renderMath(options.heading, heading);

    const focused = legend.contains(document.activeElement)
      ? document.activeElement.dataset.datasetIndex : null;
    const list = document.createElement('ul');
    const items = chart.options.plugins.legend.labels.generateLabels(chart);
    for (const item of items) {
      const index = item.datasetIndex;
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.datasetIndex = String(item.datasetIndex);
      button.setAttribute('aria-pressed', String(!item.hidden));
      button.setAttribute('aria-label', `Toggle ${chart.data.datasets[item.datasetIndex].accessibleLabel}`);
      button.classList.toggle('is-hidden', item.hidden);
      button.onclick = () => {
        chart.setDatasetVisibility(index, !chart.isDatasetVisible(index));
        chart.update();
      };

      const swatch = document.createElement('span');
      swatch.className = 'swatch';
      swatch.setAttribute('aria-hidden', 'true');
      swatch.style.backgroundColor = item.fillStyle;
      swatch.style.borderColor = item.strokeStyle;
      swatch.style.borderWidth = `${item.lineWidth}px`;
      const formula = document.createElement('span');
      formula.className = 'formula';
      renderMath(item.text, formula);
      button.append(swatch, formula);
      li.append(button);
      list.append(li);
    }
    legend.replaceChildren(list);
    if (focused != null) {
      legend.querySelector(`button[data-dataset-index="${focused}"]`)?.focus({preventScroll: true});
    }
  },
};
