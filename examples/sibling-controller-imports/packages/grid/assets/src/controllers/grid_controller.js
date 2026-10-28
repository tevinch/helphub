import { Controller } from '@hotwired/stimulus';

export default class GridController extends Controller {
  static targets = ['status', 'result'];

  connect() {
    this.rows = 0;
    this.statusTarget.textContent = 'Grid controller connected';
  }

  add() {
    this.rows += 1;
    this.resultTarget.textContent = `Grid: ${this.rows} row${this.rows === 1 ? '' : 's'}`;
  }
}
