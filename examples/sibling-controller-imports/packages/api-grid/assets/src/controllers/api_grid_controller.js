import GridController from '@guide/grid-bundle/src/controllers/grid_controller.js';

export default class ApiGridController extends GridController {
  connect() {
    super.connect();
    this.statusTarget.textContent = 'API controller connected';
  }

  add() {
    super.add();
    this.resultTarget.textContent = `API uses grid: ${this.rows} rows`;
  }
}
