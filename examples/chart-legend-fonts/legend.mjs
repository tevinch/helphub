// Create one instance for each line/bar chart and its dedicated legend container.
export function createHtmlLegend(container, styleForDataset) {
  let list;
  return {
    id: 'htmllegendfonts',
    afterUpdate(chart) {
      if (!list) {
        list = document.createElement('ul');
        list.className = 'legend-list';
        container.append(list);
      }
      const active = document.activeElement;
      const focusedIndex = list.contains(active) ? active.dataset.datasetIndex : null;
      list.replaceChildren();
      const items = chart.options.plugins.legend.labels.generateLabels(chart);
      for (const item of items) {
        const index = item.datasetIndex;
        const li = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.datasetIndex = String(index);
        button.setAttribute('aria-pressed', String(!item.hidden));
        Object.assign(button.style, styleForDataset(index));
        button.style.textDecoration = item.hidden ? 'line-through' : 'none';
        const swatch = document.createElement('span');
        swatch.className = 'legend-swatch';
        swatch.setAttribute('aria-hidden', 'true');
        swatch.style.background = item.strokeStyle;
        const label = document.createElement('span');
        label.textContent = item.text;
        button.append(swatch, label);
        button.addEventListener('click', () => {
          chart.setDatasetVisibility(index, !chart.isDatasetVisible(index));
          chart.update();
        });
        li.append(button);
        list.append(li);
      }
      if (focusedIndex != null) {
        list.querySelector(`button[data-dataset-index="${focusedIndex}"]`)?.focus({ preventScroll: true });
      }
    },
    afterDestroy() {
      list?.remove();
      list = null;
    },
  };
}
